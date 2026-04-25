from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

from cyberrange.core.config import INSTANCES_FILE
from cyberrange.core.discovery import discover_ranges, get_range_by_key
from cyberrange.core.docker_client import DockerComposeClient
from cyberrange.core.models import (
    InstanceInfo,
    InstanceRuntime,
    InstanceStatus,
    NetworkInfo,
    PortMapping,
    RangeDefinition,
    ServiceInfo,
    Topology,
    TopologyEdge,
    TopologyNode,
    AttackPath,
)
from cyberrange.core.ports import PortAllocator
from cyberrange.core.stats import StatsTracker


class RangeManager:
    def __init__(self):
        self.port_allocator = PortAllocator()
        self.stats_tracker = StatsTracker()
        self._instances: dict[str, InstanceInfo] = {}
        self._load_instances()

    @staticmethod
    def _project_name(range_name: str, instance_id: int) -> str:
        return range_name if instance_id == 1 else f"{range_name}-{instance_id}"

    def start_range(self, range_key: str, instance_id: int = 1) -> InstanceInfo:
        range_def = get_range_by_key(range_key)
        if not range_def:
            raise FileNotFoundError(f"Range not found: {range_key}")

        project_name = self._project_name(range_def.name, instance_id)

        if project_name in self._instances and self._instances[project_name].status == InstanceStatus.RUNNING:
            return self._instances[project_name]

        # Check if original project already running (instance 1)
        if instance_id == 1:
            existing_client = DockerComposeClient(
                compose_file=range_def.compose_file,
                env_file=range_def.env_file,
                project_name=range_def.name,
            )
            ps = existing_client.ps()
            if ps:
                # Adopt existing running project
                config = self._get_compose_config(range_def)
                port_mappings = []
                for svc_name, svc_cfg in config.get("services", {}).items():
                    for port_spec in svc_cfg.get("ports", []):
                        host_p, container_p = self._parse_port_spec(port_spec)
                        if host_p is not None:
                            port_mappings.append(PortMapping(
                                host_port=host_p,
                                container_port=container_p,
                                service_name=svc_name,
                            ))
                instance = InstanceInfo(
                    instance_id=1,
                    range_key=range_key,
                    project_name=project_name,
                    status=InstanceStatus.RUNNING,
                    started_at=datetime.now(timezone.utc),
                    port_mappings=port_mappings,
                )
                self._instances[project_name] = instance
                self._save_instances()
                self.stats_tracker.record_start(project_name, range_key, instance_id)
                return instance

        config = self._get_compose_config(range_def)
        service_containers = self._extract_container_names(config)

        # Extract port specs: [(service_name, host_port, container_port)]
        port_specs = self._extract_port_specs(config)
        original_host_ports = [h for _, h, _ in port_specs]

        port_map = {}
        if original_host_ports:
            port_map = self.port_allocator.allocate_ports(project_name, original_host_ports)

        needs_remap = port_map or instance_id > 1
        if needs_remap:
            subnet_map = {}
            if instance_id > 1:
                subnet_map = self._build_subnet_map(config, instance_id)
            compose_path = self._generate_compose(
                config, project_name, port_map, service_containers, subnet_map, instance_id
            )
            client = DockerComposeClient(
                compose_file=compose_path,
                project_name=project_name,
            )
        else:
            client = DockerComposeClient(
                compose_file=range_def.compose_file,
                env_file=range_def.env_file,
                project_name=project_name,
            )

        result = client.up(detach=True, build=True)
        if result.returncode != 0:
            self.port_allocator.release_ports(project_name)
            raise RuntimeError(f"docker compose up failed:\n{result.stderr}")

        port_mappings = []
        for svc_name, orig_host, container_port in port_specs:
            new_host = port_map.get(orig_host, orig_host)
            port_mappings.append(PortMapping(
                host_port=new_host,
                container_port=container_port,
                service_name=svc_name,
            ))

        instance = InstanceInfo(
            instance_id=instance_id,
            range_key=range_key,
            project_name=project_name,
            status=InstanceStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            port_mappings=port_mappings,
            compose_overrides={"port_map": {str(k): v for k, v in port_map.items()}},
        )

        self._instances[project_name] = instance
        self._save_instances()
        self.stats_tracker.record_start(project_name, range_key, instance_id)

        return instance

    def stop_range(
        self,
        range_key: str,
        instance_id: int = 1,
        remove: bool = False,
        volumes: bool = False,
    ) -> None:
        range_def = get_range_by_key(range_key)
        if not range_def:
            raise FileNotFoundError(f"Range not found: {range_key}")

        project_name = self._project_name(range_def.name, instance_id)

        client = DockerComposeClient(
            compose_file=range_def.compose_file,
            env_file=range_def.env_file,
            project_name=project_name,
        )

        if remove or volumes:
            result = client.down(remove_orphans=True, volumes=volumes)
        else:
            result = client.stop()

        if result.returncode != 0:
            raise RuntimeError(f"docker compose stop/down failed:\n{result.stderr}")

        self.port_allocator.release_ports(project_name)
        self.stats_tracker.record_stop(project_name)

        if project_name in self._instances:
            self._instances[project_name].status = InstanceStatus.STOPPED
            self._instances[project_name].stopped_at = datetime.now(timezone.utc)
            self._save_instances()

    def get_status(
        self,
        range_key: str | None = None,
        instance_id: int | None = None,
    ) -> list[InstanceRuntime]:
        results: list[InstanceRuntime] = []

        targets = self._filter_instances(range_key, instance_id)
        for project_name, instance in targets.items():
            runtime = self._build_runtime(instance)
            results.append(runtime)

        return results

    def list_ranges(self) -> list[dict]:
        ranges = discover_ranges()
        result = []
        for r in ranges:
            key = f"{r.category}/{r.name}"
            instances = []
            for pname, inst in self._instances.items():
                if inst.range_key == key and inst.status == InstanceStatus.RUNNING:
                    instances.append({
                        "instance_id": inst.instance_id,
                        "project_name": inst.project_name,
                        "status": inst.status.value,
                        "started_at": inst.started_at.isoformat() if inst.started_at else None,
                    })
            result.append({
                "range_key": key,
                "category": r.category,
                "name": r.name,
                "services": r.services,
                "networks": r.networks,
                "total_services": r.total_services,
                "has_readme": r.has_readme,
                "running_instances": instances,
            })
        return result

    def get_topology(self, range_key: str, instance_id: int = 1) -> dict:
        range_def = get_range_by_key(range_key)
        if not range_def:
            raise FileNotFoundError(f"Range not found: {range_key}")

        project_name = self._project_name(range_def.name, instance_id)
        instance = self._instances.get(project_name)

        config = self._get_compose_config(range_def)
        if not config:
            return Topology().model_dump(mode="json")

        services_cfg = config.get("services", {})
        networks_cfg = config.get("networks", {})

        port_map = {}
        if instance:
            port_map = {
                str(pm.container_port): pm.host_port
                for pm in instance.port_mappings
            }

        nodes: list[TopologyNode] = []
        edges: list[TopologyEdge] = []
        entry_points: list[dict] = []

        nodes.append(TopologyNode(
            name="attacker",
            type="external",
            description="Attacker machine (localhost)",
        ))

        net_members: dict[str, list[str]] = {}
        for svc_name, svc_cfg in services_cfg.items():
            svc_nets = svc_cfg.get("networks", {})
            ips: dict[str, str] = {}
            if isinstance(svc_nets, dict):
                for net_name, net_cfg in svc_nets.items():
                    if isinstance(net_cfg, dict) and "ipv4_address" in net_cfg:
                        ips[net_name] = net_cfg["ipv4_address"]
                    net_members.setdefault(net_name, []).append(svc_name)
            elif isinstance(svc_nets, list):
                for net_name in svc_nets:
                    net_members.setdefault(net_name, []).append(svc_name)

            image = svc_cfg.get("image", "")
            host_ports = self._extract_service_host_ports(svc_cfg)
            node = TopologyNode(
                name=svc_name,
                type="service",
                ips=ips,
                ports=host_ports,
                image=image,
            )
            nodes.append(node)

            if host_ports and instance:
                for hp in host_ports:
                    mapped = port_map.get(str(hp), hp)
                    entry_points.append({
                        "service": svc_name,
                        "url": f"http://localhost:{mapped}",
                        "container_port": hp,
                    })

        for net_name, members in net_members.items():
            subnet = None
            net_cfg = networks_cfg.get(net_name, {})
            if isinstance(net_cfg, dict):
                ipam = net_cfg.get("ipam", {})
                if isinstance(ipam, dict):
                    configs = ipam.get("config", [])
                    if configs and isinstance(configs, list):
                        subnet = configs[0].get("subnet") if isinstance(configs[0], dict) else None

            for i, svc_a in enumerate(members):
                if svc_a == "attacker":
                    continue
                if any(p in services_cfg.get(svc_a, {}).get("ports", []) for p in services_cfg.get(svc_a, {}).get("ports", [])):
                    if "attacker" not in [e.from_service for e in edges if e.to_service == svc_a]:
                        edges.append(TopologyEdge(
                            from_service="attacker",
                            to_service=svc_a,
                            network="host",
                            description=f"Host port mapping",
                        ))

                for svc_b in members[i + 1:]:
                    if svc_b == "attacker":
                        continue
                    edges.append(TopologyEdge(
                        from_service=svc_a,
                        to_service=svc_b,
                        network=net_name,
                        description=f"Same subnet {subnet or net_name}",
                    ))
                    edges.append(TopologyEdge(
                        from_service=svc_b,
                        to_service=svc_a,
                        network=net_name,
                        description=f"Same subnet {subnet or net_name}",
                    ))

        edges = self._deduplicate_edges(edges)

        attack_paths = self._build_attack_paths(nodes, edges, entry_points)

        topology = Topology(
            nodes=nodes,
            edges=edges,
            entry_points=entry_points,
            attack_paths=attack_paths,
        )
        return topology.model_dump(mode="json")

    # ---- Private helpers ----

    def _get_compose_config(self, range_def: RangeDefinition) -> dict:
        client = DockerComposeClient(
            compose_file=range_def.compose_file,
            env_file=range_def.env_file,
        )
        return client.config()

    @staticmethod
    def _parse_port_spec(port_spec) -> tuple[int | None, int]:
        if isinstance(port_spec, str) and ":" in port_spec:
            parts = port_spec.split(":")
            try:
                return int(parts[0]), int(parts[1].split("/")[0])
            except ValueError:
                return None, 0
        elif isinstance(port_spec, dict):
            try:
                return int(port_spec["published"]), int(port_spec["target"])
            except (KeyError, ValueError):
                return None, 0
        return None, 0

    def _extract_port_specs(self, config: dict) -> list[tuple[str, int, int]]:
        """Extract (service_name, host_port, container_port) from compose config."""
        specs: list[tuple[str, int, int]] = []
        for svc_name, svc_cfg in config.get("services", {}).items():
            for port_spec in svc_cfg.get("ports", []):
                host_p, container_p = self._parse_port_spec(port_spec)
                if host_p is not None:
                    specs.append((svc_name, host_p, container_p))
        return specs

    def _extract_host_ports(self, config: dict) -> list[int]:
        ports: list[int] = []
        for svc_cfg in config.get("services", {}).values():
            for port_spec in svc_cfg.get("ports", []):
                if isinstance(port_spec, str) and ":" in port_spec:
                    host_part = port_spec.split(":")[0]
                    try:
                        ports.append(int(host_part))
                    except ValueError:
                        pass
                elif isinstance(port_spec, dict):
                    published = port_spec.get("published")
                    if published:
                        try:
                            ports.append(int(published))
                        except ValueError:
                            pass
        return ports

    def _extract_service_host_ports(self, svc_cfg: dict) -> list[int]:
        ports: list[int] = []
        for port_spec in svc_cfg.get("ports", []):
            if isinstance(port_spec, str) and ":" in port_spec:
                container_part = port_spec.split(":")[-1]
                try:
                    ports.append(int(container_part.split("/")[0]))
                except ValueError:
                    pass
            elif isinstance(port_spec, dict):
                target = port_spec.get("target")
                if target:
                    try:
                        ports.append(int(target))
                    except ValueError:
                        pass
        return ports

    def _extract_container_names(self, config: dict) -> dict[str, str]:
        names = {}
        for svc_name, svc_cfg in config.get("services", {}).items():
            cn = svc_cfg.get("container_name")
            if cn:
                names[svc_name] = cn
        return names

    def _generate_compose(
        self,
        config: dict,
        project_name: str,
        port_map: dict[int, int],
        container_names: dict[str, str],
        subnet_map: dict[str, str] | None = None,
        instance_id: int = 1,
    ) -> Path:
        import copy
        cfg = copy.deepcopy(config)

        # Remove top-level keys that docker compose config adds but aren't valid compose keys
        cfg.pop("name", None)

        # Remove project-qualified network names so compose generates fresh ones
        for net_cfg in cfg.get("networks", {}).values():
            if isinstance(net_cfg, dict):
                net_cfg.pop("name", None)

        # Port specs for remapping
        port_specs = self._extract_port_specs(config)
        svc_port_map: dict[str, list[tuple[int, int]]] = {}
        for svc_name, orig_host, container_p in port_specs:
            svc_port_map.setdefault(svc_name, []).append((orig_host, container_p))

        for svc_name, svc_cfg in cfg.get("services", {}).items():
            # Override container name
            if container_names.get(svc_name):
                svc_cfg["container_name"] = f"{container_names[svc_name]}-{project_name}"

            # Override ports (replace entire list)
            if svc_name in svc_port_map:
                new_ports = []
                for orig_host, container_p in svc_port_map[svc_name]:
                    new_host = port_map.get(orig_host, orig_host)
                    new_ports.append(f"{new_host}:{container_p}")
                svc_cfg["ports"] = new_ports

            # Remap service IPs for multi-instance
            if subnet_map and instance_id > 1:
                svc_nets = svc_cfg.get("networks", {})
                if isinstance(svc_nets, dict):
                    for net_name, net_cfg in svc_nets.items():
                        if net_name not in subnet_map:
                            continue
                        if isinstance(net_cfg, dict) and "ipv4_address" in net_cfg:
                            old_ip = net_cfg["ipv4_address"]
                            net_cfg["ipv4_address"] = self._offset_ip(old_ip, instance_id - 1)

        # Network subnet overrides for multi-instance
        if subnet_map:
            for net_name, new_subnet in subnet_map.items():
                net_cfg = cfg.get("networks", {}).get(net_name)
                if isinstance(net_cfg, dict):
                    ipam = net_cfg.setdefault("ipam", {})
                    if isinstance(ipam, dict):
                        ipam["config"] = [{"subnet": new_subnet}]

        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix="-compose.yml",
            prefix=f"cyberrange-{project_name}-",
            delete=False,
        )
        yaml.dump(cfg, tmp, default_flow_style=False)
        tmp.close()
        return Path(tmp.name)

    def _build_runtime(self, instance: InstanceInfo) -> InstanceRuntime:
        range_def = get_range_by_key(instance.range_key)
        services: list[ServiceInfo] = []
        networks: list[NetworkInfo] = []
        access_urls: dict[str, str] = {}

        if range_def:
            client = DockerComposeClient(
                compose_file=range_def.compose_file,
                env_file=range_def.env_file,
                project_name=instance.project_name,
            )
            ps_data = client.ps()
            config = client.config()

            ps_by_name = {}
            for container in ps_data:
                name = container.get("Service", container.get("Name", ""))
                ps_by_name[name] = container

            for svc_name, svc_cfg in config.get("services", {}).items():
                image = svc_cfg.get("image", "")
                cn = svc_cfg.get("container_name")
                container_ps = ps_by_name.get(svc_name, {})
                status = container_ps.get("Status", "unknown")
                state = container_ps.get("State", "")
                if state:
                    status = state

                ips: dict[str, str] = {}
                svc_nets = svc_cfg.get("networks", {})
                if isinstance(svc_nets, dict):
                    for net_name, net_cfg in svc_nets.items():
                        if isinstance(net_cfg, dict) and "ipv4_address" in net_cfg:
                            ips[net_name] = net_cfg["ipv4_address"]

                svc_ports = []
                for pm in instance.port_mappings:
                    svc_ports.append(pm)

                services.append(ServiceInfo(
                    name=svc_name,
                    image=image,
                    container_name=cn,
                    status=status,
                    ports=svc_ports,
                    internal_ips=ips,
                    networks=list(svc_nets.keys()) if isinstance(svc_nets, (dict, list)) else [],
                ))

                container_ports = self._extract_service_host_ports(svc_cfg)
                for cp in container_ports:
                    host_p = None
                    for pm in instance.port_mappings:
                        if pm.container_port == cp:
                            host_p = pm.host_port
                            break
                    if host_p:
                        access_urls[svc_name] = f"http://localhost:{host_p}"

            net_members: dict[str, list[str]] = {}
            for svc_name, svc_cfg in config.get("services", {}).items():
                svc_nets = svc_cfg.get("networks", {})
                if isinstance(svc_nets, dict):
                    for net_name in svc_nets:
                        net_members.setdefault(net_name, []).append(svc_name)
                elif isinstance(svc_nets, list):
                    for net_name in svc_nets:
                        net_members.setdefault(net_name, []).append(svc_name)

            for net_name, net_cfg in config.get("networks", {}).items():
                subnet = None
                if isinstance(net_cfg, dict):
                    ipam = net_cfg.get("ipam", {})
                    if isinstance(ipam, dict):
                        configs = ipam.get("config", [])
                        if configs and isinstance(configs, list) and isinstance(configs[0], dict):
                            subnet = configs[0].get("subnet")
                networks.append(NetworkInfo(
                    name=net_name,
                    subnet=subnet,
                    services=net_members.get(net_name, []),
                ))

        return InstanceRuntime(
            instance_id=instance.instance_id,
            range_key=instance.range_key,
            project_name=instance.project_name,
            status=instance.status,
            services=services,
            networks=networks,
            access_urls=access_urls,
        )

    def _filter_instances(
        self,
        range_key: str | None,
        instance_id: int | None,
    ) -> dict[str, InstanceInfo]:
        result = {}
        for pname, inst in self._instances.items():
            if range_key and inst.range_key != range_key:
                continue
            if instance_id is not None and inst.instance_id != instance_id:
                continue
            result[pname] = inst
        return result

    def _build_subnet_map(self, config: dict, instance_id: int) -> dict[str, str]:
        subnet_map: dict[str, str] = {}
        offset = instance_id - 1
        for net_name, net_cfg in config.get("networks", {}).items():
            if not isinstance(net_cfg, dict):
                continue
            ipam = net_cfg.get("ipam", {})
            if not isinstance(ipam, dict):
                continue
            for cfg in ipam.get("config", []):
                if not isinstance(cfg, dict):
                    continue
                subnet = cfg.get("subnet")
                if not subnet:
                    continue
                new_subnet = self._offset_subnet(subnet, offset)
                if new_subnet != subnet:
                    subnet_map[net_name] = new_subnet
        return subnet_map

    @staticmethod
    def _offset_subnet(subnet: str, offset: int) -> str:
        parts = subnet.split("/")
        prefix = int(parts[1])
        octets = [int(o) for o in parts[0].split(".")]

        if prefix <= 16:
            # /16: use 172.{30 + offset}.0.0 to avoid common Docker ranges
            octets[1] = min(30 + offset, 250)
            octets[2] = 0
            octets[3] = 0
        else:
            # /24+: offset third octet by offset*10
            octets[2] = min(octets[2] + offset * 10, 250)

        return f"{'.'.join(str(o) for o in octets)}/{prefix}"

    @staticmethod
    def _offset_ip(ip: str, offset: int) -> str:
        """Offset an IP address following the same rules as _offset_subnet."""
        octets = [int(o) for o in ip.split(".")]
        if octets[0] == 172 and 14 <= octets[1] <= 29:
            # Was a /16 range: remap to 172.{30 + offset}.x.y
            octets[1] = min(30 + offset, 250)
        else:
            # Was a /24 range: offset third octet
            octets[2] = min(octets[2] + offset * 10, 250)
        return ".".join(str(o) for o in octets)

    def _deduplicate_edges(self, edges: list[TopologyEdge]) -> list[TopologyEdge]:
        seen: set[tuple[str, str, str]] = set()
        unique: list[TopologyEdge] = []
        for e in edges:
            key = (e.from_service, e.to_service, e.network)
            if key not in seen:
                seen.add(key)
                unique.append(e)
        return unique

    def _build_attack_paths(
        self,
        nodes: list[TopologyNode],
        edges: list[TopologyEdge],
        entry_points: list[dict],
    ) -> list[AttackPath]:
        if not entry_points:
            return []

        adj: dict[str, list[tuple[str, str, str]]] = {}
        for e in edges:
            adj.setdefault(e.from_service, []).append((e.to_service, e.network, e.description))

        longest_path: list[str] = []
        visited: set[str] = set()

        def dfs(node: str, path: list[str]):
            nonlocal longest_path
            if len(path) > len(longest_path):
                longest_path = list(path)
            visited.add(node)
            for neighbor, network, desc in adj.get(node, []):
                if neighbor not in visited and neighbor != "attacker":
                    path.append(f"{node} -> {neighbor} ({network})")
                    dfs(neighbor, path)
                    path.pop()
            visited.discard(node)

        for ep in entry_points:
            svc = ep["service"]
            start_desc = f"attacker -> {svc} (host:{ep.get('url', '')})"
            dfs(svc, [start_desc])

        if not longest_path:
            return []

        return [AttackPath(
            path=longest_path,
            depth=len(longest_path),
            description="Multi-layer pivoting path through internal networks",
        )]

    def _load_instances(self) -> None:
        if INSTANCES_FILE.exists():
            try:
                data = json.loads(INSTANCES_FILE.read_text())
                for pname, info in data.items():
                    self._instances[pname] = InstanceInfo.model_validate(info)
            except (json.JSONDecodeError, ValueError):
                self._instances = {}

    def _save_instances(self) -> None:
        INSTANCES_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {pname: inst.model_dump(mode="json") for pname, inst in self._instances.items()}
        INSTANCES_FILE.write_text(json.dumps(data, indent=2, default=str))

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from cyberrange.core.manager import RangeManager

mcp = FastMCP(
    name="cyberrange",
    instructions=(
        "CyberRange management server. Start, stop, and inspect Docker-based "
        "cyber range environments. Query network topologies and service details "
        "to plan penetration testing exercises."
    ),
)

_manager = RangeManager()


@mcp.tool()
def list_ranges() -> list[dict]:
    """List all discovered cyber range environments and their running instances."""
    return _manager.list_ranges()


@mcp.tool()
def start_range(range_key: str, instance_id: int = 1) -> dict:
    """Start a cyber range instance.

    Args:
        range_key: Range identifier (e.g., "pentest/cfs")
        instance_id: Instance number for multi-instance support (default: 1)
    """
    try:
        info = _manager.start_range(range_key, instance_id)
        runtimes = _manager.get_status(range_key, instance_id)
        topology = _manager.get_topology(range_key, instance_id)
        result = {
            "instance": info.model_dump(mode="json"),
            "topology": topology,
        }
        if runtimes:
            result["runtime"] = runtimes[0].model_dump(mode="json")
        return result
    except (FileNotFoundError, RuntimeError) as e:
        return {"error": str(e)}


@mcp.tool()
def stop_range(
    range_key: str,
    instance_id: int = 1,
    remove: bool = False,
    volumes: bool = False,
) -> dict:
    """Stop a running cyber range instance.

    Args:
        range_key: Range identifier (e.g., "pentest/cfs")
        instance_id: Instance number to stop (default: 1)
        remove: Remove containers and networks (docker compose down)
        volumes: Also remove named volumes (implies remove=true)
    """
    try:
        _manager.stop_range(range_key, instance_id, remove=remove or volumes, volumes=volumes)
        return {"status": "stopped", "range_key": range_key, "instance_id": instance_id}
    except (FileNotFoundError, RuntimeError) as e:
        return {"error": str(e)}


@mcp.tool()
def get_status(
    range_key: str | None = None,
    instance_id: int | None = None,
) -> list[dict]:
    """Get runtime status of cyber range instances.

    Args:
        range_key: Optional range filter (e.g., "pentest/cfs"). Omit for all.
        instance_id: Optional instance number filter.
    """
    runtimes = _manager.get_status(range_key, instance_id)
    return [r.model_dump(mode="json") for r in runtimes]


@mcp.tool()
def get_topology(range_key: str, instance_id: int = 1) -> dict:
    """Get the network topology graph for a range instance.

    Returns nodes (services + IPs), edges (network connectivity),
    entry points (host-exposed services), and suggested attack paths.

    Args:
        range_key: Range identifier (e.g., "pentest/cfs")
        instance_id: Instance number (default: 1)
    """
    try:
        return _manager.get_topology(range_key, instance_id)
    except FileNotFoundError as e:
        return {"error": str(e)}


@mcp.tool()
def get_stats(
    range_key: str | None = None,
    instance_id: int | None = None,
) -> dict:
    """Get usage statistics for range instances.

    Args:
        range_key: Optional range filter. Omit for all.
        instance_id: Optional instance number filter.
    """
    project_name = None
    if range_key:
        name = range_key.split("/")[-1]
        iid = instance_id or 1
        project_name = name if iid == 1 else f"{name}-{iid}"
    return _manager.stats_tracker.get_stats(project_name)


@mcp.tool()
def record_interaction(
    range_key: str,
    instance_id: int = 1,
    action: str = "status_check",
    details: dict | None = None,
) -> dict:
    """Record an interaction event with a range instance.

    Use to track AI agent actions: flag submissions, exploit attempts, recon.

    Args:
        range_key: Range identifier (e.g., "pentest/cfs")
        instance_id: Instance number (default: 1)
        action: Action type (e.g., "flag_submit", "exploit_attempt", "recon")
        details: Arbitrary key-value details about the interaction
    """
    name = range_key.split("/")[-1]
    project_name = name if instance_id == 1 else f"{name}-{instance_id}"
    _manager.stats_tracker.record_interaction(project_name, action, details or {})
    return {"status": "recorded", "action": action, "project_name": project_name}

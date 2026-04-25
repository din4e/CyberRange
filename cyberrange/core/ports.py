from __future__ import annotations

import json
import socket
from pathlib import Path

from cyberrange.core.config import PORT_ALLOC_FILE, PORT_POOL_END, PORT_POOL_START, PORTS_PER_INSTANCE


class PortAllocator:
    def __init__(self, state_file: Path | None = None):
        self.state_file = state_file or PORT_ALLOC_FILE
        self._allocations: dict[str, list[int]] = {}
        self._load()

    def allocate_ports(
        self, project_name: str, original_ports: list[int]
    ) -> dict[int, int]:
        if not original_ports:
            return {}

        used = {
            p
            for ports in self._allocations.values()
            for p in ports
        }

        mapping: dict[int, int] = {}
        for i, orig_port in enumerate(original_ports):
            # First instance: try to keep original port
            if orig_port not in used and _port_available(orig_port):
                mapping[orig_port] = orig_port
                used.add(orig_port)
                continue

            # Fallback: allocate from pool
            base = PORT_POOL_START + i
            stride = PORTS_PER_INSTANCE
            candidate = base
            while candidate <= PORT_POOL_END:
                if candidate not in used and _port_available(candidate):
                    break
                candidate += stride
            else:
                raise RuntimeError(
                    f"No available port in pool for mapping {orig_port}"
                )

            mapping[orig_port] = candidate
            used.add(candidate)

        self._allocations[project_name] = list(mapping.values())
        self._save()
        return mapping

    def release_ports(self, project_name: str) -> None:
        self._allocations.pop(project_name, None)
        self._save()

    def get_allocated(self, project_name: str) -> list[int]:
        return self._allocations.get(project_name, [])

    def _load(self) -> None:
        if self.state_file.exists():
            try:
                self._allocations = json.loads(self.state_file.read_text())
            except (json.JSONDecodeError, OSError):
                self._allocations = {}

    def _save(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self._allocations, indent=2))


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False

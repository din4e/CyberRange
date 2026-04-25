from __future__ import annotations

import os
from pathlib import Path

from cyberrange.core.config import PROJECT_ROOT, SKIP_DIRS
from cyberrange.core.docker_client import DockerComposeClient
from cyberrange.core.models import RangeDefinition


def discover_ranges(root_dir: Path | None = None) -> list[RangeDefinition]:
    root = root_dir or PROJECT_ROOT
    results: list[RangeDefinition] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for filename in filenames:
            if filename not in ("docker-compose.yml", "docker-compose.yaml"):
                continue

            compose_path = Path(dirpath) / filename
            rel = compose_path.parent.relative_to(root)
            parts = rel.parts

            if len(parts) >= 2:
                category = parts[-2]
                name = parts[-1]
            elif len(parts) == 1:
                category = "default"
                name = parts[0]
            else:
                continue

            env_path = compose_path.parent / ".env"
            readme_path = compose_path.parent / "README.md"

            meta = _parse_compose_metadata(
                compose_path,
                env_path if env_path.exists() else None,
            )

            results.append(RangeDefinition(
                category=category,
                name=name,
                path=compose_path.parent.resolve(),
                compose_file=compose_path.resolve(),
                env_file=env_path.resolve() if env_path.exists() else None,
                services=meta.get("services", []),
                networks=meta.get("networks", []),
                total_services=len(meta.get("services", [])),
                has_readme=readme_path.exists(),
            ))

    return sorted(results, key=lambda r: (r.category, r.name))


def get_range(category: str, name: str) -> RangeDefinition | None:
    for r in discover_ranges():
        if r.category == category and r.name == name:
            return r
    return None


def get_range_by_key(range_key: str) -> RangeDefinition | None:
    parts = range_key.split("/", 1)
    if len(parts) != 2:
        return None
    return get_range(parts[0], parts[1])


def _parse_compose_metadata(
    compose_path: Path, env_path: Path | None
) -> dict:
    client = DockerComposeClient(compose_path, env_file=env_path)
    config = client.config()
    if not config:
        return {"services": [], "networks": []}

    services = list(config.get("services", {}).keys())
    networks = list(config.get("networks", {}).keys())

    return {"services": services, "networks": networks}

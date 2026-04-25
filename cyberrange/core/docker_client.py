from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cyberrange.core.config import DEFAULT_COMPOSE_TIMEOUT


class DockerComposeClient:
    def __init__(
        self,
        compose_file: Path,
        env_file: Path | None = None,
        project_name: str | None = None,
        override_file: Path | None = None,
        timeout: int = DEFAULT_COMPOSE_TIMEOUT,
    ):
        self.compose_file = compose_file
        self.env_file = env_file
        self.project_name = project_name
        self.override_file = override_file
        self.timeout = timeout

    def _base_args(self) -> list[str]:
        args = ["docker", "compose"]
        if self.project_name:
            args += ["-p", self.project_name]
        if self.env_file:
            args += ["--env-file", str(self.env_file)]
        args += ["-f", str(self.compose_file)]
        if self.override_file:
            args += ["-f", str(self.override_file)]
        return args

    def up(self, detach: bool = True, build: bool = False) -> subprocess.CompletedProcess:
        cmd = self._base_args() + ["up"]
        if detach:
            cmd.append("-d")
        if build:
            cmd.append("--build")
        return self._run(cmd)

    def down(self, remove_orphans: bool = True, volumes: bool = False) -> subprocess.CompletedProcess:
        cmd = self._base_args() + ["down"]
        if remove_orphans:
            cmd.append("--remove-orphans")
        if volumes:
            cmd.append("-v")
        return self._run(cmd)

    def stop(self) -> subprocess.CompletedProcess:
        return self._run(self._base_args() + ["stop"])

    def ps(self) -> list[dict]:
        result = self._run(self._base_args() + ["ps", "--format", "json"])
        if result.returncode != 0:
            return []
        text = result.stdout.strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # NDJSON: one JSON object per line
            items = []
            for line in text.splitlines():
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            return items

    def config(self) -> dict:
        result = self._run(self._base_args() + ["config", "--format", "json"])
        if result.returncode != 0:
            return {}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}

    def _run(self, args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout,
            cwd=self.compose_file.parent,
        )

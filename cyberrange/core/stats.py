from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cyberrange.core.config import STATS_FILE
from cyberrange.core.models import AllStats, InstanceStats, InteractionRecord


class StatsTracker:
    def __init__(self, stats_file: Path | None = None):
        self.stats_file = stats_file or STATS_FILE
        self._stats = self._load()

    def record_start(self, project_name: str, range_key: str, instance_id: int) -> None:
        stats = self._ensure_instance(project_name, range_key, instance_id)
        stats.total_starts += 1
        stats.current_session_start = datetime.now(timezone.utc)
        stats.last_interaction = datetime.now(timezone.utc)
        stats.interactions.append(InteractionRecord(
            timestamp=datetime.now(timezone.utc),
            action="start",
            details={"range_key": range_key, "instance_id": instance_id},
        ))
        self._save()

    def record_stop(self, project_name: str) -> float:
        stats = self._stats.instances.get(project_name)
        if not stats:
            return 0.0

        now = datetime.now(timezone.utc)
        stats.total_stops += 1
        runtime = 0.0
        if stats.current_session_start:
            runtime = (now - stats.current_session_start).total_seconds()
            stats.total_runtime_seconds += runtime
            stats.current_session_start = None

        stats.last_interaction = now
        stats.interactions.append(InteractionRecord(
            timestamp=now,
            action="stop",
            details={"runtime_seconds": runtime},
        ))
        self._save()
        return runtime

    def record_interaction(
        self, project_name: str, action: str, details: dict | None = None
    ) -> None:
        stats = self._stats.instances.get(project_name)
        if not stats:
            return
        now = datetime.now(timezone.utc)
        stats.last_interaction = now
        stats.interactions.append(InteractionRecord(
            timestamp=now,
            action=action,
            details=details or {},
        ))
        self._save()

    def get_stats(self, project_name: str | None = None) -> dict:
        if project_name:
            stats = self._stats.instances.get(project_name)
            if not stats:
                return {}
            result = stats.model_dump(mode="json")
            if stats.current_session_start:
                elapsed = (datetime.now(timezone.utc) - stats.current_session_start).total_seconds()
                result["current_session_seconds"] = elapsed
            return result

        summary = {}
        for name, s in self._stats.instances.items():
            entry = {
                "range_key": s.range_key,
                "instance_id": s.instance_id,
                "total_starts": s.total_starts,
                "total_stops": s.total_stops,
                "total_runtime_seconds": s.total_runtime_seconds,
                "interaction_count": len(s.interactions),
                "last_interaction": s.last_interaction.isoformat() if s.last_interaction else None,
            }
            if s.current_session_start:
                elapsed = (datetime.now(timezone.utc) - s.current_session_start).total_seconds()
                entry["current_session_seconds"] = elapsed
            summary[name] = entry
        return summary

    def _ensure_instance(
        self, project_name: str, range_key: str, instance_id: int
    ) -> InstanceStats:
        if project_name not in self._stats.instances:
            self._stats.instances[project_name] = InstanceStats(
                range_key=range_key,
                instance_id=instance_id,
                project_name=project_name,
            )
        return self._stats.instances[project_name]

    def _load(self) -> AllStats:
        if self.stats_file.exists():
            try:
                return AllStats.model_validate_json(self.stats_file.read_text())
            except (json.JSONDecodeError, ValueError):
                pass
        return AllStats()

    def _save(self) -> None:
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats_file.write_text(self._stats.model_dump_json(indent=2))

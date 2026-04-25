from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class InstanceStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    REMOVED = "removed"


class PortMapping(BaseModel):
    host_port: int
    container_port: int
    protocol: str = "tcp"
    service_name: str


class ServiceInfo(BaseModel):
    name: str
    image: str
    container_name: str | None = None
    status: str = "unknown"
    ports: list[PortMapping] = []
    internal_ips: dict[str, str] = {}
    networks: list[str] = []
    flags: dict[str, str] = {}


class NetworkInfo(BaseModel):
    name: str
    subnet: str | None = None
    services: list[str] = []


class TopologyNode(BaseModel):
    name: str
    type: str = "service"
    ips: dict[str, str] = {}
    vulnerabilities: list[str] = []
    flags: list[str] = []
    ports: list[int] = []


class TopologyEdge(BaseModel):
    from_service: str
    to_service: str
    network: str
    description: str = ""


class AttackPath(BaseModel):
    path: list[str]
    depth: int
    description: str = ""


class Topology(BaseModel):
    nodes: list[TopologyNode] = []
    edges: list[TopologyEdge] = []
    entry_points: list[dict] = []
    attack_paths: list[AttackPath] = []


class RangeDefinition(BaseModel):
    category: str
    name: str
    path: Path
    compose_file: Path
    env_file: Path | None = None
    description: str | None = None
    services: list[str] = []
    networks: list[str] = []
    total_services: int = 0
    has_readme: bool = False


class InstanceInfo(BaseModel):
    instance_id: int
    range_key: str
    project_name: str
    status: InstanceStatus = InstanceStatus.STOPPED
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    port_mappings: list[PortMapping] = []
    compose_overrides: dict = {}
    services: list[ServiceInfo] = []


class InstanceRuntime(BaseModel):
    instance_id: int
    range_key: str
    project_name: str
    status: InstanceStatus
    services: list[ServiceInfo]
    networks: list[NetworkInfo]
    topology: Topology | None = None
    access_urls: dict[str, str] = {}


class InteractionRecord(BaseModel):
    timestamp: datetime
    action: str
    details: dict = {}


class InstanceStats(BaseModel):
    range_key: str
    instance_id: int
    project_name: str
    total_starts: int = 0
    total_stops: int = 0
    total_runtime_seconds: float = 0.0
    current_session_start: datetime | None = None
    interactions: list[InteractionRecord] = Field(default_factory=list)
    last_interaction: datetime | None = None


class AllStats(BaseModel):
    instances: dict[str, InstanceStats] = Field(default_factory=dict)


"""
Pydantic models for the Multi-Agent IT Ops Platform.
All data structures used across agents, API, and WebSocket events.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
import uuid


class Severity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"

class IncidentStatus(str, Enum):
    OPEN = "open"
    TRIAGING = "triaging"
    REMEDIATING = "remediating"
    PREEMPTING = "preempting"
    RESOLVED = "resolved"

class AgentStatus(str, Enum):
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"

class AgentType(str, Enum):
    SERVER_MONITOR = "server_monitor"
    CLOUD_MONITOR = "cloud_monitor"
    APP_HEALTH = "app_health"
    PREDICTIVE = "predictive"
    REMEDIATION = "remediation"
    DEPLOYMENT = "deployment"
    REPORTING = "reporting"

class FailureClass(str, Enum):
    OOMKILL = "OOMKill"
    CPU_SATURATION = "CPUSaturation"
    NETWORK_DEGRADATION = "NetworkDegradation"
    LATENCY_SPIKE = "LatencySpike"
    DISK_PRESSURE = "DiskPressure"
    CERT_EXPIRY = "CertExpiry"
    REPLICA_LAG = "ReplicaLag"
    KAFKA_LAG = "KafkaLag"


# ─── Telemetry / Metrics ───────────────────────────────────────────────────

class HostMetric(BaseModel):
    host: str
    cpu_pct: float = Field(ge=0, le=100)
    mem_pct: float = Field(ge=0, le=100)
    disk_pct: float = Field(ge=0, le=100)
    net_in_mbps: float = 0.0
    net_out_mbps: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class CloudMetric(BaseModel):
    provider: Literal["AWS", "Azure", "GCP"]
    region: str
    service: str
    packet_loss_pct: float = 0.0
    latency_ms: float = 0.0
    cost_usd_day: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AppMetric(BaseModel):
    service: str
    p99_ms: float = 0.0
    error_rate_pct: float = 0.0
    rps: float = 0.0
    replica_count: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── A2A Messages ──────────────────────────────────────────────────────────

class A2AMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    from_agent: AgentType
    to_agent: AgentType
    payload: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── Incidents ────────────────────────────────────────────────────────────

class Incident(BaseModel):
    id: str = Field(default_factory=lambda: f"INC-{str(uuid.uuid4())[:4].upper()}")
    severity: Severity
    title: str
    description: str
    failure_class: FailureClass
    status: IncidentStatus = IncidentStatus.OPEN
    host: Optional[str] = None
    region: Optional[str] = None
    agent_chain: List[AgentType] = []
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    mttr_seconds: Optional[float] = None
    runbook: Optional[str] = None
    auto_resolved: bool = False


# ─── Predictions ──────────────────────────────────────────────────────────

class Prediction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    failure_class: FailureClass
    target: str
    probability: float = Field(ge=0.0, le=1.0)
    horizon_minutes: int
    signal_description: str
    recommended_runbook: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acted_on: bool = False

    @property
    def risk_level(self) -> str:
        if self.probability >= 0.75:
            return "high"
        elif self.probability >= 0.50:
            return "medium"
        return "low"


# ─── Agent State ──────────────────────────────────────────────────────────

class AgentState(BaseModel):
    agent_type: AgentType
    status: AgentStatus = AgentStatus.ACTIVE
    description: str
    pills: List[dict] = []
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    messages_sent: int = 0
    messages_received: int = 0


# ─── KPIs ─────────────────────────────────────────────────────────────────

class KPISnapshot(BaseModel):
    uptime_pct: float
    active_incidents: int
    resolved_24h: int
    avg_mttr_minutes: float
    sla_adherence_pct: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ─── WebSocket Events ─────────────────────────────────────────────────────

class WSEvent(BaseModel):
    event: str  # "incident", "prediction", "a2a_log", "kpi", "agent_update", "metric"
    data: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)

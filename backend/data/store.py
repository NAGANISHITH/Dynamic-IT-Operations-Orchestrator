"""
In-memory data store — simulates a real database + time-series store.
In production: replace with PostgreSQL + TimescaleDB + Redis.
"""

import asyncio
from collections import deque
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random

from models.schemas import (
    Incident, Prediction, A2AMessage, AgentState, KPISnapshot,
    HostMetric, CloudMetric, AppMetric,
    AgentType, AgentStatus, IncidentStatus, Severity,
    FailureClass
)


class DataStore:
    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.predictions: Dict[str, Prediction] = {}
        self.a2a_log: deque = deque(maxlen=500)
        self.host_metrics: deque = deque(maxlen=1000)
        self.cloud_metrics: deque = deque(maxlen=500)
        self.app_metrics: deque = deque(maxlen=1000)
        self.kpi_history: deque = deque(maxlen=200)
        self.agent_states: Dict[str, AgentState] = {}
        self._resolved_count_24h: int = 27
        self._total_mttr_seconds: float = 0.0
        self._resolved_count_mttr: int = 0
        self._lock = asyncio.Lock()

        self._init_agents()
        self._seed_initial_data()

    def _init_agents(self):
        agents = [
            (AgentType.SERVER_MONITOR, "Polls 240 hosts · 15s interval", AgentStatus.ACTIVE,
             [{"label":"Healthy","cls":"green"},{"label":"2 alerts","cls":"amber"},{"label":"CMDB synced","cls":"gray"}]),
            (AgentType.CLOUD_MONITOR, "12 regions · 3 cloud providers", AgentStatus.ACTIVE,
             [{"label":"All regions up","cls":"green"},{"label":"$4.2k/day","cls":"blue"}]),
            (AgentType.APP_HEALTH, "38 services · OpenTelemetry", AgentStatus.BUSY,
             [{"label":"p99: 840ms","cls":"amber"},{"label":"Error: 0.3%","cls":"gray"}]),
            (AgentType.PREDICTIVE, "LSTM ensemble · 72h forecast", AgentStatus.ACTIVE,
             [{"label":"3 high-risk","cls":"red"},{"label":"Acc: 94.1%","cls":"green"}]),
            (AgentType.REMEDIATION, "Policy-driven · runbook engine", AgentStatus.BUSY,
             [{"label":"1 active fix","cls":"amber"},{"label":"27 resolved","cls":"green"}]),
            (AgentType.DEPLOYMENT, "Kubernetes · Terraform · Ansible", AgentStatus.ACTIVE,
             [{"label":"Stable","cls":"green"},{"label":"8 pods scaled","cls":"teal"}]),
            (AgentType.REPORTING, "SLA tracking · executive dashboards", AgentStatus.ACTIVE,
             [{"label":"99.1% SLA","cls":"teal"},{"label":"Daily report","cls":"gray"}]),
        ]
        for atype, desc, status, pills in agents:
            self.agent_states[atype.value] = AgentState(
                agent_type=atype, status=status, description=desc, pills=pills
            )

    def _seed_initial_data(self):
        """Seed realistic initial incidents and predictions."""
        seed_incidents = [
            Incident(
                id="INC-2041", severity=Severity.P1,
                title="payment-api · Pod OOMKill — us-east-1a",
                description="Memory usage at 91.4%, OOMKill imminent. Heap limit increase and pod scale-out initiated.",
                failure_class=FailureClass.OOMKILL, status=IncidentStatus.REMEDIATING,
                host="payment-api-pod-3", region="us-east-1a",
                agent_chain=[AgentType.SERVER_MONITOR, AgentType.PREDICTIVE, AgentType.REMEDIATION, AgentType.DEPLOYMENT],
                runbook="oom-001",
            ),
            Incident(
                id="INC-2040", severity=Severity.P2,
                title="db-primary · Replication lag forecast — eu-west-2",
                description="Write IOPS trending toward saturation. Replication lag increasing at +12ms/min.",
                failure_class=FailureClass.REPLICA_LAG, status=IncidentStatus.PREEMPTING,
                region="eu-west-2",
                agent_chain=[AgentType.PREDICTIVE, AgentType.REMEDIATION, AgentType.DEPLOYMENT],
                runbook="db-throttle",
            ),
            Incident(
                id="INC-2039", severity=Severity.P2,
                title="vpc-transit · Packet loss 3.2% — us-west-2",
                description="Network packet loss detected. Traffic rerouted via backup AZ.",
                failure_class=FailureClass.NETWORK_DEGRADATION, status=IncidentStatus.RESOLVED,
                region="us-west-2",
                agent_chain=[AgentType.CLOUD_MONITOR, AgentType.REMEDIATION],
                resolved_at=datetime.utcnow() - timedelta(minutes=5),
                mttr_seconds=134.0, auto_resolved=True, runbook="vpc-reroute",
            ),
            Incident(
                id="INC-2038", severity=Severity.P3,
                title="search-cluster · CPU saturation 94% — ap-southeast-1",
                description="CPU saturation. HPA scale-out from 4 to 9 pods completed.",
                failure_class=FailureClass.CPU_SATURATION, status=IncidentStatus.RESOLVED,
                region="ap-southeast-1",
                agent_chain=[AgentType.APP_HEALTH, AgentType.PREDICTIVE, AgentType.DEPLOYMENT],
                resolved_at=datetime.utcnow() - timedelta(minutes=10),
                mttr_seconds=98.0, auto_resolved=True, runbook="hpa-scale",
            ),
        ]
        for inc in seed_incidents:
            self.incidents[inc.id] = inc

        seed_preds = [
            Prediction(
                failure_class=FailureClass.OOMKILL, target="payment-api",
                probability=0.91, horizon_minutes=135,
                signal_description="6-hr mem growth +2.1 GB/hr · current: 91.4% of 8 GB · pattern: OOMKill (7 historical matches)",
                recommended_runbook="oom-001"
            ),
            Prediction(
                failure_class=FailureClass.REPLICA_LAG, target="db-primary",
                probability=0.78, horizon_minutes=45,
                signal_description="Write IOPS: 94% capacity · lag increasing +12ms/min · ETL batch job spike detected",
                recommended_runbook="db-throttle"
            ),
            Prediction(
                failure_class=FailureClass.CERT_EXPIRY, target="us-east-1-lb",
                probability=0.64, horizon_minutes=8640,
                signal_description="TLS cert expires in 6 days · ACM auto-renewal pending DNS validation",
                recommended_runbook="cert-renew"
            ),
            Prediction(
                failure_class=FailureClass.KAFKA_LAG, target="kafka-consumer-group-1",
                probability=0.38, horizon_minutes=1080,
                signal_description="Consumer offset divergence: 2.4M msgs behind · producer stable · consumer threads reduced",
                recommended_runbook="kafka-rebalance"
            ),
        ]
        for p in seed_preds:
            self.predictions[p.id] = p

    # ── Incidents ──────────────────────────────────────────────

    async def add_incident(self, inc: Incident):
        async with self._lock:
            self.incidents[inc.id] = inc

    async def update_incident(self, inc_id: str, **kwargs):
        async with self._lock:
            if inc_id in self.incidents:
                inc = self.incidents[inc_id]
                for k, v in kwargs.items():
                    setattr(inc, k, v)
                if kwargs.get("status") == IncidentStatus.RESOLVED:
                    inc.resolved_at = datetime.utcnow()
                    if inc.opened_at:
                        mttr = (inc.resolved_at - inc.opened_at).total_seconds()
                        inc.mttr_seconds = mttr
                        self._total_mttr_seconds += mttr
                        self._resolved_count_mttr += 1
                    self._resolved_count_24h += 1
                    inc.auto_resolved = True
                return inc
        return None

    def get_incidents(self, status: Optional[str] = None) -> List[Incident]:
        incs = list(self.incidents.values())
        if status:
            incs = [i for i in incs if i.status.value == status]
        return sorted(incs, key=lambda i: i.opened_at, reverse=True)

    def get_active_incident_count(self) -> int:
        return sum(1 for i in self.incidents.values()
                   if i.status not in [IncidentStatus.RESOLVED])

    # ── Predictions ────────────────────────────────────────────

    async def add_prediction(self, pred: Prediction):
        async with self._lock:
            self.predictions[pred.id] = pred

    def get_predictions(self) -> List[Prediction]:
        return sorted(self.predictions.values(), key=lambda p: p.probability, reverse=True)

    # ── A2A Log ────────────────────────────────────────────────

    async def add_a2a_message(self, msg: A2AMessage):
        async with self._lock:
            self.a2a_log.append(msg)
            state = self.agent_states.get(msg.from_agent.value)
            if state:
                state.messages_sent += 1
                state.last_heartbeat = datetime.utcnow()
            dst = self.agent_states.get(msg.to_agent.value)
            if dst:
                dst.messages_received += 1

    def get_a2a_log(self, limit: int = 100) -> List[A2AMessage]:
        logs = list(self.a2a_log)
        return logs[-limit:]

    # ── Metrics ────────────────────────────────────────────────

    async def add_host_metric(self, m: HostMetric):
        async with self._lock:
            self.host_metrics.append(m)

    async def add_cloud_metric(self, m: CloudMetric):
        async with self._lock:
            self.cloud_metrics.append(m)

    async def add_app_metric(self, m: AppMetric):
        async with self._lock:
            self.app_metrics.append(m)

    def get_latest_host_metrics(self, n: int = 10) -> List[HostMetric]:
        seen = {}
        for m in reversed(list(self.host_metrics)):
            if m.host not in seen:
                seen[m.host] = m
        return list(seen.values())[:n]

    def get_latest_app_metrics(self) -> List[AppMetric]:
        seen = {}
        for m in reversed(list(self.app_metrics)):
            if m.service not in seen:
                seen[m.service] = m
        return list(seen.values())

    # ── KPIs ───────────────────────────────────────────────────

    def get_kpi(self) -> KPISnapshot:
        mttr = (self._total_mttr_seconds / self._resolved_count_mttr / 60.0
                if self._resolved_count_mttr > 0 else 4.2)
        return KPISnapshot(
            uptime_pct=round(99.90 + random.uniform(0, 0.09), 2),
            active_incidents=self.get_active_incident_count(),
            resolved_24h=self._resolved_count_24h,
            avg_mttr_minutes=round(mttr, 1),
            sla_adherence_pct=99.1,
        )

    # ── Agent States ───────────────────────────────────────────

    def get_agent_states(self) -> List[AgentState]:
        return list(self.agent_states.values())

    async def update_agent_status(self, agent_type: AgentType, status: AgentStatus):
        async with self._lock:
            if agent_type.value in self.agent_states:
                self.agent_states[agent_type.value].status = status
                self.agent_states[agent_type.value].last_heartbeat = datetime.utcnow()


# Singleton
store = DataStore()

"""
Predictive Failure Agent — simulates LSTM ensemble scoring.
Receives telemetry alerts, scores failure probability, emits to Remediation.
"""

import asyncio
import random
from datetime import datetime

from agents.base import BaseAgent
from models.schemas import (
    AgentType, AgentStatus, Prediction, FailureClass, Incident,
    Severity, IncidentStatus
)
from data.store import store
from services.websocket_manager import websocket_manager


# Runbook mapping per failure class
RUNBOOK_MAP = {
    "mem":          ("oom-001",          FailureClass.OOMKILL,           Severity.P1),
    "cpu":          ("hpa-scale",        FailureClass.CPU_SATURATION,    Severity.P2),
    "disk":         ("disk-cleanup",     FailureClass.DISK_PRESSURE,     Severity.P2),
    "packet_loss":  ("vpc-reroute",      FailureClass.NETWORK_DEGRADATION, Severity.P2),
    "latency":      ("db-throttle",      FailureClass.LATENCY_SPIKE,     Severity.P2),
    "error_rate":   ("rollback-deploy",  FailureClass.LATENCY_SPIKE,     Severity.P3),
}

SIGNAL_DESCRIPTIONS = {
    "mem":         "Memory growth trend detected · heap pressure increasing",
    "cpu":         "CPU saturation sustained >3 min · HPA threshold breached",
    "disk":        "Disk usage growing · log accumulation pattern detected",
    "packet_loss": "Network packet loss detected · routing anomaly",
    "latency":     "p99 latency degradation · upstream contention suspected",
    "error_rate":  "Error rate spike · possible bad deployment",
}


class PredictiveFailureAgent(BaseAgent):
    """LSTM-based failure prediction. Scores alert payloads and routes to remediation."""

    def __init__(self, remediation_agent=None):
        super().__init__(AgentType.PREDICTIVE)
        self.remediation_agent = remediation_agent
        self._recent_alerts: dict = {}  # deduplicate: alert_key → timestamp

    async def run(self):
        while True:
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=30)
                await self._process(msg)
            except asyncio.TimeoutError:
                # Periodic autonomous prediction sweep
                await self._autonomous_sweep()

    async def _process(self, msg):
        await store.update_agent_status(self.agent_type, AgentStatus.BUSY)
        payload = msg.payload
        alert_type = payload.get("alert_type", "mem")

        # Dedup: same host+alert_type within 60s → skip
        dedup_key = f"{payload.get('host','')}{payload.get('service','')}{payload.get('region','')}-{alert_type}"
        now = datetime.utcnow().timestamp()
        if dedup_key in self._recent_alerts and now - self._recent_alerts[dedup_key] < 60:
            await store.update_agent_status(self.agent_type, AgentStatus.ACTIVE)
            return
        self._recent_alerts[dedup_key] = now

        # Simulate LSTM scoring
        await asyncio.sleep(random.uniform(0.5, 1.5))

        value = payload.get("value", 50.0)
        threshold = payload.get("threshold", 85.0)
        overshoot = (value - threshold) / threshold
        base_prob = min(0.97, 0.60 + overshoot * 0.8 + random.uniform(-0.05, 0.05))

        runbook, failure_class, severity = RUNBOOK_MAP.get(alert_type, RUNBOOK_MAP["mem"])
        horizon = max(5, int(120 - overshoot * 60 + random.randint(-10, 10)))
        signal = SIGNAL_DESCRIPTIONS.get(alert_type, "Anomaly detected")
        target = payload.get("host") or payload.get("service") or payload.get("region") or "unknown"

        pred = Prediction(
            failure_class=failure_class,
            target=target,
            probability=round(base_prob, 2),
            horizon_minutes=horizon,
            signal_description=f"{signal} · value={value} (threshold={threshold})",
            recommended_runbook=runbook,
        )
        await store.add_prediction(pred)
        await websocket_manager.broadcast("prediction", pred.model_dump(mode="json"))

        # Dispatch to remediation if high confidence
        if base_prob > 0.55:
            # Create incident
            inc = Incident(
                severity=severity,
                title=f"{target} · {failure_class.value} detected",
                description=f"{signal}. Auto-remediation triggered. Runbook: {runbook}.",
                failure_class=failure_class,
                status=IncidentStatus.TRIAGING,
                host=payload.get("host"),
                region=payload.get("region"),
                agent_chain=[msg.from_agent, self.agent_type],
                runbook=runbook,
            )
            await store.add_incident(inc)
            await websocket_manager.broadcast("incident", inc.model_dump(mode="json"))

            await self.send(AgentType.REMEDIATION, {
                "incident_id": inc.id,
                "failure_class": failure_class.value,
                "severity": severity.value,
                "runbook": runbook,
                "target": target,
                "probability": base_prob,
                "host": payload.get("host"),
                "region": payload.get("region"),
                "service": payload.get("service"),
            })

            # Forward to remediation agent directly
            if self.remediation_agent:
                await self.remediation_agent.receive(
                    await self.send(AgentType.REMEDIATION, {
                        "incident_id": inc.id,
                        "failure_class": failure_class.value,
                        "severity": severity.value,
                        "runbook": runbook,
                        "target": target,
                    })
                )

        await store.update_agent_status(self.agent_type, AgentStatus.ACTIVE)

    async def _autonomous_sweep(self):
        """Proactively scan stored metrics for emerging patterns."""
        host_metrics = store.get_latest_host_metrics(5)
        for m in host_metrics:
            if m.mem_pct > 88 or m.cpu_pct > 88:
                alert_type = "mem" if m.mem_pct > 88 else "cpu"
                val = m.mem_pct if alert_type == "mem" else m.cpu_pct
                from models.schemas import A2AMessage
                fake_msg = A2AMessage(
                    from_agent=AgentType.SERVER_MONITOR,
                    to_agent=AgentType.PREDICTIVE,
                    payload={"alert_type": alert_type, "host": m.host, "value": val, "threshold": 85.0}
                )
                await self._process(fake_msg)

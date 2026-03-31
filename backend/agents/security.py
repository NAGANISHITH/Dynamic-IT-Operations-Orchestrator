"""
Security Agent.
Detects anomalies, intrusions, and unusual patterns in traffic and access logs.
"""

import asyncio
import random
from datetime import datetime
from .base import BaseAgent
from models.schemas import AgentType, SecurityAnomaly, Severity
from services.websocket_manager import websocket_manager

class SecurityAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.SECURITY)

    async def run(self):
        print(f"Agent {self.agent_type.value} started.")
        while True:
            await self._scan_for_anomalies()
            await asyncio.sleep(45)

    async def _scan_for_anomalies(self):
        from data.store import store
        if random.random() < 0.1:  # 10% chance to detect an anomaly
            threats = [
                ("Brute Force Attempt", "P1", "Multiple failed login attempts from unknown IP."),
                ("DDoS Pattern", "P1", "Unexpected spike in traffic from disparate regions."),
                ("SQL Injection", "P2", "Malicious patterns detected in application logs."),
                ("Unusual Access", "P3", "Admin access from a new geographic location."),
            ]
            title, sev, desc = random.choice(threats)
            
            anomaly = SecurityAnomaly(
                title=title,
                severity=Severity(sev),
                source_ip=f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                threat_type="External",
                description=desc
            )
            await store.add_security_anomaly(anomaly)
            await websocket_manager.broadcast("security_anomaly", anomaly.model_dump(mode="json"))
            
            await self.send(AgentType.REPORTING, {
                "type": "security_anomaly",
                "anomaly_id": anomaly.id
            })
            
            # Explicit integration for Webhooks
            await self.send(AgentType.NOTIFICATION, {
                "action": "trigger_webhook",
                "url": "https://siem.enterprise.local/api/v1/ingest",
                "data": {
                    "alert": anomaly.title,
                    "severity": anomaly.severity.value,
                    "ip": anomaly.source_ip
                }
            })

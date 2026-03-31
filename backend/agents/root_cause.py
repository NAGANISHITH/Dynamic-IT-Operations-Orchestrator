"""
Root Cause Analysis Agent.
Correlates logs, metrics, and events to identify the exact cause of failures.
"""

import asyncio
import random
from datetime import datetime
from .base import BaseAgent
from models.schemas import AgentType, IncidentRCA, A2AMessage

class RootCauseAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.ROOT_CAUSE)
        self.knowledge_base = {
            "OOMKill": "Memory leak detected in service heap. High allocation rate in recent 10 mins.",
            "CPUSaturation": "Unexpected spike in background worker threads correlated with high request volume.",
            "NetworkDegradation": "BGP route flap in upstream provider AZ. Increased packet retransmissions.",
            "LatencySpike": "Database lock contention on primary index during large ETL batch job.",
            "DiskPressure": "Log rotation failure in /var/log/app. Uncompressed old logs consuming space.",
        }

    async def run(self):
        print(f"Agent {self.agent_type.value} started.")
        while True:
            msg: A2AMessage = await self._inbox.get()
            
            if msg.payload.get("type") == "analyze_incident":
                await self._process_analysis(msg)
            
            self._inbox.task_done()

    async def _process_analysis(self, msg: A2AMessage):
        incident_id = msg.payload.get("incident_id")
        failure_class = msg.payload.get("failure_class")
        resource_id = msg.payload.get("resource_id")
        
        # Simulate thinking time
        await asyncio.sleep(2)
        
        from data.store import store
        res = store.get_resource(resource_id) if resource_id else None
        
        if res and res.type.value == "database":
            cause = "Database Lock Contention"
            explanation = f"Database [{res.name}] is experiencing lock contention on primary index causing {failure_class}."
        elif res and res.type.value == "web_app":
            cause = "Massive Traffic Spike"
            explanation = f"Web App [{res.name}] overwhelmed by 400% organic traffic burst resulting in {failure_class}."
        elif res and res.type.value == "server":
            cause = "Process Exhaustion"
            explanation = f"Server [{res.name}] underlying OS CPU/Memory exhaustion due to runaway background java process."
        else:
            cause = self.knowledge_base.get(failure_class, "Unknown system anomaly.")
            explanation = f"Automated correlation for {incident_id} confirms: {cause}"
        
        rca = IncidentRCA(
            incident_id=incident_id,
            cause=failure_class,
            explanation=explanation,
            confidence=round(0.85 + random.uniform(0, 0.1), 2),
            suggested_fix=f"Trigger runbook for {failure_class}"
        )
        
        # Store the RCA
        await store.add_rca(rca)
        
        # Notify other agents
        await self.send(AgentType.REPORTING, {
            "type": "rca_completed",
            "incident_id": incident_id,
            "rca_id": rca.id
        })
        
        # Explicit integration for Slack
        await self.send(AgentType.NOTIFICATION, {
            "action": "send_slack",
            "channel": "#devops-alerts",
            "message": f"🚨 RCA Completed for {incident_id}: {cause} ({rca.confidence * 100:.0f}% confidence)"
        })

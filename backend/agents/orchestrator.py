"""
Agent Orchestrator — creates all agents, wires A2A message routing,
starts their async run-loops concurrently.
"""

import asyncio
from models.schemas import AgentType, A2AMessage
from agents.monitoring import ServerMonitorAgent, CloudMonitorAgent, AppHealthAgent
from agents.predictive import PredictiveFailureAgent
from agents.remediation import RemediationAgent, DeploymentAgent
from agents.reporting import ReportingAgent
from services.websocket_manager import websocket_manager
from data.store import store


class AgentOrchestrator:
    def __init__(self):
        # Instantiate all agents
        self.deployment = DeploymentAgent()
        self.remediation = RemediationAgent(deployment_agent=self.deployment)
        self.predictive = PredictiveFailureAgent(remediation_agent=self.remediation)
        self.server_monitor = ServerMonitorAgent()
        self.cloud_monitor = CloudMonitorAgent()
        self.app_health = AppHealthAgent()
        self.reporting = ReportingAgent()

        # Wire monitors → predictive
        self.server_monitor.send = self._make_router(self.server_monitor, "send")
        self.cloud_monitor.send = self._make_router(self.cloud_monitor, "send")
        self.app_health.send = self._make_router(self.app_health, "send")

        self._agent_map = {
            AgentType.SERVER_MONITOR: self.server_monitor,
            AgentType.CLOUD_MONITOR: self.cloud_monitor,
            AgentType.APP_HEALTH: self.app_health,
            AgentType.PREDICTIVE: self.predictive,
            AgentType.REMEDIATION: self.remediation,
            AgentType.DEPLOYMENT: self.deployment,
            AgentType.REPORTING: self.reporting,
        }

    def _make_router(self, agent, _):
        """Wrap send() to also deliver the message to the target agent inbox."""
        orig_send = agent.__class__.__bases__[0].send

        async def routed_send(to: AgentType, payload: dict):
            msg = A2AMessage(from_agent=agent.agent_type, to_agent=to, payload=payload)
            from data.store import store as ds
            await ds.add_a2a_message(msg)
            await websocket_manager.broadcast("a2a_log", {
                "id": msg.id,
                "from_agent": msg.from_agent.value,
                "to_agent": msg.to_agent.value,
                "payload": msg.payload,
                "timestamp": msg.timestamp.isoformat(),
            })
            target = self._agent_map.get(to)
            if target:
                await target.receive(msg)
            return msg

        return routed_send

    async def run(self):
        """Start all agent loops concurrently."""
        tasks = [
            asyncio.create_task(self.server_monitor.run()),
            asyncio.create_task(self.cloud_monitor.run()),
            asyncio.create_task(self.app_health.run()),
            asyncio.create_task(self.predictive.run()),
            asyncio.create_task(self.remediation.run()),
            asyncio.create_task(self.deployment.run()),
            asyncio.create_task(self.reporting.run()),
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def simulate_incident(self, incident_type: str = "oom"):
        """Manually inject a simulated incident for demo purposes."""
        from models.schemas import A2AMessage
        type_map = {
            "oom":     {"alert_type": "mem",         "host": "redis-master",      "value": 93.2, "threshold": 85.0},
            "cpu":     {"alert_type": "cpu",         "host": "api-gateway",       "value": 95.1, "threshold": 85.0},
            "network": {"alert_type": "packet_loss", "region": "eu-central-1",   "value": 4.8,  "threshold": 1.0},
            "latency": {"alert_type": "latency",     "service": "auth-service",   "value": 950,  "threshold": 800},
            "disk":    {"alert_type": "disk",        "host": "elasticsearch-1",   "value": 91.0, "threshold": 85.0},
        }
        payload = type_map.get(incident_type, type_map["oom"])
        msg = A2AMessage(
            from_agent=AgentType.SERVER_MONITOR,
            to_agent=AgentType.PREDICTIVE,
            payload=payload,
        )
        await self.predictive.receive(msg)

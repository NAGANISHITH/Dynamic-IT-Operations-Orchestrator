"""
Notification Agent.
Simulates sending external notifications via Webhooks, Slack, and Email.
"""

import asyncio
from datetime import datetime
from .base import BaseAgent
from models.schemas import AgentType, A2AMessage

class NotificationAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.NOTIFICATION)

    async def run(self):
        print(f"Agent {self.agent_type.value} started.")
        while True:
            msg: A2AMessage = await self._inbox.get()
            
            action = msg.payload.get("action")
            
            if action == "send_slack":
                await self._simulate_slack(msg.payload)
            elif action == "send_email":
                await self._simulate_email(msg.payload)
            elif action == "trigger_webhook":
                await self._simulate_webhook(msg.payload)
            
            self._inbox.task_done()

    async def _simulate_slack(self, payload: dict):
        channel = payload.get("channel", "#devops-alerts")
        message = payload.get("message", "")
        # Simulate network latency
        await asyncio.sleep(0.5)
        print(f"[Slack] Posted to {channel}: {message}")

    async def _simulate_email(self, payload: dict):
        to_address = payload.get("to", "soc-team@company.local")
        subject = payload.get("subject", "Alert")
        # Simulate network latency
        await asyncio.sleep(1.0)
        print(f"[Email] Sent to {to_address}. Subject: {subject}")

    async def _simulate_webhook(self, payload: dict):
        url = payload.get("url", "https://api.pagerduty.simulation/v1/alert")
        data = payload.get("data", {})
        # Simulate network latency
        await asyncio.sleep(0.3)
        print(f"[Webhook] POST {url} - Payload: {data}")

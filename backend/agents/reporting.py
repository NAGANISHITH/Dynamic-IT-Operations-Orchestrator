"""Reporting Agent — aggregates outcomes and broadcasts SLA snapshots."""

import asyncio
import random
from agents.base import BaseAgent
from models.schemas import AgentType, AgentStatus
from data.store import store
from services.websocket_manager import websocket_manager


class ReportingAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.REPORTING)

    async def run(self):
        while True:
            # Broadcast KPI every 10 seconds
            kpi = store.get_kpi()
            await websocket_manager.broadcast("kpi", kpi.model_dump(mode="json"))
            await asyncio.sleep(10)

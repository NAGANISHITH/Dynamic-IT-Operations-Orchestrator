"""Base agent interface shared by all specialized agents."""

import asyncio
from abc import ABC, abstractmethod
from models.schemas import AgentType, A2AMessage
from data.store import store
from services.websocket_manager import websocket_manager


class BaseAgent(ABC):
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self._inbox: asyncio.Queue = asyncio.Queue()

    async def send(self, to: AgentType, payload: dict):
        msg = A2AMessage(from_agent=self.agent_type, to_agent=to, payload=payload)
        await store.add_a2a_message(msg)
        await websocket_manager.broadcast("a2a_log", {
            "id": msg.id,
            "from_agent": msg.from_agent.value,
            "to_agent": msg.to_agent.value,
            "payload": msg.payload,
            "timestamp": msg.timestamp.isoformat(),
        })
        return msg

    async def receive(self, msg: A2AMessage):
        await self._inbox.put(msg)

    @abstractmethod
    async def run(self):
        """Main agent loop."""
        ...

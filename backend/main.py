"""
Multi-Agent IT Operations Platform - FastAPI Backend
Entry point for the entire backend application.
"""

import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routes import router
from agents.orchestrator import AgentOrchestrator
from services.websocket_manager import websocket_manager

orchestrator = AgentOrchestrator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start agent orchestrator on startup, stop on shutdown."""
    task = asyncio.create_task(orchestrator.run())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="Autonomous IT Ops Platform",
    description="Multi-agent AI system for real-time IT infrastructure management",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Expose orchestrator to routes via app state
app.state.orchestrator = orchestrator
app.state.wsm = websocket_manager

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

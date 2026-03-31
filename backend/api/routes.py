"""
FastAPI Routes — REST API + WebSocket endpoint.
All frontend data access goes through these endpoints.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Query
from fastapi.responses import JSONResponse
from typing import Optional
import asyncio

from data.store import store
from services.websocket_manager import websocket_manager
from models.schemas import AgentType

router = APIRouter()


# ─── WebSocket ────────────────────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main real-time event stream for the frontend."""
    await websocket_manager.connect(websocket)
    try:
        # Send initial snapshot on connect
        kpi = store.get_kpi()
        await websocket.send_json({"event": "kpi", "data": kpi.model_dump(mode="json")})

        incidents = [i.model_dump(mode="json") for i in store.get_incidents()]
        await websocket.send_json({"event": "incidents_snapshot", "data": incidents})

        predictions = [p.model_dump(mode="json") for p in store.get_predictions()]
        await websocket.send_json({"event": "predictions_snapshot", "data": predictions})

        agents = [a.model_dump(mode="json") for a in store.get_agent_states()]
        await websocket.send_json({"event": "agents_snapshot", "data": agents})

        logs = [m.model_dump(mode="json") for m in store.get_a2a_log(50)]
        await websocket.send_json({"event": "log_snapshot", "data": logs})

        # Keep alive
        while True:
            await asyncio.sleep(30)
            await websocket.send_json({"event": "ping"})

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception:
        websocket_manager.disconnect(websocket)


# ─── KPIs ────────────────────────────────────────────────────────────────

@router.get("/api/kpi")
async def get_kpi():
    return store.get_kpi().model_dump(mode="json")


# ─── Incidents ───────────────────────────────────────────────────────────

@router.get("/api/incidents")
async def get_incidents(status: Optional[str] = Query(None)):
    return [i.model_dump(mode="json") for i in store.get_incidents(status)]

@router.post("/api/incidents/simulate")
async def simulate_incident(request: Request, incident_type: str = "oom"):
    """Inject a simulated incident through the full agent pipeline."""
    orchestrator = request.app.state.orchestrator
    await orchestrator.simulate_incident(incident_type)
    return {"status": "triggered", "incident_type": incident_type}


# ─── Predictions ─────────────────────────────────────────────────────────

@router.get("/api/predictions")
async def get_predictions():
    return [p.model_dump(mode="json") for p in store.get_predictions()]


# ─── Agents ──────────────────────────────────────────────────────────────

@router.get("/api/agents")
async def get_agents():
    return [a.model_dump(mode="json") for a in store.get_agent_states()]


# ─── A2A Log ────────────────────────────────────────────────────────────

@router.get("/api/logs")
async def get_logs(limit: int = Query(100, le=500)):
    logs = store.get_a2a_log(limit)
    return [m.model_dump(mode="json") for m in logs]


# ─── Metrics ─────────────────────────────────────────────────────────────

@router.get("/api/metrics/hosts")
async def get_host_metrics():
    return [m.model_dump(mode="json") for m in store.get_latest_host_metrics(20)]

@router.get("/api/metrics/apps")
async def get_app_metrics():
    return [m.model_dump(mode="json") for m in store.get_latest_app_metrics()]


# ─── Health ──────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return {"status": "ok", "agents": len(store.agent_states), "incidents": len(store.incidents)}

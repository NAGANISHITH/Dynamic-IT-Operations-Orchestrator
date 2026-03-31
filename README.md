# Autonomous IT Ops Platform
### Multi-Agent AI System for Real-Time IT Infrastructure Management

---

## Overview

This platform deploys **7 autonomous AI agents** that continuously monitor enterprise IT infrastructure, coordinate through an **Agent-to-Agent (A2A) message bus**, predict failures using an **LSTM ensemble**, and execute auto-remediation — all without human intervention.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AGENT PIPELINE                                  │
│                                                                     │
│  [Server Monitor] ──┐                                               │
│  [Cloud Monitor]  ──┼──► [Predictive Failure] ──► [Remediation] ──► [Reporting]
│  [App Health]     ──┘         (LSTM·72h)            [Deployment]    (SLA·KPI)
│                                                                     │
│           ◄────────── A2A Event Bus (async) ─────────────►         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
multi-agent-itops/
│
├── backend/                        # FastAPI Python backend
│   ├── main.py                     # App entry point + lifespan management
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── agents/                     # All AI agent implementations
│   │   ├── base.py                 # BaseAgent: send/receive/run interface
│   │   ├── monitoring.py           # ServerMonitor, CloudMonitor, AppHealth
│   │   ├── predictive.py           # PredictiveFailureAgent (LSTM simulation)
│   │   ├── remediation.py          # RemediationAgent + DeploymentAgent
│   │   ├── reporting.py            # ReportingAgent (SLA + KPI broadcast)
│   │   └── orchestrator.py         # AgentOrchestrator (wires all agents)
│   │
│   ├── api/
│   │   └── routes.py               # REST endpoints + WebSocket /ws
│   │
│   ├── models/
│   │   └── schemas.py              # All Pydantic data models
│   │
│   ├── data/
│   │   └── store.py                # In-memory data store (DB simulation)
│   │
│   └── services/
│       └── websocket_manager.py    # WebSocket broadcast manager
│
├── frontend/                       # React frontend
│   ├── package.json
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── App.jsx                 # Main app + all view components
│       ├── App.css                 # Global styles
│       ├── index.js                # React entry point
│       ├── hooks/
│       │   └── useWebSocket.js     # Auto-reconnecting WebSocket hook
│       └── services/
│           └── api.js              # REST API client
│
└── docker-compose.yml              # Full stack deployment
```

---

## Tech Stack

### Backend
| Layer | Technology |
|---|---|
| API framework | FastAPI (async) |
| Real-time | WebSockets (native FastAPI) |
| Agent runtime | asyncio — concurrent task loops |
| Data store | In-memory (swap for PostgreSQL + TimescaleDB) |
| ML simulation | LSTM scoring logic (swap for PyTorch/TensorFlow) |
| Deployment | Uvicorn ASGI |

### Frontend
| Layer | Technology |
|---|---|
| Framework | React 18 |
| Charts | Recharts |
| Real-time | Native WebSocket with auto-reconnect |
| Icons | Lucide React |
| Styling | Pure CSS-in-JS (no Tailwind dependency) |

---

## Quick Start

### Option 1 — Docker Compose (recommended)

```bash
git clone <repo>
cd multi-agent-itops
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

### Option 2 — Run locally (two terminals)

**Terminal 1 — Backend**
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend**
```bash
cd frontend
npm install
npm start
```

Frontend runs at http://localhost:3000, proxies API to port 8000.

---

## REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check + agent count |
| GET | `/api/kpi` | Current KPI snapshot |
| GET | `/api/incidents` | All incidents (optional `?status=`) |
| POST | `/api/incidents/simulate?incident_type=oom` | Trigger simulated incident |
| GET | `/api/predictions` | Active failure predictions |
| GET | `/api/agents` | All agent states + status |
| GET | `/api/logs?limit=100` | Recent A2A messages |
| GET | `/api/metrics/hosts` | Latest host metrics |
| GET | `/api/metrics/apps` | Latest app metrics |
| WS | `/ws` | Real-time event stream |

### Simulate Incident Types
```bash
curl -X POST "http://localhost:8000/api/incidents/simulate?incident_type=oom"
curl -X POST "http://localhost:8000/api/incidents/simulate?incident_type=cpu"
curl -X POST "http://localhost:8000/api/incidents/simulate?incident_type=network"
curl -X POST "http://localhost:8000/api/incidents/simulate?incident_type=latency"
curl -X POST "http://localhost:8000/api/incidents/simulate?incident_type=disk"
```

---

## WebSocket Event Types

Connect to `ws://localhost:8000/ws` to receive:

```jsonc
// On connect — full snapshots
{ "event": "incidents_snapshot",   "data": [...] }
{ "event": "predictions_snapshot", "data": [...] }
{ "event": "agents_snapshot",      "data": [...] }
{ "event": "log_snapshot",         "data": [...] }
{ "event": "kpi",                  "data": { ... } }

// Streaming updates
{ "event": "incident",        "data": { Incident } }
{ "event": "incident_update", "data": { id, status, ... } }
{ "event": "prediction",      "data": { Prediction } }
{ "event": "a2a_log",         "data": { A2AMessage } }
{ "event": "metric",          "data": { type, host/service, ... } }
{ "event": "kpi",             "data": { KPISnapshot } }
```

---

## Agent Architecture

### BaseAgent
```python
class BaseAgent(ABC):
    async def send(self, to: AgentType, payload: dict) -> A2AMessage
    async def receive(self, msg: A2AMessage)
    async def run(self)   # main loop — must be implemented
```

### Agent Responsibilities

| Agent | Loop interval | Input | Output |
|---|---|---|---|
| ServerMonitorAgent | 15s | Host metrics (CPU/mem/disk) | Alert → Predictive |
| CloudMonitorAgent | 20s | Cloud telemetry (packet loss, latency) | Alert → Predictive |
| AppHealthAgent | 12s | App metrics (p99, error rate) | Alert → Predictive |
| PredictiveFailureAgent | Event-driven | Alert payloads | Prediction + Incident → Remediation |
| RemediationAgent | Event-driven | Incident directive | Runbook steps → Deployment |
| DeploymentAgent | Event-driven | Deploy action | K8s/Terraform ops → Reporting |
| ReportingAgent | 10s | Store state | KPI broadcast |

---

## A2A Message Flow

```
ServerMonitor ──alert──► Predictive ──directive──► Remediation ──action──► Deployment ──resolved──► Reporting
                              │                                                                          │
                              └──────────────────── prediction broadcast ──────────────────────────────►│
                                                                                                        ▼
                                                                                               SLA + KPI update
```

Every message is:
1. Persisted to the in-memory store
2. Broadcast over WebSocket to all connected frontend clients
3. Delivered to the target agent's inbox queue

---

## Data Models

### Incident
```python
class Incident(BaseModel):
    id: str                    # "INC-XXXX"
    severity: Severity         # P1 | P2 | P3
    title: str
    failure_class: FailureClass
    status: IncidentStatus     # open | triaging | remediating | preempting | resolved
    host: Optional[str]
    region: Optional[str]
    agent_chain: List[AgentType]
    opened_at: datetime
    resolved_at: Optional[datetime]
    mttr_seconds: Optional[float]
    runbook: Optional[str]
    auto_resolved: bool
```

### Prediction
```python
class Prediction(BaseModel):
    failure_class: FailureClass
    target: str
    probability: float         # 0.0–1.0
    horizon_minutes: int
    signal_description: str
    recommended_runbook: str
```

---

## Supported Failure Classes & Runbooks

| Failure Class | Severity | Runbook | Action |
|---|---|---|---|
| OOMKill | P1 | oom-001 | Heap limit increase + pod scale-out |
| CPUSaturation | P2 | hpa-scale | HPA scale-out (K8s) |
| NetworkDegradation | P2 | vpc-reroute | BGP reroute to backup AZ |
| LatencySpike | P2 | db-throttle | Read replica promote + ETL throttle |
| DiskPressure | P2 | disk-cleanup | Log rotation + compression |
| CertExpiry | P3 | cert-renew | ACM auto-renewal trigger |
| ReplicaLag | P2 | db-throttle | Replication lag remediation |
| KafkaLag | P3 | kafka-rebalance | Partition rebalance + consumer scale |

---

## Production Upgrade Path

| Component | Dev (current) | Production |
|---|---|---|
| Data store | In-memory dict | PostgreSQL + TimescaleDB |
| ML model | Scoring simulation | PyTorch LSTM / MLflow |
| Message bus | asyncio Queue | Apache Kafka / RabbitMQ |
| Agent runtime | asyncio tasks | Celery / Ray |
| Auth | None | OAuth2 / JWT |
| Secrets | Env vars | HashiCorp Vault |
| Deployment | Docker Compose | Kubernetes Helm chart |
| Observability | WebSocket logs | Prometheus + Grafana + Jaeger |

---

## Frontend Views

| Tab | Description |
|---|---|
| Agent Topology | Animated SVG showing all agents + live A2A flow lines + agent status cards |
| Incidents | Live incident board with severity badges, agent chain, simulate button |
| Predictions | LSTM failure predictions with probability bars and recommended runbooks |
| A2A Log Stream | Real-time message bus feed + JSON payload inspector |
| Live Metrics | Host resource charts (CPU/mem/disk), app latency charts, host table |
| Architecture | Tech stack detail cards + 4-step workflow pipeline diagram |

---

## License
MIT — free to use, extend, and deploy.

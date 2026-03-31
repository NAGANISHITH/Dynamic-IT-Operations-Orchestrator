# Architecture — Autonomous Multi-Agent IT Ops Platform

## 1. System Overview

The platform is a **fully autonomous, event-driven multi-agent system** built to manage enterprise IT infrastructure in real time. Seven specialized AI agents continuously monitor infrastructure, collaborate over an in-process **Agent-to-Agent (A2A) message bus**, predict failures using an **LSTM-inspired scoring model**, and execute automated runbook-driven remediation — all without human intervention.

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                              HIGH-LEVEL SYSTEM VIEW                               │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐  │
│  │                          REACT FRONTEND (Port 3000)                         │  │
│  │  Agent Topology | Incidents | Predictions | A2A Log | Live Metrics | Arch   │  │
│  └─────────────────────┬────────────────────────────┬───────────────────────── ┘  │
│                         │  REST (HTTP/JSON)           │  WebSocket (ws://…/ws)     │
│  ┌─────────────────────▼────────────────────────────▼───────────────────────── ┐  │
│  │                     FASTAPI BACKEND (Port 8000)                              │  │
│  │  ┌──────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                    AGENT ORCHESTRATOR (asyncio)                      │   │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐                     │   │  │
│  │  │  │Server      │  │Cloud       │  │App Health  │  ← Monitoring Tier  │   │  │
│  │  │  │Monitor     │  │Monitor     │  │Agent       │                     │   │  │
│  │  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                     │   │  │
│  │  │        └───────────────┼───────────────┘                             │   │  │
│  │  │                        ▼  A2A alert                                  │   │  │
│  │  │              ┌────────────────────┐                                  │   │  │
│  │  │              │ Predictive Failure │  ← AI/ML Scoring Tier            │   │  │
│  │  │              │ Agent (LSTM 72h)   │                                  │   │  │
│  │  │              └─────────┬──────────┘                                  │   │  │
│  │  │                        ▼  A2A directive                              │   │  │
│  │  │              ┌────────────────────┐                                  │   │  │
│  │  │              │ Remediation Agent  │  ← Decision & Execution Tier     │   │  │
│  │  │              └─────────┬──────────┘                                  │   │  │
│  │  │                        ▼  A2A deploy action                         │   │  │
│  │  │              ┌────────────────────┐                                  │   │  │
│  │  │              │ Deployment Agent   │  ← Infrastructure Execution Tier │   │  │
│  │  │              └─────────┬──────────┘                                  │   │  │
│  │  │                        ▼  A2A resolved                              │   │  │
│  │  │              ┌────────────────────┐                                  │   │  │
│  │  │              │ Reporting Agent   │  ← SLA / KPI Telemetry Tier      │   │  │
│  │  │              └────────────────────┘                                  │   │  │
│  │  │                                                                      │   │  │
│  │  │  ◄──────────────── A2A Event Bus (asyncio Queue) ──────────────────► │   │  │
│  │  └──────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                              │  │
│  │  ┌──────────────┐  ┌──────────────────────┐  ┌────────────────────────┐    │  │
│  │  │ In-Memory    │  │ WebSocket Manager     │  │ REST API (FastAPI      │    │  │
│  │  │ Data Store   │  │ (Broadcast)           │  │ Router)               │    │  │
│  │  └──────────────┘  └──────────────────────┘  └────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────── ┘  │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technology Stack

### 2.1 Backend

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| API Framework | FastAPI | 0.111.0 | Async HTTP + WebSocket server |
| ASGI Server | Uvicorn | 0.29.0 | High-performance Python ASGI runtime |
| Data Validation | Pydantic v2 | 2.7.1 | Schema definitions, serialization |
| Concurrency | Python asyncio | stdlib | Native async agent task loops |
| WebSockets | Native FastAPI WS | — | Real-time push to frontend |
| Data Layer | In-memory dict store | — | Incidents, metrics, predictions, KPIs |
| ML Simulation | LSTM scoring logic | — | Probabilistic failure prediction (PyTorch-ready) |
| Containerization | Docker + Compose | 3.9 | Full-stack deployment |

### 2.2 Frontend

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| Framework | React | 18.2.0 | Component-based UI |
| Build Tool | Create React App | 5.0.1 | Dev server + bundler |
| Charts | Recharts | 2.12.0 | LiveMetrics charts (line, bar, area) |
| Icons | Lucide React | 0.383.0 | Icon set |
| Real-time | Native WebSocket API | — | Auto-reconnecting event stream |
| Styling | Pure CSS-in-JS | — | No external CSS framework dependency |

### 2.3 Networking / Infrastructure

| Layer | Technology | Purpose |
|---|---|---|
| Service Mesh | Docker Compose | Orchestrates backend + frontend containers |
| Reverse Proxy | Nginx (frontend container) | Static asset serving + API proxy |
| Inter-service | HTTP proxy (`:8000`) | Frontend → Backend REST |
| Real-time pipe | WebSocket `/ws` | Backend → Frontend events push |

---

## 3. Repository Structure

```
multi-agent-itops/
│
├── backend/                             # Python FastAPI service
│   ├── main.py                          # App entrypoint + lifespan (asyncio orchestrator start/stop)
│   ├── requirements.txt                 # Python dependencies
│   ├── Dockerfile                       # Backend container image
│   │
│   ├── agents/                          # All agent implementations
│   │   ├── base.py                      # BaseAgent ABC: send / receive / run
│   │   ├── monitoring.py                # ServerMonitorAgent, CloudMonitorAgent, AppHealthAgent
│   │   ├── predictive.py                # PredictiveFailureAgent (LSTM scoring)
│   │   ├── remediation.py               # RemediationAgent + DeploymentAgent
│   │   ├── reporting.py                 # ReportingAgent (SLA + KPI broadcast)
│   │   ├── root_cause.py                # RootCauseAgent (correlates logs & events)
│   │   ├── security.py                  # SecurityAgent (anomaly & intrusion detection)
│   │   ├── optimization.py              # OptimizationAgent (cloud cost analysis)
│   │   ├── notifications.py             # NotificationAgent (Slack / webhook dispatch)
│   │   └── orchestrator.py              # AgentOrchestrator (wires & starts all agents)
│   │
│   ├── api/
│   │   └── routes.py                    # All REST endpoints + /ws WebSocket
│   │
│   ├── models/
│   │   └── schemas.py                   # Pydantic models: Incident, Prediction, A2AMessage…
│   │
│   ├── data/
│   │   └── store.py                     # In-memory data store (swap → PostgreSQL + TimescaleDB)
│   │
│   └── services/
│       └── websocket_manager.py         # Connection pool + broadcast helper
│
├── frontend/                            # React SPA
│   ├── package.json
│   ├── Dockerfile                       # Multi-stage: build → Nginx serve
│   ├── nginx.conf                       # Nginx config
│   └── src/
│       ├── App.jsx                      # Root component + all views (6 tabs)
│       ├── App.css                      # Global styles
│       ├── index.js                     # React DOM render entry
│       ├── hooks/
│       │   └── useWebSocket.js          # Auto-reconnecting WebSocket hook
│       └── services/
│           └── api.js                   # Axios/fetch REST client wrapper
│
└── docker-compose.yml                   # Full stack definition (backend + frontend)
```

---

## 4. Agent Architecture

### 4.1 BaseAgent (Abstract)

Every agent extends `BaseAgent`, which provides:

```python
class BaseAgent(ABC):
    async def send(self, to: AgentType, payload: dict) -> A2AMessage
    # Persists message → broadcasts over WebSocket → returns A2AMessage

    async def receive(self, msg: A2AMessage)
    # Drops message into agent's asyncio.Queue inbox

    @abstractmethod
    async def run(self)
    # Main event loop — implemented by each specialized agent
```

### 4.2 Agent Registry

| Agent | Class | Loop | Primary Inputs | Primary Outputs |
|---|---|---|---|---|
| **ServerMonitorAgent** | `monitoring.py` | Every 15s | Host CPU/mem/disk (simulated) | Alert → Predictive |
| **CloudMonitorAgent** | `monitoring.py` | Every 20s | Cloud packet loss / latency / cost | Alert → Predictive |
| **AppHealthAgent** | `monitoring.py` | Every 12s | App p99 latency / error rate / RPS | Alert → Predictive |
| **PredictiveFailureAgent** | `predictive.py` | Event-driven + 30s sweep | Alert payloads from monitors | Prediction + Incident → Remediation |
| **RemediationAgent** | `remediation.py` | Event-driven | Incident directives | Runbook steps → Deployment |
| **DeploymentAgent** | `remediation.py` | Event-driven | Deploy action commands | K8s/Terraform ops → Resolved + Reporting |
| **ReportingAgent** | `reporting.py` | Every 10s | Store state snapshot | KPI broadcast over WebSocket |
| **RootCauseAgent** | `root_cause.py` | Event-driven (inbox) | Incident + failure class | RCA explanation → Reporting + Notification |
| **SecurityAgent** | `security.py` | Every 45s | Traffic/access log simulation | SecurityAnomaly → Reporting + Notification webhook |
| **OptimizationAgent** | `optimization.py` | Every 60s | Cloud cost metrics | Optimization suggestions → Reporting |

### 4.3 AgentOrchestrator

The `AgentOrchestrator` class:
1. **Instantiates** all agents in the correct dependency order (Deployment → Remediation → Predictive → Monitors → Reporting)
2. **Wraps** each monitor agent's `send()` with a router that:
   - Persists the `A2AMessage` to the store
   - Broadcasts it over WebSocket to all frontend clients
   - Delivers it directly to the target agent's inbox queue
3. **Launches** all agent `run()` coroutines concurrently via `asyncio.gather()`

---

## 5. A2A Message Bus

### 5.1 Message Structure

```python
class A2AMessage(BaseModel):
    id: str                     # UUID[:8] — short unique ID
    from_agent: AgentType       # Source agent enum
    to_agent: AgentType         # Target agent enum
    payload: dict               # Arbitrary JSON payload
    timestamp: datetime         # UTC timestamp
```

### 5.2 Full Message Flow

```
ServerMonitorAgent ─── alert ──────────────────────────────────────────────────────────────────────────► PredictiveFailureAgent
CloudMonitorAgent  ─── alert ──────────────────────────────────────────────────────────────────────────►      │
AppHealthAgent     ─── alert ──────────────────────────────────────────────────────────────────────────►      │
                                                                                                               │  LSTM score
                                                                                                               ▼
                                                                                                    ┌─────────────────────┐
                                                                                                    │ Prediction created  │
                                                                                                    │ Incident opened     │
                                                                                                    └─────────┬───────────┘
                                                                                                              │  directive
                                                                                                              ▼
                                                                                               RemediationAgent (runbook steps)
                                                                                                              │  deploy action
                                                                                                              ▼
                                                                                               DeploymentAgent (K8s/Terraform)
                                                                                                              │  resolved
                                                                                                              ▼
                                                                                               ReportingAgent → KPI broadcast
```

Every message is:
1. **Persisted** to the in-memory store (`data/store.py`)
2. **Broadcast** over WebSocket to all connected frontend clients
3. **Delivered** to the target agent's `asyncio.Queue` inbox

---

## 6. Data Models

### 6.1 Core Enums

| Enum | Values |
|---|---|
| `Severity` | P1 (critical), P2 (high), P3 (medium) |
| `IncidentStatus` | open → triaging → remediating → preempting → resolved |
| `AgentStatus` | active, busy, idle |
| `AgentType` | server_monitor, cloud_monitor, app_health, predictive, remediation, deployment, reporting |
| `FailureClass` | OOMKill, CPUSaturation, NetworkDegradation, LatencySpike, DiskPressure, CertExpiry, ReplicaLag, KafkaLag |

### 6.2 Incident Model

```
Incident
├── id             (INC-XXXX)
├── severity       (P1/P2/P3)
├── title
├── description
├── failure_class
├── status
├── host / region
├── agent_chain    (list of agents that handled it)
├── opened_at / resolved_at
├── mttr_seconds   (Mean Time To Resolve)
├── runbook
└── auto_resolved  (always true in this platform)
```

### 6.3 Prediction Model

```
Prediction
├── id
├── failure_class
├── target         (host / service / region)
├── probability    (0.0–1.0 LSTM score)
├── horizon_minutes (time to failure window)
├── signal_description
├── recommended_runbook
├── triggered_at
└── acted_on
```

### 6.4 KPI Snapshot

```
KPISnapshot
├── uptime_pct
├── active_incidents
├── resolved_24h
├── avg_mttr_minutes
├── sla_adherence_pct
└── timestamp
```

---

## 7. Predictive Failure Engine

The `PredictiveFailureAgent` simulates an LSTM ensemble:

1. **Deduplication**: Same `host + alert_type` within 60 s is ignored
2. **Scoring formula**:
   ```
   overshoot = (value - threshold) / threshold
   base_prob  = min(0.97, 0.60 + overshoot × 0.8 + jitter[-0.05, +0.05])
   ```
3. **Horizon**: `horizon = max(5, 120 - overshoot×60 ± jitter)`
4. **Dispatch**: If `base_prob > 0.55` → create `Incident` + send directive to `RemediationAgent`
5. **Autonomous sweep**: Every 30 s, proactively scans latest host metrics for `mem > 88%` or `cpu > 88%`

### Runbook Mapping

| Alert Type | Failure Class | Severity | Runbook |
|---|---|---|---|
| mem | OOMKill | P1 | oom-001 |
| cpu | CPUSaturation | P2 | hpa-scale |
| disk | DiskPressure | P2 | disk-cleanup |
| packet_loss | NetworkDegradation | P2 | vpc-reroute |
| latency | LatencySpike | P2 | db-throttle |
| error_rate | LatencySpike | P3 | rollback-deploy |

---

## 8. Remediation & Deployment Pipeline

### 8.1 RemediationAgent

- Waits on inbox queue (60 s timeout)
- Executes multi-step runbooks (policy-approved with simulated delays 0.8–2.0 s per step)
- Dispatches deploy actions to `DeploymentAgent`

### 8.2 DeploymentAgent

- Simulates Kubernetes / Terraform / Ansible execution (2–5 s per action)
- Marks incident as `resolved`
- Reports MTTR to `ReportingAgent`
- Triggers KPI broadcast

### 8.3 Supported Runbooks

| Runbook ID | Failure Class | Actions |
|---|---|---|
| `oom-001` | OOMKill | Heap limit increase + pod scale-out +2 |
| `hpa-scale` | CPUSaturation | HPA update 4→9 replicas |
| `vpc-reroute` | NetworkDegradation | BGP reroute to backup AZ |
| `db-throttle` | LatencySpike / ReplicaLag | Read replica promote + ETL throttle 40% |
| `disk-cleanup` | DiskPressure | Log rotation + compression (18 GB freed) |
| `cert-renew` | CertExpiry | ACM auto-renewal + DNS validation |
| `kafka-rebalance` | KafkaLag | Partition rebalance + consumer scale +4 |
| `rollback-deploy` | Error spike | kubectl rollout undo to previous version |

---

## 9. REST API & WebSocket Endpoints

### 9.1 REST Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Platform health + agent count |
| GET | `/api/kpi` | Current KPI snapshot |
| GET | `/api/incidents` | All incidents (filter `?status=`) |
| POST | `/api/incidents/simulate?incident_type=` | Inject simulated incident |
| GET | `/api/predictions` | Active failure predictions |
| GET | `/api/agents` | All agent states |
| GET | `/api/logs?limit=100` | Recent A2A messages |
| GET | `/api/metrics/hosts` | Latest host metrics |
| GET | `/api/metrics/apps` | Latest app metrics |

### 9.2 WebSocket Event Stream (`/ws`)

**On connection (full snapshots):**

| Event | Payload |
|---|---|
| `incidents_snapshot` | `[...Incident]` |
| `predictions_snapshot` | `[...Prediction]` |
| `agents_snapshot` | `[...AgentState]` |
| `log_snapshot` | `[...A2AMessage]` |
| `kpi` | `KPISnapshot` |

**Streaming updates:**

| Event | Payload |
|---|---|
| `incident` | New Incident |
| `incident_update` | `{id, status, mttr_seconds}` |
| `prediction` | New Prediction |
| `a2a_log` | A2AMessage |
| `metric` | `{type, host/service, ...values}` |
| `kpi` | Updated KPISnapshot |
| `security_anomaly` | SecurityAnomaly |
| `cost_metric` | CostMetric |
| `optimization_suggestion` | OptimizationSuggestion |

---

## 10. Frontend Architecture

The React SPA is a single `App.jsx` with six tabbed views:

| Tab | Component | Key Data Source |
|---|---|---|
| **Agent Topology** | Animated SVG graph | WebSocket `agents_snapshot` + `a2a_log` |
| **Incidents** | Live incident board | WebSocket `incidents_snapshot` + `incident_update` |
| **Predictions** | LSTM prediction cards | WebSocket `predictions_snapshot` + `prediction` |
| **A2A Log Stream** | Real-time message feed | WebSocket `log_snapshot` + `a2a_log` |
| **Live Metrics** | Host + app charts (Recharts) | WebSocket `metric` events |
| **Architecture** | Tech stack reference | Static content |

### WebSocket Hook (`useWebSocket.js`)
- Auto-reconnects on disconnect with exponential backoff
- Dispatches incoming events to component state via `onMessage` callback

---

## 11. Deployment Architecture

### 11.1 Docker Compose (Current)

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    healthcheck: curl /health every 10s

  frontend:
    build: ./frontend          # React build → Nginx serve
    ports: ["3000:80"]
    depends_on: backend
    env:
      REACT_APP_API_URL: http://localhost:8000
      REACT_APP_WS_URL: ws://localhost:8000
```

### 11.2 Production Upgrade Path

| Component | Dev (Current) | Production Target |
|---|---|---|
| Data store | In-memory dict | PostgreSQL + TimescaleDB |
| ML model | Scoring simulation | PyTorch LSTM / MLflow |
| Message bus | asyncio Queue | Apache Kafka / RabbitMQ |
| Agent runtime | asyncio tasks | Celery / Ray |
| Auth | None | OAuth2 / JWT (FastAPI Security) |
| Secrets | Env vars | HashiCorp Vault |
| Deployment | Docker Compose | Kubernetes Helm chart |
| Observability | WebSocket logs | Prometheus + Grafana + Jaeger |

---

## 12. Key Design Decisions

| Decision | Rationale |
|---|---|
| **asyncio throughout** | Single-threaded event loop eliminates locking; all agents co-exist in one process |
| **A2A message bus as asyncio.Queue** | Zero-latency in-process delivery; swappable with Kafka for production |
| **In-memory data store** | Zero infra dependency for demo/dev; all interfaces designed for easy DB swap |
| **WebSocket-first push** | Frontend always receives data; no polling overhead |
| **LSTM simulation without PyTorch** | Allows demo without GPU dependency; algorithm logic is production-equivalent |
| **Pydantic v2 models** | Strict schema validation + fast JSON serialization across all layers |
| **Docker multi-stage frontend build** | Minimal Nginx image; no Node.js runtime in production container |

---

*Generated: 2026-03-28 | Multi-Agent IT Ops Platform v1.0.0*

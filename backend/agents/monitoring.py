"""
Monitoring Agents: Server Monitor, Cloud Monitor, App Health
Each continuously generates simulated telemetry and emits A2A events.
"""

import asyncio
import random
from datetime import datetime

from agents.base import BaseAgent
from models.schemas import (
    AgentType, HostMetric, CloudMetric, AppMetric, AgentStatus
)
from data.store import store
from services.websocket_manager import websocket_manager


HOSTS = [
    "payment-api-pod-1","payment-api-pod-2","payment-api-pod-3",
    "auth-service","db-primary","db-replica-1","db-replica-2",
    "search-cluster-1","search-cluster-2","redis-master",
    "kafka-broker-1","kafka-broker-2","api-gateway",
]

SERVICES = [
    "payment-api","auth-service","db-primary","search-cluster",
    "redis","kafka-consumer","api-gateway","notification-svc",
]

CLOUD_REGIONS = [
    ("AWS","us-east-1","EC2"),("AWS","eu-west-2","RDS"),
    ("AWS","us-west-2","VPC"),("Azure","eu-north-1","AKS"),
    ("GCP","ap-southeast-1","GKE"),("AWS","ap-southeast-1","Lambda"),
]


class ServerMonitorAgent(BaseAgent):
    """Polls hosts for CPU/mem/disk metrics. Emits alerts to Predictive agent."""

    def __init__(self):
        super().__init__(AgentType.SERVER_MONITOR)
        self._mem_trend = {"payment-api-pod-3": 85.0}  # simulate growing mem

    async def run(self):
        while True:
            await store.update_agent_status(self.agent_type, AgentStatus.BUSY)
            for host in HOSTS:
                # Gradually increase payment-api mem to simulate OOM
                if host == "payment-api-pod-3":
                    self._mem_trend[host] = min(98.0, self._mem_trend[host] + random.uniform(0.3, 0.8))
                    mem = self._mem_trend[host]
                else:
                    mem = random.uniform(40, 78)

                cpu = random.uniform(20, 94) if host == "search-cluster-1" else random.uniform(15, 60)
                disk = random.uniform(30, 75)

                m = HostMetric(host=host, cpu_pct=round(cpu,1), mem_pct=round(mem,1), disk_pct=round(disk,1))
                await store.add_host_metric(m)

                # Broadcast metric tick
                await websocket_manager.broadcast("metric", {
                    "type": "host",
                    "host": host,
                    "cpu_pct": m.cpu_pct,
                    "mem_pct": m.mem_pct,
                    "disk_pct": m.disk_pct,
                })

                # Alert threshold crossed → send to predictive
                if mem > 85.0 or cpu > 90.0 or disk > 85.0:
                    alert_type = "mem" if mem > 85.0 else ("cpu" if cpu > 90.0 else "disk")
                    alert_val = mem if alert_type == "mem" else (cpu if alert_type == "cpu" else disk)
                    await self.send(AgentType.PREDICTIVE, {
                        "alert_type": alert_type,
                        "host": host,
                        "value": round(alert_val, 1),
                        "threshold": 85.0,
                        "metrics": {"cpu": m.cpu_pct, "mem": m.mem_pct, "disk": m.disk_pct},
                    })

                await asyncio.sleep(0.05)

            await store.update_agent_status(self.agent_type, AgentStatus.ACTIVE)
            await asyncio.sleep(15)


class CloudMonitorAgent(BaseAgent):
    """Monitors cloud providers for network/latency/cost metrics."""

    def __init__(self):
        super().__init__(AgentType.CLOUD_MONITOR)
        self._packet_loss_sim = 0.0

    async def run(self):
        while True:
            await store.update_agent_status(self.agent_type, AgentStatus.BUSY)
            for provider, region, service in CLOUD_REGIONS:
                # Occasionally spike packet loss for us-west-2
                if region == "us-west-2" and random.random() < 0.08:
                    self._packet_loss_sim = round(random.uniform(2.0, 5.0), 2)
                else:
                    self._packet_loss_sim = max(0.0, self._packet_loss_sim - 0.5)

                latency = random.uniform(5, 30) + (80 if self._packet_loss_sim > 1 else 0)
                m = CloudMetric(
                    provider=provider, region=region, service=service,
                    packet_loss_pct=self._packet_loss_sim,
                    latency_ms=round(latency, 1),
                    cost_usd_day=round(random.uniform(300, 800), 2),
                )
                await store.add_cloud_metric(m)
                await websocket_manager.broadcast("metric", {
                    "type": "cloud",
                    "provider": provider,
                    "region": region,
                    "packet_loss_pct": m.packet_loss_pct,
                    "latency_ms": m.latency_ms,
                })

                if m.packet_loss_pct > 1.0:
                    await self.send(AgentType.PREDICTIVE, {
                        "alert_type": "packet_loss",
                        "region": region,
                        "provider": provider,
                        "value": m.packet_loss_pct,
                        "threshold": 1.0,
                    })

            await store.update_agent_status(self.agent_type, AgentStatus.ACTIVE)
            await asyncio.sleep(20)


class AppHealthAgent(BaseAgent):
    """Monitors application-level telemetry: latency, error rate, RPS."""

    def __init__(self):
        super().__init__(AgentType.APP_HEALTH)
        self._p99_trend = {"payment-api": 450.0}

    async def run(self):
        while True:
            await store.update_agent_status(self.agent_type, AgentStatus.BUSY)
            for svc in SERVICES:
                if svc == "payment-api":
                    # Gradually degrade latency
                    self._p99_trend[svc] = min(1200.0, self._p99_trend.get(svc, 450.0) + random.uniform(5, 15))
                    p99 = self._p99_trend[svc]
                else:
                    p99 = random.uniform(50, 400)

                err = random.uniform(0.0, 0.8)
                rps = random.uniform(100, 2000)
                replicas = random.randint(2, 9)

                m = AppMetric(service=svc, p99_ms=round(p99,1), error_rate_pct=round(err,2), rps=round(rps,0), replica_count=replicas)
                await store.add_app_metric(m)
                await websocket_manager.broadcast("metric", {
                    "type": "app",
                    "service": svc,
                    "p99_ms": m.p99_ms,
                    "error_rate_pct": m.error_rate_pct,
                    "rps": m.rps,
                    "replica_count": m.replica_count,
                })

                if p99 > 800 or err > 0.5:
                    await self.send(AgentType.PREDICTIVE, {
                        "alert_type": "latency" if p99 > 800 else "error_rate",
                        "service": svc,
                        "value": p99 if p99 > 800 else err,
                        "threshold": 800 if p99 > 800 else 0.5,
                        "metrics": {"p99_ms": m.p99_ms, "error_rate": m.error_rate_pct},
                    })

            await store.update_agent_status(self.agent_type, AgentStatus.ACTIVE)
            await asyncio.sleep(12)

"""
Remediation Agent — applies policy-approved fixes.
Deployment Agent — executes infrastructure changes (K8s, Terraform, Ansible).
"""

import asyncio
import random
from datetime import datetime

from agents.base import BaseAgent
from models.schemas import (
    AgentType, AgentStatus, IncidentStatus, Severity
)
from data.store import store
from services.websocket_manager import websocket_manager


# Runbook execution plans
RUNBOOK_STEPS = {
    "oom-001": [
        "Evaluating policy matrix for OOMKill runbook",
        "Auto-approval granted · P1 within SLA budget",
        "Dispatching heap limit increase to Deployment Agent",
        "Dispatching pod scale-out +2 replicas",
        "Confirming new pods healthy",
    ],
    "hpa-scale": [
        "Evaluating HPA scale-out policy",
        "Auto-approval granted · CPU > 90% sustained",
        "Dispatching HPA update to Deployment Agent",
        "Waiting for pod rollout completion",
        "Verifying CPU normalisation",
    ],
    "vpc-reroute": [
        "Network degradation detected · checking CMDB for backup routes",
        "Backup AZ identified · dispatching traffic reroute",
        "BGP route update applied",
        "Packet loss confirmed 0.0%",
    ],
    "db-throttle": [
        "Analysing DB dependency graph via CMDB",
        "Identifying upstream write contention sources",
        "Throttling batch ETL job write rate to 40%",
        "Promoting read replica for query offload",
        "Monitoring replication lag recovery",
    ],
    "cert-renew": [
        "TLS certificate expiry detected",
        "Triggering ACM auto-renewal",
        "DNS validation record created",
        "Certificate renewed · deployed to load balancer",
    ],
    "kafka-rebalance": [
        "Consumer group lag detected",
        "Triggering partition rebalance",
        "Consumer threads scaled +4",
        "Lag recovering · offset convergence in progress",
    ],
    "rollback-deploy": [
        "Error rate spike · checking recent deployments",
        "Identified bad deployment: v2.4.1 (rolled out 8m ago)",
        "Initiating rollback to v2.4.0",
        "Rollback complete · error rate normalising",
    ],
    "disk-cleanup": [
        "Disk pressure detected · scanning log volumes",
        "Identified 18 GB stale log files > 7 days",
        "Triggering automated log rotation + compression",
        "Disk usage reduced from 86% to 61%",
    ],
}

DEPLOY_ACTIONS = {
    "oom-001":       [("scale_out", "replicas +2"), ("configmap_patch", "heap_limit=4096m")],
    "hpa-scale":     [("hpa_update", "4→9 replicas")],
    "vpc-reroute":   [("bgp_reroute", "backup-az activated")],
    "db-throttle":   [("read_replica_promote", "replica-1"), ("etl_throttle", "rate=40%")],
    "cert-renew":    [("acm_renew", "cert-arn-us-east-1")],
    "kafka-rebalance":[("partition_rebalance", "group-1"), ("consumer_scale", "+4 threads")],
    "rollback-deploy":[("kubectl_rollout_undo", "deployment/app v2.4.0")],
    "disk-cleanup":  [("log_rotation", "18 GB freed")],
}


class RemediationAgent(BaseAgent):
    def __init__(self, deployment_agent=None):
        super().__init__(AgentType.REMEDIATION)
        self.deployment_agent = deployment_agent

    async def run(self):
        while True:
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=60)
                await self._execute(msg)
            except asyncio.TimeoutError:
                pass

    async def _execute(self, msg):
        await store.update_agent_status(self.agent_type, AgentStatus.BUSY)
        p = msg.payload
        inc_id = p.get("incident_id")
        runbook = p.get("runbook", "oom-001")
        target = p.get("target", "unknown")
        severity = p.get("severity", "P2")

        # Update incident to remediating
        await store.update_incident(inc_id, status=IncidentStatus.REMEDIATING,
                                    agent_chain=[AgentType.SERVER_MONITOR,
                                                  AgentType.PREDICTIVE,
                                                  AgentType.REMEDIATION])
        await websocket_manager.broadcast("incident_update", {"id": inc_id, "status": "remediating"})

        steps = RUNBOOK_STEPS.get(runbook, ["Executing remediation runbook"])
        for step in steps:
            await asyncio.sleep(random.uniform(0.8, 2.0))
            await self.send(AgentType.REMEDIATION, {
                "step": step,
                "incident_id": inc_id,
                "runbook": runbook,
                "target": target,
            })

        # Dispatch deploy actions
        deploy_actions = DEPLOY_ACTIONS.get(runbook, [])
        for action, detail in deploy_actions:
            dep_payload = {
                "incident_id": inc_id,
                "action": action,
                "target": target,
                "detail": detail,
                "runbook": runbook,
            }
            await self.send(AgentType.DEPLOYMENT, dep_payload)
            if self.deployment_agent:
                from models.schemas import A2AMessage
                fake = A2AMessage(
                    from_agent=self.agent_type,
                    to_agent=AgentType.DEPLOYMENT,
                    payload=dep_payload,
                )
                await self.deployment_agent.receive(fake)

        await store.update_agent_status(self.agent_type, AgentStatus.ACTIVE)


class DeploymentAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.DEPLOYMENT)

    async def run(self):
        while True:
            try:
                msg = await asyncio.wait_for(self._inbox.get(), timeout=60)
                await self._apply(msg)
            except asyncio.TimeoutError:
                pass

    async def _apply(self, msg):
        await store.update_agent_status(self.agent_type, AgentStatus.BUSY)
        p = msg.payload
        inc_id = p.get("incident_id")
        action = p.get("action", "unknown")
        detail = p.get("detail", "")

        # Simulate deployment time
        await asyncio.sleep(random.uniform(2.0, 5.0))

        # Resolve incident
        inc = await store.update_incident(inc_id, status=IncidentStatus.RESOLVED)
        if inc:
            mttr = inc.mttr_seconds or random.uniform(60, 300)
            await websocket_manager.broadcast("incident_update", {
                "id": inc_id,
                "status": "resolved",
                "mttr_seconds": round(mttr, 1),
                "auto_resolved": True,
            })

        await self.send(AgentType.REPORTING, {
            "incident_id": inc_id,
            "action": action,
            "detail": detail,
            "status": "resolved",
            "mttr_seconds": inc.mttr_seconds if inc else None,
        })

        # Broadcast updated KPIs
        kpi = store.get_kpi()
        await websocket_manager.broadcast("kpi", kpi.model_dump(mode="json"))
        await store.update_agent_status(self.agent_type, AgentStatus.ACTIVE)

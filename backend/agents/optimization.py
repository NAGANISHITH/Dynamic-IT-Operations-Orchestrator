"""
Optimization Agent.
Analyzes usage and suggests cost-saving strategies across multi-cloud infrastructure.
"""

import asyncio
import random
from datetime import datetime
from .base import BaseAgent
from models.schemas import AgentType, CostMetric, OptimizationSuggestion
from services.websocket_manager import websocket_manager

class OptimizationAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentType.OPTIMIZATION)

    async def run(self):
        print(f"Agent {self.agent_type.value} started.")
        while True:
            # Periodically generate cost metrics and suggestions
            await self._update_costs()
            await self._check_for_optimizations()
            await asyncio.sleep(60)

    async def _update_costs(self):
        from data.store import store
        providers = ["AWS", "Azure", "GCP"]
        res_types = ["EC2", "RDS", "VM", "Storage"]
        
        for _ in range(5):
            m = CostMetric(
                provider=random.choice(providers),
                resource_id=f"res-{random.randint(100, 999)}",
                resource_type=random.choice(res_types),
                daily_cost=round(random.uniform(5, 150), 2),
                utilization_pct=round(random.uniform(10, 95), 2),
            )
            m.is_underutilized = m.utilization_pct < 30
            await store.add_cost_metric(m)
            await websocket_manager.broadcast("cost_metric", m.model_dump(mode="json"))

    async def _check_for_optimizations(self):
        from data.store import store
        if random.random() < 0.3:  # 30% chance to find a new optimization
            sugg = OptimizationSuggestion(
                title=f"Rightsize Underutilized {random.choice(['EC2', 'RDS', 'VM'])}",
                description="Analysis shows this resource is consistently below 20% CPU. Recommend downgrading instance type.",
                estimated_savings_monthly=round(random.uniform(50, 500), 2),
                impact=random.choice(["low", "medium", "high"])
            )
            await store.add_optimization_suggestion(sugg)
            await websocket_manager.broadcast("optimization_suggestion", sugg.model_dump(mode="json"))
            
            await self.send(AgentType.REPORTING, {
                "type": "optimization_suggestion",
                "suggestion_id": sugg.id
            })

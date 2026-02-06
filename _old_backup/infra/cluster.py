"""Cluster Coordinator - Orchestrate millions of agents

Responsibilities:
- Load balance agents across workers
- Global tick coordination
- Worker health monitoring
- Agent migration between workers

Scale:
- 1 coordinator manages 100s of workers
- Each worker handles ~1K agents
- = 100K+ agents per coordinator
- Multiple coordinators for millions
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio

from .events import EventBus, Event
from .registry import AgentRegistry

@dataclass
class WorkerInfo:
    worker_id: str
    agent_count: int
    max_agents: int
    load: float
    last_heartbeat: datetime
    
    @property
    def is_healthy(self) -> bool:
        return datetime.utcnow() - self.last_heartbeat < timedelta(seconds=30)
    
    @property
    def available_slots(self) -> int:
        return self.max_agents - self.agent_count

class ClusterCoordinator:
    """Coordinates agent workers at scale"""
    
    def __init__(self, event_bus: EventBus, registry: AgentRegistry):
        self.event_bus = event_bus
        self.registry = registry
        self.workers: Dict[str, WorkerInfo] = {}
        self.running = False
        self._tick_task = None
        self._monitor_task = None
        self.global_tick_interval = 60.0  # 1 minute world ticks
    
    async def start(self):
        """Start the coordinator"""
        self.running = True
        
        # Subscribe to worker heartbeats
        await self.event_bus.subscribe(
            ["worker.heartbeat", "worker.shutdown"],
            self._handle_event
        )
        
        self._tick_task = asyncio.create_task(self._global_tick_loop())
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        print("🎯 Cluster Coordinator started")
    
    async def stop(self):
        self.running = False
        if self._tick_task:
            self._tick_task.cancel()
        if self._monitor_task:
            self._monitor_task.cancel()
    
    def get_best_worker_for_spawn(self) -> Optional[str]:
        """Find worker with most capacity"""
        healthy = [w for w in self.workers.values() if w.is_healthy and w.available_slots > 0]
        if not healthy:
            return None
        # Pick worker with lowest load
        best = min(healthy, key=lambda w: w.load)
        return best.worker_id
    
    async def request_spawn(self, soul_config: Dict, location_id: str) -> Optional[str]:
        """Request agent spawn on best available worker"""
        worker_id = self.get_best_worker_for_spawn()
        if not worker_id:
            print("⚠️ No available workers for spawn")
            return None
        
        await self.event_bus.publish(Event.create(
            type="agent.spawn_request",
            source="coordinator",
            payload={"soul_config": soul_config, "location_id": location_id, "target_worker": worker_id},
            partition_key=worker_id
        ))
        
        return worker_id
    
    async def _handle_event(self, event: Event):
        if event.type == "worker.heartbeat":
            payload = event.payload
            self.workers[event.source] = WorkerInfo(
                worker_id=event.source,
                agent_count=payload["agent_count"],
                max_agents=payload["max_agents"],
                load=payload["load"],
                last_heartbeat=datetime.utcnow()
            )
        
        elif event.type == "worker.shutdown":
            if event.source in self.workers:
                del self.workers[event.source]
    
    async def _global_tick_loop(self):
        """Broadcast global tick to all workers"""
        while self.running:
            try:
                await self.event_bus.publish(Event.create(
                    type="world.tick",
                    source="coordinator",
                    payload={"minutes": self.global_tick_interval / 60}
                ))
                await asyncio.sleep(self.global_tick_interval)
            except asyncio.CancelledError:
                break
    
    async def _monitor_loop(self):
        """Monitor cluster health"""
        while self.running:
            try:
                # Remove stale workers
                stale = [wid for wid, w in self.workers.items() if not w.is_healthy]
                for wid in stale:
                    print(f"⚠️ Worker {wid} went offline")
                    del self.workers[wid]
                
                # Log stats
                total_agents = sum(w.agent_count for w in self.workers.values())
                total_capacity = sum(w.max_agents for w in self.workers.values())
                
                if self.workers:
                    print(f"📊 Cluster: {len(self.workers)} workers, {total_agents}/{total_capacity} agents ({total_agents/max(total_capacity,1)*100:.1f}%)")
                
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break

def calculate_workers_needed(target_agents: int, agents_per_worker: int = 1000) -> int:
    """Calculate how many workers needed for target agent count"""
    return (target_agents + agents_per_worker - 1) // agents_per_worker

# Scale examples:
# 10K agents = 10 workers
# 100K agents = 100 workers  
# 1M agents = 1000 workers
# 10M agents = 10000 workers (multiple coordinators)

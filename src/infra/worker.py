"""Agent Worker - Run agents at scale

One worker can handle ~1000 agents.
Deploy multiple workers horizontally.
Workers are stateless - state lives in DB/Redis.

Architecture:
┌─────────────────────────────────────────────────────┐
│                    CLUSTER                           │
├─────────────┬─────────────┬─────────────────────────┤
│  Worker 1   │  Worker 2   │  Worker N               │
│  ~1K agents │  ~1K agents │  ~1K agents             │
├─────────────┴─────────────┴─────────────────────────┤
│              Event Bus (NATS/Kafka)                  │
├─────────────────────────────────────────────────────┤
│  PostgreSQL (state)    Redis (cache/realtime)       │
└─────────────────────────────────────────────────────┘
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from datetime import datetime
import asyncio
import uuid
import os

from .events import EventBus, Event, LocalEventBus
from .registry import AgentRegistry, AgentRecord, LocalRegistry

@dataclass
class WorkerConfig:
    worker_id: str = field(default_factory=lambda: f"worker_{uuid.uuid4().hex[:8]}")
    max_agents: int = 1000
    tick_interval: float = 1.0  # seconds
    heartbeat_interval: float = 10.0

class AgentWorker:
    """Runs a batch of agents on one server"""
    
    def __init__(
        self,
        config: WorkerConfig,
        event_bus: EventBus,
        registry: AgentRegistry
    ):
        self.config = config
        self.event_bus = event_bus
        self.registry = registry
        self.agents: Dict[str, "Agent"] = {}  # Active agents on this worker
        self.running = False
        self._tick_task = None
        self._heartbeat_task = None
    
    @property
    def agent_count(self) -> int:
        return len(self.agents)
    
    @property
    def can_accept_more(self) -> bool:
        return self.agent_count < self.config.max_agents
    
    async def start(self):
        """Start the worker"""
        self.running = True
        
        # Subscribe to events
        await self.event_bus.subscribe(
            ["agent.spawn_request", "agent.message", "world.tick"],
            self._handle_event
        )
        
        # Start tick loop
        self._tick_task = asyncio.create_task(self._tick_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        print(f"🚀 Worker {self.config.worker_id} started (max {self.config.max_agents} agents)")
    
    async def stop(self):
        """Stop the worker"""
        self.running = False
        
        # Mark all agents as offline
        for agent_id in self.agents:
            await self.registry.set_status(agent_id, "offline")
        
        if self._tick_task:
            self._tick_task.cancel()
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        print(f"⏹️ Worker {self.config.worker_id} stopped")
    
    async def spawn_agent(self, agent: "Agent") -> bool:
        """Spawn an agent on this worker"""
        if not self.can_accept_more:
            return False
        
        self.agents[agent.id] = agent
        
        # Register in global registry
        record = AgentRecord(
            agent_id=agent.id,
            name=agent.name,
            soul_hash=hash(str(agent.soul.__dict__)),
            current_persona=agent.personas.current,
            location_id=agent.location,
            server_id=self.config.worker_id,
            last_active=datetime.utcnow(),
            status="online"
        )
        await self.registry.register(record)
        
        # Emit spawn event
        await self.event_bus.publish(Event.create(
            type="agent.spawned",
            source=self.config.worker_id,
            payload={"agent_id": agent.id, "name": agent.name},
            partition_key=agent.location
        ))
        
        return True
    
    async def remove_agent(self, agent_id: str):
        """Remove agent from this worker"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            await self.registry.set_status(agent_id, "offline")
    
    async def _handle_event(self, event: Event):
        """Handle incoming events"""
        if event.type == "agent.message":
            # Route message to agent
            target = event.payload.get("target_agent")
            if target and target in self.agents:
                agent = self.agents[target]
                agent.perceive(event.payload)
        
        elif event.type == "world.tick":
            # Tick all agents (usually triggered by cluster coordinator)
            minutes = event.payload.get("minutes", 1.0)
            for agent in self.agents.values():
                agent.tick(minutes)
    
    async def _tick_loop(self):
        """Regular tick for agent updates"""
        while self.running:
            try:
                # Update agent states
                for agent_id, agent in list(self.agents.items()):
                    # Check drives, maybe trigger actions
                    if agent.drives.state.pressures.get('social', 0) > 0.7:
                        # Agent wants to speak - would trigger LLM
                        pass
                
                await asyncio.sleep(self.config.tick_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Tick error: {e}")
    
    async def _heartbeat_loop(self):
        """Send heartbeats to registry"""
        while self.running:
            try:
                # Update all agents' last_active
                for agent_id in self.agents:
                    await self.registry.set_status(agent_id, "online")
                
                # Publish worker stats
                await self.event_bus.publish(Event.create(
                    type="worker.heartbeat",
                    source=self.config.worker_id,
                    payload={
                        "agent_count": self.agent_count,
                        "max_agents": self.config.max_agents,
                        "load": self.agent_count / self.config.max_agents
                    }
                ))
                
                await asyncio.sleep(self.config.heartbeat_interval)
            except asyncio.CancelledError:
                break

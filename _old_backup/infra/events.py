"""Event Bus - Scale to millions of agents

Architecture:
- Local: asyncio queues (dev)
- Production: NATS JetStream / Kafka / Redis Streams

Each agent doesn't talk directly - events flow through bus.
Allows horizontal scaling across servers.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
import asyncio
import json
import uuid

@dataclass
class Event:
    id: str
    type: str
    timestamp: datetime
    source: str  # agent_id or "system"
    payload: Dict[str, Any]
    partition_key: Optional[str] = None  # For ordered processing (e.g., location_id)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "payload": self.payload,
            "partition_key": self.partition_key
        }
    
    @classmethod
    def create(cls, type: str, source: str, payload: Dict, partition_key: str = None) -> "Event":
        return cls(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            type=type,
            timestamp=datetime.utcnow(),
            source=source,
            payload=payload,
            partition_key=partition_key
        )

class EventBus(ABC):
    """Abstract event bus - implement for different backends"""
    
    @abstractmethod
    async def publish(self, event: Event):
        """Publish event to bus"""
        pass
    
    @abstractmethod
    async def subscribe(self, event_types: List[str], handler: Callable):
        """Subscribe to event types"""
        pass
    
    @abstractmethod
    async def start(self):
        """Start the event bus"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the event bus"""
        pass

class LocalEventBus(EventBus):
    """In-memory event bus for development/testing"""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        self.queue: asyncio.Queue = None
        self.running = False
        self._task = None
    
    async def publish(self, event: Event):
        if self.queue:
            await self.queue.put(event)
    
    async def subscribe(self, event_types: List[str], handler: Callable):
        for et in event_types:
            if et not in self.handlers:
                self.handlers[et] = []
            self.handlers[et].append(handler)
    
    async def start(self):
        self.queue = asyncio.Queue()
        self.running = True
        self._task = asyncio.create_task(self._process())
    
    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
    
    async def _process(self):
        while self.running:
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                handlers = self.handlers.get(event.type, []) + self.handlers.get("*", [])
                for handler in handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        print(f"Handler error: {e}")
            except asyncio.TimeoutError:
                continue

class RedisEventBus(EventBus):
    """Redis Streams event bus for production scale
    
    - Supports millions of events/sec
    - Consumer groups for horizontal scaling
    - Persistence and replay
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.client = None
        self.handlers: Dict[str, List[Callable]] = {}
        self.consumer_group = "clawbots"
        self.consumer_name = f"consumer_{uuid.uuid4().hex[:8]}"
        self.running = False
    
    async def connect(self):
        import redis.asyncio as redis
        self.client = redis.from_url(self.redis_url)
    
    async def publish(self, event: Event):
        if not self.client:
            await self.connect()
        
        stream = f"events:{event.partition_key or 'global'}"
        await self.client.xadd(stream, event.to_dict())
    
    async def subscribe(self, event_types: List[str], handler: Callable):
        for et in event_types:
            if et not in self.handlers:
                self.handlers[et] = []
            self.handlers[et].append(handler)
    
    async def start(self):
        if not self.client:
            await self.connect()
        self.running = True
        # Create consumer group, start consuming
        # (Simplified - production would have proper consumer group setup)
    
    async def stop(self):
        self.running = False
        if self.client:
            await self.client.close()

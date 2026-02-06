"""
ClawBots Event System

Handles event creation, routing, and subscription.
"""

from typing import Optional, Dict, List, Any, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import json


class EventType(Enum):
    """Types of world events."""
    # Agent events
    AGENT_SPAWN = "agent_spawn"
    AGENT_DESPAWN = "agent_despawn"
    AGENT_MOVE = "agent_move"
    AGENT_TELEPORT = "agent_teleport"
    AGENT_STATUS = "agent_status"
    
    # Communication events
    SPEECH = "speech"
    WHISPER = "whisper"
    EMOTE = "emote"
    
    # Interaction events
    OBJECT_USE = "object_use"
    ITEM_GIVE = "item_give"
    ITEM_RECEIVE = "item_receive"
    
    # World events
    WORLD_TICK = "world_tick"
    REGION_CHANGE = "region_change"
    WEATHER_CHANGE = "weather_change"
    
    # System events
    SYSTEM_MESSAGE = "system_message"
    ERROR = "error"


@dataclass
class WorldEvent:
    """A single world event."""
    id: str
    type: EventType
    source: str  # agent_id, "world", or "system"
    timestamp: datetime
    tick: int
    
    # Location context
    region: Optional[str] = None
    position: Optional[Dict[str, float]] = None
    radius: Optional[float] = None  # Visibility radius
    
    # Event data
    data: Dict[str, Any] = field(default_factory=dict)
    
    # Privacy
    private: bool = False
    visible_to: Optional[Set[str]] = None  # If set, only these agents see it
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "tick": self.tick,
            "region": self.region,
            "position": self.position,
            "radius": self.radius,
            "data": self.data,
            "private": self.private
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldEvent":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            type=EventType(data["type"]),
            source=data["source"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tick=data["tick"],
            region=data.get("region"),
            position=data.get("position"),
            radius=data.get("radius"),
            data=data.get("data", {}),
            private=data.get("private", False)
        )


class EventFilter:
    """Filter for event subscriptions."""
    
    def __init__(
        self,
        event_types: Optional[List[EventType]] = None,
        regions: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        exclude_self: bool = True
    ):
        self.event_types = set(event_types) if event_types else None
        self.regions = set(regions) if regions else None
        self.sources = set(sources) if sources else None
        self.exclude_self = exclude_self
    
    def matches(self, event: WorldEvent, subscriber_id: str) -> bool:
        """Check if event matches this filter."""
        # Exclude own events if requested
        if self.exclude_self and event.source == subscriber_id:
            return False
        
        # Check event type
        if self.event_types and event.type not in self.event_types:
            return False
        
        # Check region
        if self.regions and event.region and event.region not in self.regions:
            return False
        
        # Check source
        if self.sources and event.source not in self.sources:
            return False
        
        return True


@dataclass
class Subscription:
    """A subscriber's event subscription."""
    subscriber_id: str
    filter: EventFilter
    callback: Callable[[WorldEvent], None]
    created_at: datetime = field(default_factory=datetime.utcnow)


class EventBus:
    """
    Central event bus for the world.
    
    Features:
    - Publish events
    - Subscribe with filters
    - Event history
    - Spatial filtering (only see nearby events)
    """
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.history: List[WorldEvent] = []
        self.subscriptions: Dict[str, List[Subscription]] = {}
        self.event_counter: int = 0
        self.current_tick: int = 0
        
        # Async event queue for non-blocking publishing
        self.queue: asyncio.Queue = asyncio.Queue()
        self.running: bool = False
    
    # ========== PUBLISHING ==========
    
    def create_event(
        self,
        event_type: EventType,
        source: str,
        data: Dict[str, Any] = None,
        region: Optional[str] = None,
        position: Optional[Dict[str, float]] = None,
        radius: Optional[float] = None,
        private: bool = False,
        visible_to: Optional[Set[str]] = None
    ) -> WorldEvent:
        """Create a new event."""
        self.event_counter += 1
        
        return WorldEvent(
            id=f"evt_{self.event_counter}",
            type=event_type,
            source=source,
            timestamp=datetime.utcnow(),
            tick=self.current_tick,
            region=region,
            position=position,
            radius=radius,
            data=data or {},
            private=private,
            visible_to=visible_to
        )
    
    async def publish(self, event: WorldEvent) -> None:
        """Publish an event to all matching subscribers."""
        # Add to history
        self.history.append(event)
        if len(self.history) > self.history_size:
            self.history = self.history[-self.history_size:]
        
        # Notify subscribers
        for subscriber_id, subs in self.subscriptions.items():
            for sub in subs:
                if self._can_receive(event, subscriber_id, sub.filter):
                    try:
                        if asyncio.iscoroutinefunction(sub.callback):
                            await sub.callback(event)
                        else:
                            sub.callback(event)
                    except Exception as e:
                        print(f"Event callback error for {subscriber_id}: {e}")
    
    def publish_sync(self, event: WorldEvent) -> None:
        """Synchronous publish (adds to queue)."""
        self.queue.put_nowait(event)
    
    async def process_queue(self) -> None:
        """Process queued events."""
        self.running = True
        while self.running:
            try:
                event = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                await self.publish(event)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Event queue error: {e}")
    
    def _can_receive(
        self,
        event: WorldEvent,
        subscriber_id: str,
        filter: EventFilter
    ) -> bool:
        """Check if subscriber can receive this event."""
        # Check visibility restrictions
        if event.visible_to and subscriber_id not in event.visible_to:
            return False
        
        # Check filter
        if not filter.matches(event, subscriber_id):
            return False
        
        return True
    
    # ========== SUBSCRIPTIONS ==========
    
    def subscribe(
        self,
        subscriber_id: str,
        callback: Callable[[WorldEvent], None],
        filter: Optional[EventFilter] = None
    ) -> str:
        """Subscribe to events."""
        if subscriber_id not in self.subscriptions:
            self.subscriptions[subscriber_id] = []
        
        sub = Subscription(
            subscriber_id=subscriber_id,
            filter=filter or EventFilter(),
            callback=callback
        )
        
        self.subscriptions[subscriber_id].append(sub)
        return f"sub_{subscriber_id}_{len(self.subscriptions[subscriber_id])}"
    
    def unsubscribe(self, subscriber_id: str) -> bool:
        """Remove all subscriptions for a subscriber."""
        if subscriber_id in self.subscriptions:
            del self.subscriptions[subscriber_id]
            return True
        return False
    
    # ========== HISTORY QUERIES ==========
    
    def get_history(
        self,
        limit: int = 100,
        event_types: Optional[List[EventType]] = None,
        region: Optional[str] = None,
        since_tick: int = 0
    ) -> List[WorldEvent]:
        """Get event history with optional filters."""
        results = []
        
        for event in reversed(self.history):
            if len(results) >= limit:
                break
            
            if event.tick < since_tick:
                continue
            
            if event_types and event.type not in event_types:
                continue
            
            if region and event.region != region:
                continue
            
            results.append(event)
        
        return list(reversed(results))
    
    def get_events_for_agent(
        self,
        agent_id: str,
        agent_region: str,
        agent_position: Dict[str, float],
        limit: int = 50,
        since_tick: int = 0
    ) -> List[WorldEvent]:
        """Get events visible to a specific agent."""
        results = []
        
        for event in reversed(self.history):
            if len(results) >= limit:
                break
            
            if event.tick < since_tick:
                continue
            
            # Check visibility
            if event.visible_to and agent_id not in event.visible_to:
                continue
            
            # Check private events
            if event.private:
                if event.data.get("to_id") != agent_id and event.source != agent_id:
                    continue
            
            # Check spatial visibility
            if event.region and event.region != agent_region:
                continue
            
            if event.radius and event.position:
                # Calculate distance
                dx = event.position["x"] - agent_position.get("x", 0)
                dy = event.position["y"] - agent_position.get("y", 0)
                distance = (dx**2 + dy**2) ** 0.5
                if distance > event.radius:
                    continue
            
            results.append(event)
        
        return list(reversed(results))
    
    # ========== CONVENIENCE METHODS ==========
    
    async def emit_speech(
        self,
        speaker_id: str,
        message: str,
        region: str,
        position: Dict[str, float],
        volume: str = "normal"
    ) -> WorldEvent:
        """Emit a speech event."""
        radius_map = {
            "whisper": 3.0,
            "normal": 15.0,
            "shout": 100.0
        }
        
        event = self.create_event(
            event_type=EventType.SPEECH,
            source=speaker_id,
            data={"message": message, "volume": volume},
            region=region,
            position=position,
            radius=radius_map.get(volume, 15.0)
        )
        
        await self.publish(event)
        return event
    
    async def emit_whisper(
        self,
        from_id: str,
        to_id: str,
        message: str
    ) -> WorldEvent:
        """Emit a private whisper event."""
        event = self.create_event(
            event_type=EventType.WHISPER,
            source=from_id,
            data={"message": message, "to_id": to_id},
            private=True,
            visible_to={from_id, to_id}
        )
        
        await self.publish(event)
        return event
    
    async def emit_emote(
        self,
        agent_id: str,
        action: str,
        region: str,
        position: Dict[str, float]
    ) -> WorldEvent:
        """Emit an emote event."""
        event = self.create_event(
            event_type=EventType.EMOTE,
            source=agent_id,
            data={"action": action},
            region=region,
            position=position,
            radius=20.0
        )
        
        await self.publish(event)
        return event
    
    async def emit_movement(
        self,
        agent_id: str,
        from_pos: Dict[str, float],
        to_pos: Dict[str, float],
        region: str
    ) -> WorldEvent:
        """Emit a movement event."""
        event = self.create_event(
            event_type=EventType.AGENT_MOVE,
            source=agent_id,
            data={"from": from_pos, "to": to_pos},
            region=region,
            position=to_pos,
            radius=30.0
        )
        
        await self.publish(event)
        return event
    
    async def emit_spawn(
        self,
        agent_id: str,
        agent_name: str,
        region: str,
        position: Dict[str, float]
    ) -> WorldEvent:
        """Emit an agent spawn event."""
        event = self.create_event(
            event_type=EventType.AGENT_SPAWN,
            source=agent_id,
            data={"name": agent_name},
            region=region,
            position=position,
            radius=50.0
        )
        
        await self.publish(event)
        return event
    
    async def emit_despawn(
        self,
        agent_id: str,
        region: str,
        position: Dict[str, float]
    ) -> WorldEvent:
        """Emit an agent despawn event."""
        event = self.create_event(
            event_type=EventType.AGENT_DESPAWN,
            source=agent_id,
            data={},
            region=region,
            position=position,
            radius=50.0
        )
        
        await self.publish(event)
        return event
    
    def set_tick(self, tick: int) -> None:
        """Update current tick."""
        self.current_tick = tick
    
    def stop(self) -> None:
        """Stop event processing."""
        self.running = False

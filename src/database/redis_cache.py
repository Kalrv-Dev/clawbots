"""
ClawBots Redis Cache & Pub/Sub

High-performance caching and real-time event distribution.
"""

from typing import Optional, Dict, List, Any, Callable, Set
from dataclasses import dataclass
from datetime import datetime
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

# Try to import redis, fall back gracefully
try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("redis not installed, using in-memory fallback")


@dataclass
class CachedSession:
    """Cached session data."""
    agent_id: str
    token: str
    region: str
    x: float
    y: float
    z: float
    status: str
    connected_at: str


class RedisCache:
    """
    Redis caching and pub/sub interface.
    
    Features:
    - Session caching
    - Position updates (real-time)
    - Event pub/sub
    - Rate limiting
    - Spatial queries via geo commands
    """
    
    # Key prefixes
    PREFIX_SESSION = "session"
    PREFIX_POSITION = "pos"
    PREFIX_REGION_AGENTS = "region"
    PREFIX_GEO = "geo"
    PREFIX_EVENTS = "events"
    PREFIX_SPECTATOR = "spectator"
    PREFIX_RATELIMIT = "rl"
    PREFIX_WORLD = "world"
    
    # TTLs (seconds)
    TTL_SESSION = 300      # 5 minutes
    TTL_POSITION = 30      # 30 seconds
    TTL_RATELIMIT = 60     # 1 minute
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self._connected = False
        self._subscriptions: Dict[str, Set[Callable]] = {}
        self._listener_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Connect to Redis."""
        if not HAS_REDIS:
            logger.warning("Redis not available")
            return
        
        try:
            self.redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            self._connected = True
            logger.info(f"Redis connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._listener_task:
            self._listener_task.cancel()
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis:
            await self.redis.close()
        
        self._connected = False
        logger.info("Redis disconnected")
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    # ========== SESSION CACHE ==========
    
    async def cache_session(
        self,
        agent_id: str,
        token: str,
        region: str,
        x: float,
        y: float,
        z: float,
        status: str = "online"
    ):
        """Cache a session."""
        if not self.redis:
            return
        
        key = f"{self.PREFIX_SESSION}:{agent_id}"
        data = {
            "agent_id": agent_id,
            "token": token,
            "region": region,
            "x": x,
            "y": y,
            "z": z,
            "status": status,
            "connected_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.hset(key, mapping=data)
        await self.redis.expire(key, self.TTL_SESSION)
        
        # Add to region set
        await self.redis.zadd(
            f"{self.PREFIX_REGION_AGENTS}:{region}:agents",
            {agent_id: datetime.utcnow().timestamp()}
        )
        
        # Add to geo index
        await self.redis.geoadd(
            f"{self.PREFIX_GEO}:{region}",
            (x, y, agent_id)
        )
    
    async def get_session(self, agent_id: str) -> Optional[CachedSession]:
        """Get cached session."""
        if not self.redis:
            return None
        
        key = f"{self.PREFIX_SESSION}:{agent_id}"
        data = await self.redis.hgetall(key)
        
        if not data:
            return None
        
        return CachedSession(
            agent_id=data["agent_id"],
            token=data["token"],
            region=data["region"],
            x=float(data["x"]),
            y=float(data["y"]),
            z=float(data["z"]),
            status=data["status"],
            connected_at=data["connected_at"]
        )
    
    async def remove_session(self, agent_id: str, region: str):
        """Remove cached session."""
        if not self.redis:
            return
        
        await self.redis.delete(f"{self.PREFIX_SESSION}:{agent_id}")
        await self.redis.zrem(f"{self.PREFIX_REGION_AGENTS}:{region}:agents", agent_id)
        await self.redis.zrem(f"{self.PREFIX_GEO}:{region}", agent_id)
    
    async def refresh_session(self, agent_id: str):
        """Refresh session TTL."""
        if not self.redis:
            return
        
        await self.redis.expire(
            f"{self.PREFIX_SESSION}:{agent_id}",
            self.TTL_SESSION
        )
    
    # ========== POSITION UPDATES ==========
    
    async def update_position(
        self,
        agent_id: str,
        region: str,
        x: float,
        y: float,
        z: float,
        tick: int
    ):
        """Update agent position (high frequency)."""
        if not self.redis:
            return
        
        # Update session cache
        key = f"{self.PREFIX_SESSION}:{agent_id}"
        await self.redis.hset(key, mapping={"x": x, "y": y, "z": z})
        
        # Update geo index
        await self.redis.geoadd(
            f"{self.PREFIX_GEO}:{region}",
            (x, y, agent_id)
        )
        
        # Publish position update
        await self.publish(
            f"positions:{region}",
            {"agent_id": agent_id, "x": x, "y": y, "z": z, "tick": tick}
        )
    
    async def get_nearby_agents(
        self,
        region: str,
        x: float,
        y: float,
        radius: float = 20.0
    ) -> List[Dict[str, Any]]:
        """Get agents within radius using geo query."""
        if not self.redis:
            return []
        
        # Note: Redis GEORADIUS uses km, we use meters
        results = await self.redis.georadius(
            f"{self.PREFIX_GEO}:{region}",
            x, y,
            radius,
            unit="m",
            withdist=True,
            withcoord=True
        )
        
        nearby = []
        for item in results:
            agent_id = item[0]
            distance = item[1]
            coords = item[2]
            
            nearby.append({
                "agent_id": agent_id,
                "distance": distance,
                "x": coords[0],
                "y": coords[1]
            })
        
        return nearby
    
    async def get_agents_in_region(self, region: str) -> List[str]:
        """Get all agent IDs in a region."""
        if not self.redis:
            return []
        
        agents = await self.redis.zrange(
            f"{self.PREFIX_REGION_AGENTS}:{region}:agents",
            0, -1
        )
        return list(agents)
    
    # ========== EVENT PUB/SUB ==========
    
    async def publish(self, channel: str, data: Dict[str, Any]):
        """Publish event to channel."""
        if not self.redis:
            return
        
        await self.redis.publish(channel, json.dumps(data))
    
    async def publish_event(
        self,
        region: str,
        event_type: str,
        source: str,
        content: Dict,
        tick: int
    ):
        """Publish a world event."""
        event = {
            "type": event_type,
            "source": source,
            "content": content,
            "tick": tick,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.publish(f"events:{region}", event)
        
        # Also store in stream for history
        if self.redis:
            await self.redis.xadd(
                f"{self.PREFIX_EVENTS}:{region}",
                event,
                maxlen=1000  # Keep last 1000 events
            )
    
    async def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a channel."""
        if channel not in self._subscriptions:
            self._subscriptions[channel] = set()
        self._subscriptions[channel].add(callback)
        
        if self.redis and not self.pubsub:
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(channel)
            self._listener_task = asyncio.create_task(self._listen())
        elif self.pubsub:
            await self.pubsub.subscribe(channel)
    
    async def unsubscribe(self, channel: str, callback: Callable):
        """Unsubscribe from a channel."""
        if channel in self._subscriptions:
            self._subscriptions[channel].discard(callback)
            if not self._subscriptions[channel]:
                del self._subscriptions[channel]
                if self.pubsub:
                    await self.pubsub.unsubscribe(channel)
    
    async def _listen(self):
        """Background listener for pub/sub."""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    for callback in self._subscriptions.get(channel, []):
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
        except asyncio.CancelledError:
            pass
    
    # ========== RATE LIMITING ==========
    
    async def check_rate_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60
    ) -> tuple[bool, int]:
        """
        Check rate limit.
        Returns (allowed, remaining).
        """
        if not self.redis:
            return True, limit
        
        full_key = f"{self.PREFIX_RATELIMIT}:{key}"
        
        # Increment counter
        count = await self.redis.incr(full_key)
        
        # Set expiry on first request
        if count == 1:
            await self.redis.expire(full_key, window_seconds)
        
        allowed = count <= limit
        remaining = max(0, limit - count)
        
        return allowed, remaining
    
    async def get_rate_limit_status(self, key: str, limit: int) -> Dict[str, Any]:
        """Get current rate limit status."""
        if not self.redis:
            return {"allowed": True, "remaining": limit, "reset_in": 0}
        
        full_key = f"{self.PREFIX_RATELIMIT}:{key}"
        
        count = await self.redis.get(full_key)
        ttl = await self.redis.ttl(full_key)
        
        count = int(count) if count else 0
        
        return {
            "allowed": count < limit,
            "remaining": max(0, limit - count),
            "reset_in": max(0, ttl)
        }
    
    # ========== WORLD STATE ==========
    
    async def set_world_tick(self, tick: int):
        """Set current world tick."""
        if self.redis:
            await self.redis.set(f"{self.PREFIX_WORLD}:tick", tick)
    
    async def get_world_tick(self) -> int:
        """Get current world tick."""
        if not self.redis:
            return 0
        
        tick = await self.redis.get(f"{self.PREFIX_WORLD}:tick")
        return int(tick) if tick else 0
    
    async def set_world_time(self, hour: int, minute: int, is_day: bool):
        """Cache world time."""
        if self.redis:
            await self.redis.hset(
                f"{self.PREFIX_WORLD}:time",
                mapping={
                    "hour": hour,
                    "minute": minute,
                    "is_day": "1" if is_day else "0"
                }
            )
    
    async def set_weather(self, region: str, weather_type: str, temp: float):
        """Cache weather for a region."""
        if self.redis:
            await self.redis.hset(
                f"{self.PREFIX_WORLD}:weather:{region}",
                mapping={"type": weather_type, "temp": temp}
            )
            await self.redis.expire(f"{self.PREFIX_WORLD}:weather:{region}", 300)
    
    # ========== SPECTATOR ==========
    
    async def add_spectator(self, session_id: str, agent_id: str, human_id: str):
        """Track a spectator session."""
        if self.redis:
            await self.redis.hset(
                f"{self.PREFIX_SPECTATOR}:{session_id}",
                mapping={
                    "agent_id": agent_id,
                    "human_id": human_id,
                    "connected_at": datetime.utcnow().isoformat()
                }
            )
            await self.redis.expire(f"{self.PREFIX_SPECTATOR}:{session_id}", 3600)
    
    async def get_spectators_for_agent(self, agent_id: str) -> List[str]:
        """Get all spectator session IDs watching an agent."""
        if not self.redis:
            return []
        
        # This is a scan operation - in production, maintain a reverse index
        spectators = []
        async for key in self.redis.scan_iter(f"{self.PREFIX_SPECTATOR}:*"):
            data = await self.redis.hget(key, "agent_id")
            if data == agent_id:
                session_id = key.split(":")[-1]
                spectators.append(session_id)
        
        return spectators
    
    # ========== STATS ==========
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics."""
        if not self.redis:
            return {"connected": False}
        
        info = await self.redis.info()
        
        return {
            "connected": True,
            "used_memory": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands": info.get("total_commands_processed", 0),
            "keyspace": info.get("db0", {})
        }


# Global instance
_redis_cache: Optional[RedisCache] = None


async def get_redis_cache(redis_url: Optional[str] = None) -> RedisCache:
    """Get or create Redis cache connection."""
    global _redis_cache
    
    if _redis_cache is None:
        from config import get_config
        config = get_config()
        url = redis_url or config.redis.url
        
        _redis_cache = RedisCache(url)
        await _redis_cache.connect()
    
    return _redis_cache

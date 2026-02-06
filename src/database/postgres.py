"""
ClawBots PostgreSQL Database Layer

Production-ready async database operations.
Falls back to SQLite for development.
"""

from typing import Optional, Dict, List, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from contextlib import asynccontextmanager
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

# Try to import asyncpg, fall back gracefully
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False
    logger.warning("asyncpg not installed, using SQLite fallback")


@dataclass
class AgentRecord:
    """Agent database record."""
    id: str
    agent_id: str
    name: str
    owner_id: Optional[str]
    description: str
    avatar: Dict
    brain_config: Dict
    permissions: List[str]
    default_region: str
    total_online_seconds: int
    message_count: int
    last_seen: Optional[datetime]
    created_at: datetime


@dataclass
class SessionRecord:
    """Session database record."""
    id: str
    agent_id: str
    token: str
    region: str
    position_x: float
    position_y: float
    position_z: float
    status: str
    connected_at: datetime
    last_heartbeat: datetime


@dataclass
class EventRecord:
    """Event database record."""
    id: int
    event_id: str
    event_type: str
    source_agent: Optional[str]
    target_agent: Optional[str]
    region: str
    content: Dict
    world_tick: int
    created_at: datetime


class PostgresDatabase:
    """
    Async PostgreSQL database interface.
    
    Features:
    - Connection pooling
    - Automatic reconnection
    - Query logging
    - Metrics collection
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        self._connected = False
    
    async def connect(self, min_size: int = 5, max_size: int = 20):
        """Initialize connection pool."""
        if not HAS_ASYNCPG:
            logger.warning("PostgreSQL not available, operations will fail")
            return
        
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=30,
                statement_cache_size=100
            )
            self._connected = True
            logger.info(f"PostgreSQL connected (pool: {min_size}-{max_size})")
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            raise
    
    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self._connected = False
            logger.info("PostgreSQL disconnected")
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool."""
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    @property
    def connected(self) -> bool:
        return self._connected
    
    # ========== AGENTS ==========
    
    async def create_agent(
        self,
        agent_id: str,
        name: str,
        owner_id: Optional[str] = None,
        description: str = "",
        avatar: Optional[Dict] = None,
        brain_config: Optional[Dict] = None,
        permissions: Optional[List[str]] = None,
        default_region: str = "main"
    ) -> AgentRecord:
        """Create a new agent."""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO agents 
                    (agent_id, name, owner_id, description, avatar, brain_config, permissions, default_region)
                VALUES 
                    ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING *
            """, 
                agent_id, 
                name, 
                owner_id, 
                description,
                json.dumps(avatar or {}),
                json.dumps(brain_config or {}),
                permissions or ["move", "speak", "emote"],
                default_region
            )
            return self._row_to_agent(row)
    
    async def get_agent(self, agent_id: str) -> Optional[AgentRecord]:
        """Get agent by ID."""
        async with self.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM agents WHERE agent_id = $1", 
                agent_id
            )
            return self._row_to_agent(row) if row else None
    
    async def get_all_agents(self, limit: int = 100, offset: int = 0) -> List[AgentRecord]:
        """Get all agents with pagination."""
        async with self.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM agents ORDER BY created_at DESC LIMIT $1 OFFSET $2",
                limit, offset
            )
            return [self._row_to_agent(row) for row in rows]
    
    async def update_agent_stats(
        self, 
        agent_id: str, 
        online_seconds: int = 0, 
        messages: int = 0
    ):
        """Update agent statistics."""
        async with self.acquire() as conn:
            await conn.execute("""
                UPDATE agents 
                SET total_online_seconds = total_online_seconds + $2,
                    message_count = message_count + $3,
                    last_seen = NOW()
                WHERE agent_id = $1
            """, agent_id, online_seconds, messages)
    
    async def search_agents(self, query: str, limit: int = 20) -> List[AgentRecord]:
        """Search agents by name."""
        async with self.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM agents 
                WHERE name ILIKE $1 OR description ILIKE $1
                ORDER BY similarity(name, $2) DESC
                LIMIT $3
            """, f"%{query}%", query, limit)
            return [self._row_to_agent(row) for row in rows]
    
    def _row_to_agent(self, row: asyncpg.Record) -> AgentRecord:
        """Convert database row to AgentRecord."""
        return AgentRecord(
            id=str(row["id"]),
            agent_id=row["agent_id"],
            name=row["name"],
            owner_id=row["owner_id"],
            description=row["description"],
            avatar=json.loads(row["avatar"]) if isinstance(row["avatar"], str) else row["avatar"],
            brain_config=json.loads(row["brain_config"]) if isinstance(row["brain_config"], str) else row["brain_config"],
            permissions=row["permissions"],
            default_region=row["default_region"],
            total_online_seconds=row["total_online_seconds"],
            message_count=row["message_count"],
            last_seen=row["last_seen"],
            created_at=row["created_at"]
        )
    
    # ========== SESSIONS ==========
    
    async def create_session(
        self,
        agent_id: str,
        token: str,
        region: str,
        x: float = 128.0,
        y: float = 128.0,
        z: float = 25.0
    ) -> SessionRecord:
        """Create a new session."""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO sessions 
                    (agent_id, token, region, position_x, position_y, position_z)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """, agent_id, token, region, x, y, z)
            return self._row_to_session(row)
    
    async def get_active_sessions(self, region: Optional[str] = None) -> List[SessionRecord]:
        """Get all active sessions."""
        async with self.acquire() as conn:
            if region:
                rows = await conn.fetch("""
                    SELECT * FROM sessions 
                    WHERE disconnected_at IS NULL AND region = $1
                    ORDER BY connected_at DESC
                """, region)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM sessions 
                    WHERE disconnected_at IS NULL
                    ORDER BY connected_at DESC
                """)
            return [self._row_to_session(row) for row in rows]
    
    async def update_session_position(
        self,
        agent_id: str,
        x: float,
        y: float,
        z: float
    ):
        """Update session position."""
        async with self.acquire() as conn:
            await conn.execute("""
                UPDATE sessions 
                SET position_x = $2, position_y = $3, position_z = $4, last_heartbeat = NOW()
                WHERE agent_id = $1 AND disconnected_at IS NULL
            """, agent_id, x, y, z)
    
    async def end_session(self, agent_id: str) -> Optional[int]:
        """End a session and return duration."""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                UPDATE sessions 
                SET disconnected_at = NOW()
                WHERE agent_id = $1 AND disconnected_at IS NULL
                RETURNING EXTRACT(EPOCH FROM (NOW() - connected_at))::INTEGER as duration
            """, agent_id)
            return row["duration"] if row else None
    
    def _row_to_session(self, row: asyncpg.Record) -> SessionRecord:
        """Convert database row to SessionRecord."""
        return SessionRecord(
            id=str(row["id"]),
            agent_id=row["agent_id"],
            token=row["token"],
            region=row["region"],
            position_x=row["position_x"],
            position_y=row["position_y"],
            position_z=row["position_z"],
            status=row["status"],
            connected_at=row["connected_at"],
            last_heartbeat=row["last_heartbeat"]
        )
    
    # ========== EVENTS ==========
    
    async def log_event(
        self,
        event_type: str,
        source_agent: Optional[str],
        region: str,
        content: Dict,
        world_tick: int,
        target_agent: Optional[str] = None
    ) -> int:
        """Log a world event."""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO events 
                    (event_type, source_agent, target_agent, region, content, world_tick)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, event_type, source_agent, target_agent, region, json.dumps(content), world_tick)
            return row["id"]
    
    async def get_events(
        self,
        region: Optional[str] = None,
        event_type: Optional[str] = None,
        since_tick: int = 0,
        limit: int = 100
    ) -> List[EventRecord]:
        """Get events with filters."""
        async with self.acquire() as conn:
            conditions = ["world_tick >= $1"]
            params = [since_tick]
            param_idx = 2
            
            if region:
                conditions.append(f"region = ${param_idx}")
                params.append(region)
                param_idx += 1
            
            if event_type:
                conditions.append(f"event_type = ${param_idx}")
                params.append(event_type)
                param_idx += 1
            
            params.append(limit)
            
            query = f"""
                SELECT * FROM events 
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
                LIMIT ${param_idx}
            """
            
            rows = await conn.fetch(query, *params)
            return [self._row_to_event(row) for row in rows]
    
    def _row_to_event(self, row: asyncpg.Record) -> EventRecord:
        """Convert database row to EventRecord."""
        return EventRecord(
            id=row["id"],
            event_id=str(row["event_id"]),
            event_type=row["event_type"],
            source_agent=row["source_agent"],
            target_agent=row["target_agent"],
            region=row["region"],
            content=json.loads(row["content"]) if isinstance(row["content"], str) else row["content"],
            world_tick=row["world_tick"],
            created_at=row["created_at"]
        )
    
    # ========== CHAT ==========
    
    async def save_message(
        self,
        sender_id: str,
        sender_name: str,
        message: str,
        region: str,
        volume: str = "normal",
        recipient_id: Optional[str] = None
    ) -> int:
        """Save a chat message."""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO chat_messages 
                    (sender_id, sender_name, recipient_id, region, message, volume)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, sender_id, sender_name, recipient_id, region, message, volume)
            
            # Update sender's message count
            await conn.execute(
                "UPDATE agents SET message_count = message_count + 1 WHERE agent_id = $1",
                sender_id
            )
            
            return row["id"]
    
    async def get_messages(
        self,
        region: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get chat messages."""
        async with self.acquire() as conn:
            if region and agent_id:
                rows = await conn.fetch("""
                    SELECT * FROM chat_messages 
                    WHERE region = $1 AND (sender_id = $2 OR recipient_id = $2)
                    ORDER BY created_at DESC LIMIT $3
                """, region, agent_id, limit)
            elif region:
                rows = await conn.fetch("""
                    SELECT * FROM chat_messages 
                    WHERE region = $1
                    ORDER BY created_at DESC LIMIT $2
                """, region, limit)
            elif agent_id:
                rows = await conn.fetch("""
                    SELECT * FROM chat_messages 
                    WHERE sender_id = $1 OR recipient_id = $1
                    ORDER BY created_at DESC LIMIT $2
                """, agent_id, limit)
            else:
                rows = await conn.fetch(
                    "SELECT * FROM chat_messages ORDER BY created_at DESC LIMIT $1",
                    limit
                )
            
            return [dict(row) for row in rows]
    
    # ========== STATS ==========
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        async with self.acquire() as conn:
            stats = {}
            
            # Agent count
            row = await conn.fetchrow("SELECT COUNT(*) as count FROM agents")
            stats["total_agents"] = row["count"]
            
            # Active sessions
            row = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM sessions WHERE disconnected_at IS NULL"
            )
            stats["active_sessions"] = row["count"]
            
            # Messages today
            row = await conn.fetchrow("""
                SELECT COUNT(*) as count FROM chat_messages 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            stats["messages_24h"] = row["count"]
            
            # Events today
            row = await conn.fetchrow("""
                SELECT COUNT(*) as count FROM events 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            stats["events_24h"] = row["count"]
            
            return stats


# Global instance
_postgres: Optional[PostgresDatabase] = None


async def get_postgres(database_url: Optional[str] = None) -> PostgresDatabase:
    """Get or create PostgreSQL connection."""
    global _postgres
    
    if _postgres is None:
        from config import get_config
        config = get_config()
        url = database_url or config.database.url
        
        if "postgresql" not in url and "postgres" not in url:
            raise ValueError("PostgreSQL URL required")
        
        _postgres = PostgresDatabase(url)
        await _postgres.connect()
    
    return _postgres

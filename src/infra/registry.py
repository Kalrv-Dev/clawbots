"""Agent Registry - Track millions of agents

Stores:
- Agent metadata (soul, current state snapshot)
- Location mapping
- Online/offline status

Backends:
- Local: Dict (dev)
- Production: PostgreSQL + Redis cache
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from datetime import datetime
import json

@dataclass
class AgentRecord:
    agent_id: str
    name: str
    soul_hash: str  # Hash of soul config for versioning
    current_persona: str
    location_id: Optional[str]
    server_id: Optional[str]  # Which server is running this agent
    last_active: datetime
    status: str = "offline"  # online, offline, suspended
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "soul_hash": self.soul_hash,
            "current_persona": self.current_persona,
            "location_id": self.location_id,
            "server_id": self.server_id,
            "last_active": self.last_active.isoformat(),
            "status": self.status
        }

class AgentRegistry(ABC):
    """Abstract registry - implement for different backends"""
    
    @abstractmethod
    async def register(self, record: AgentRecord):
        pass
    
    @abstractmethod
    async def get(self, agent_id: str) -> Optional[AgentRecord]:
        pass
    
    @abstractmethod
    async def update_location(self, agent_id: str, location_id: str):
        pass
    
    @abstractmethod
    async def get_agents_at_location(self, location_id: str) -> List[str]:
        pass
    
    @abstractmethod
    async def set_status(self, agent_id: str, status: str):
        pass

class LocalRegistry(AgentRegistry):
    """In-memory registry for development"""
    
    def __init__(self):
        self.agents: Dict[str, AgentRecord] = {}
        self.location_index: Dict[str, Set[str]] = {}
    
    async def register(self, record: AgentRecord):
        self.agents[record.agent_id] = record
        if record.location_id:
            if record.location_id not in self.location_index:
                self.location_index[record.location_id] = set()
            self.location_index[record.location_id].add(record.agent_id)
    
    async def get(self, agent_id: str) -> Optional[AgentRecord]:
        return self.agents.get(agent_id)
    
    async def update_location(self, agent_id: str, location_id: str):
        record = self.agents.get(agent_id)
        if not record:
            return
        
        # Remove from old location
        if record.location_id and record.location_id in self.location_index:
            self.location_index[record.location_id].discard(agent_id)
        
        # Add to new location
        if location_id not in self.location_index:
            self.location_index[location_id] = set()
        self.location_index[location_id].add(agent_id)
        record.location_id = location_id
    
    async def get_agents_at_location(self, location_id: str) -> List[str]:
        return list(self.location_index.get(location_id, set()))
    
    async def set_status(self, agent_id: str, status: str):
        if agent_id in self.agents:
            self.agents[agent_id].status = status
            self.agents[agent_id].last_active = datetime.utcnow()
    
    async def count(self) -> int:
        return len(self.agents)
    
    async def count_online(self) -> int:
        return sum(1 for a in self.agents.values() if a.status == "online")

class PostgresRegistry(AgentRegistry):
    """PostgreSQL registry for production scale
    
    - Handles millions of agents
    - Efficient location queries with indexes
    - Partitioned tables for scale
    """
    
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None
    
    async def connect(self):
        import asyncpg
        self.pool = await asyncpg.create_pool(self.dsn, min_size=5, max_size=20)
        
        # Create tables
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    soul_hash TEXT,
                    current_persona TEXT,
                    location_id TEXT,
                    server_id TEXT,
                    last_active TIMESTAMPTZ DEFAULT NOW(),
                    status TEXT DEFAULT 'offline'
                );
                CREATE INDEX IF NOT EXISTS idx_agents_location ON agents(location_id);
                CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
            ''')
    
    async def register(self, record: AgentRecord):
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO agents (agent_id, name, soul_hash, current_persona, location_id, server_id, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (agent_id) DO UPDATE SET
                    current_persona = $4, location_id = $5, server_id = $6, status = $7, last_active = NOW()
            ''', record.agent_id, record.name, record.soul_hash, record.current_persona,
                record.location_id, record.server_id, record.status)
    
    async def get(self, agent_id: str) -> Optional[AgentRecord]:
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM agents WHERE agent_id = $1', agent_id)
            if row:
                return AgentRecord(**dict(row))
        return None
    
    async def update_location(self, agent_id: str, location_id: str):
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                'UPDATE agents SET location_id = $1, last_active = NOW() WHERE agent_id = $2',
                location_id, agent_id
            )
    
    async def get_agents_at_location(self, location_id: str) -> List[str]:
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT agent_id FROM agents WHERE location_id = $1 AND status = $2',
                location_id, 'online'
            )
            return [r['agent_id'] for r in rows]
    
    async def set_status(self, agent_id: str, status: str):
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                'UPDATE agents SET status = $1, last_active = NOW() WHERE agent_id = $2',
                status, agent_id
            )

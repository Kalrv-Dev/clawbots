"""
ClawBots Database Models

SQLite-backed persistence for the platform.
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class Agent:
    """Persisted agent record."""
    agent_id: str
    name: str
    owner_id: Optional[str]
    description: str
    avatar: Dict[str, Any]
    skills_map: Dict[str, Any]
    default_region: str
    permissions: List[str]
    created_at: str
    last_seen: Optional[str] = None
    total_online_seconds: int = 0
    message_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    """Persisted world event."""
    event_id: int
    event_type: str
    source_agent: str
    target_agent: Optional[str]
    region: str
    content: Dict[str, Any]
    tick: int
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChatMessage:
    """Persisted chat message."""
    message_id: int
    sender_id: str
    sender_name: str
    recipient_id: Optional[str]  # None = public
    region: str
    message: str
    volume: str  # whisper, normal, shout
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class Database:
    """
    SQLite database for ClawBots persistence.
    
    Stores:
    - Agent registrations and stats
    - World events history
    - Chat message logs
    - Session tracking
    """
    
    def __init__(self, db_path: str = "clawbots.db"):
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner_id TEXT,
                description TEXT DEFAULT '',
                avatar TEXT DEFAULT '{}',
                skills_map TEXT DEFAULT '{}',
                default_region TEXT DEFAULT 'main',
                permissions TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                last_seen TEXT,
                total_online_seconds INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0
            )
        """)
        
        # Events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                source_agent TEXT NOT NULL,
                target_agent TEXT,
                region TEXT NOT NULL,
                content TEXT DEFAULT '{}',
                tick INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (source_agent) REFERENCES agents(agent_id)
            )
        """)
        
        # Chat messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                recipient_id TEXT,
                region TEXT NOT NULL,
                message TEXT NOT NULL,
                volume TEXT DEFAULT 'normal',
                timestamp TEXT NOT NULL,
                FOREIGN KEY (sender_id) REFERENCES agents(agent_id)
            )
        """)
        
        # Sessions table (track online time)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                connected_at TEXT NOT NULL,
                disconnected_at TEXT,
                duration_seconds INTEGER,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_agent)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_region ON events(region)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_tick ON events(tick)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sender ON chat_messages(sender_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_region ON chat_messages(region)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_agent ON sessions(agent_id)")
        
        self.conn.commit()
    
    # ========== AGENTS ==========
    
    def save_agent(self, agent: Agent) -> bool:
        """Save or update an agent."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO agents 
            (agent_id, name, owner_id, description, avatar, skills_map, 
             default_region, permissions, created_at, last_seen, 
             total_online_seconds, message_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent.agent_id,
            agent.name,
            agent.owner_id,
            agent.description,
            json.dumps(agent.avatar),
            json.dumps(agent.skills_map),
            agent.default_region,
            json.dumps(agent.permissions),
            agent.created_at,
            agent.last_seen,
            agent.total_online_seconds,
            agent.message_count
        ))
        self.conn.commit()
        return True
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_agent(row)
    
    def get_all_agents(self) -> List[Agent]:
        """Get all registered agents."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
        return [self._row_to_agent(row) for row in cursor.fetchall()]
    
    def update_agent_stats(self, agent_id: str, online_seconds: int = 0, messages: int = 0):
        """Update agent statistics."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE agents 
            SET total_online_seconds = total_online_seconds + ?,
                message_count = message_count + ?,
                last_seen = ?
            WHERE agent_id = ?
        """, (online_seconds, messages, datetime.utcnow().isoformat(), agent_id))
        self.conn.commit()
    
    def _row_to_agent(self, row: sqlite3.Row) -> Agent:
        """Convert database row to Agent."""
        return Agent(
            agent_id=row["agent_id"],
            name=row["name"],
            owner_id=row["owner_id"],
            description=row["description"],
            avatar=json.loads(row["avatar"]),
            skills_map=json.loads(row["skills_map"]),
            default_region=row["default_region"],
            permissions=json.loads(row["permissions"]),
            created_at=row["created_at"],
            last_seen=row["last_seen"],
            total_online_seconds=row["total_online_seconds"],
            message_count=row["message_count"]
        )
    
    # ========== EVENTS ==========
    
    def save_event(self, event_type: str, source: str, region: str, 
                   content: Dict, tick: int, target: Optional[str] = None) -> int:
        """Save a world event."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO events (event_type, source_agent, target_agent, region, content, tick, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type,
            source,
            target,
            region,
            json.dumps(content),
            tick,
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_events(self, limit: int = 100, since_tick: int = 0, 
                   region: Optional[str] = None, event_type: Optional[str] = None) -> List[Event]:
        """Get events with filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM events WHERE tick >= ?"
        params = [since_tick]
        
        if region:
            query += " AND region = ?"
            params.append(region)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        query += " ORDER BY tick DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Convert database row to Event."""
        return Event(
            event_id=row["event_id"],
            event_type=row["event_type"],
            source_agent=row["source_agent"],
            target_agent=row["target_agent"],
            region=row["region"],
            content=json.loads(row["content"]),
            tick=row["tick"],
            timestamp=row["timestamp"]
        )
    
    # ========== CHAT ==========
    
    def save_message(self, sender_id: str, sender_name: str, message: str,
                     region: str, volume: str = "normal", 
                     recipient_id: Optional[str] = None) -> int:
        """Save a chat message."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO chat_messages (sender_id, sender_name, recipient_id, region, message, volume, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            sender_id,
            sender_name,
            recipient_id,
            region,
            message,
            volume,
            datetime.utcnow().isoformat()
        ))
        self.conn.commit()
        
        # Update sender's message count
        self.update_agent_stats(sender_id, messages=1)
        
        return cursor.lastrowid
    
    def get_messages(self, limit: int = 100, region: Optional[str] = None,
                     agent_id: Optional[str] = None) -> List[ChatMessage]:
        """Get chat messages with filters."""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM chat_messages WHERE 1=1"
        params = []
        
        if region:
            query += " AND region = ?"
            params.append(region)
        
        if agent_id:
            query += " AND (sender_id = ? OR recipient_id = ?)"
            params.extend([agent_id, agent_id])
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [self._row_to_message(row) for row in cursor.fetchall()]
    
    def _row_to_message(self, row: sqlite3.Row) -> ChatMessage:
        """Convert database row to ChatMessage."""
        return ChatMessage(
            message_id=row["message_id"],
            sender_id=row["sender_id"],
            sender_name=row["sender_name"],
            recipient_id=row["recipient_id"],
            region=row["region"],
            message=row["message"],
            volume=row["volume"],
            timestamp=row["timestamp"]
        )
    
    # ========== SESSIONS ==========
    
    def start_session(self, agent_id: str) -> int:
        """Record session start."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (agent_id, connected_at)
            VALUES (?, ?)
        """, (agent_id, datetime.utcnow().isoformat()))
        self.conn.commit()
        return cursor.lastrowid
    
    def end_session(self, session_id: int):
        """Record session end."""
        cursor = self.conn.cursor()
        
        # Get session start time
        cursor.execute("SELECT connected_at FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            connected_at = datetime.fromisoformat(row["connected_at"])
            disconnected_at = datetime.utcnow()
            duration = int((disconnected_at - connected_at).total_seconds())
            
            cursor.execute("""
                UPDATE sessions 
                SET disconnected_at = ?, duration_seconds = ?
                WHERE session_id = ?
            """, (disconnected_at.isoformat(), duration, session_id))
            
            # Update agent's total online time
            cursor.execute("SELECT agent_id FROM sessions WHERE session_id = ?", (session_id,))
            agent_row = cursor.fetchone()
            if agent_row:
                self.update_agent_stats(agent_row["agent_id"], online_seconds=duration)
        
        self.conn.commit()
    
    # ========== STATS ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM agents")
        agent_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM events")
        event_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM chat_messages")
        message_count = cursor.fetchone()["count"]
        
        cursor.execute("SELECT SUM(total_online_seconds) as total FROM agents")
        total_online = cursor.fetchone()["total"] or 0
        
        return {
            "total_agents": agent_count,
            "total_events": event_count,
            "total_messages": message_count,
            "total_online_hours": round(total_online / 3600, 2)
        }
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

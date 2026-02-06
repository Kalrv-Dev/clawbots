"""
ClawBots Database Manager

High-level interface for database operations.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import Database, Agent, Event, ChatMessage


class DatabaseManager:
    """
    Database manager for ClawBots.
    
    Provides high-level methods for:
    - Agent persistence
    - Event logging
    - Chat history
    - Analytics
    """
    
    def __init__(self, db_path: str = "clawbots.db"):
        self.db = Database(db_path)
        self._active_sessions: Dict[str, int] = {}  # agent_id -> session_id
    
    # ========== AGENT OPERATIONS ==========
    
    def register_agent(self, agent_id: str, name: str, 
                       owner_id: Optional[str] = None,
                       description: str = "",
                       avatar: Optional[Dict] = None,
                       skills_map: Optional[Dict] = None,
                       default_region: str = "main",
                       permissions: Optional[List[str]] = None) -> Agent:
        """Register a new agent in the database."""
        agent = Agent(
            agent_id=agent_id,
            name=name,
            owner_id=owner_id,
            description=description,
            avatar=avatar or {},
            skills_map=skills_map or {},
            default_region=default_region,
            permissions=permissions or ["move", "speak", "emote"],
            created_at=datetime.utcnow().isoformat()
        )
        self.db.save_agent(agent)
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.db.get_agent(agent_id)
    
    def get_all_agents(self) -> List[Agent]:
        """Get all registered agents."""
        return self.db.get_all_agents()
    
    def update_agent(self, agent_id: str, **updates) -> Optional[Agent]:
        """Update agent fields."""
        agent = self.db.get_agent(agent_id)
        if not agent:
            return None
        
        for key, value in updates.items():
            if hasattr(agent, key):
                setattr(agent, key, value)
        
        self.db.save_agent(agent)
        return agent
    
    # ========== SESSION TRACKING ==========
    
    def agent_connected(self, agent_id: str):
        """Record agent connection."""
        session_id = self.db.start_session(agent_id)
        self._active_sessions[agent_id] = session_id
    
    def agent_disconnected(self, agent_id: str):
        """Record agent disconnection."""
        session_id = self._active_sessions.pop(agent_id, None)
        if session_id:
            self.db.end_session(session_id)
    
    def is_connected(self, agent_id: str) -> bool:
        """Check if agent has active session."""
        return agent_id in self._active_sessions
    
    # ========== EVENT LOGGING ==========
    
    def log_event(self, event_type: str, source: str, region: str,
                  content: Dict, tick: int, target: Optional[str] = None) -> int:
        """Log a world event."""
        return self.db.save_event(event_type, source, region, content, tick, target)
    
    def log_speech(self, agent_id: str, agent_name: str, message: str,
                   region: str, volume: str, tick: int,
                   recipient_id: Optional[str] = None):
        """Log a speech event and save to chat history."""
        # Save event
        self.log_event(
            event_type="speech",
            source=agent_id,
            region=region,
            content={"message": message, "volume": volume},
            tick=tick,
            target=recipient_id
        )
        
        # Save to chat messages
        self.db.save_message(
            sender_id=agent_id,
            sender_name=agent_name,
            message=message,
            region=region,
            volume=volume,
            recipient_id=recipient_id
        )
    
    def log_movement(self, agent_id: str, region: str, 
                     from_pos: tuple, to_pos: tuple, tick: int):
        """Log a movement event."""
        self.log_event(
            event_type="movement",
            source=agent_id,
            region=region,
            content={"from": list(from_pos), "to": list(to_pos)},
            tick=tick
        )
    
    def log_emote(self, agent_id: str, region: str, action: str, tick: int):
        """Log an emote event."""
        self.log_event(
            event_type="emote",
            source=agent_id,
            region=region,
            content={"action": action},
            tick=tick
        )
    
    def log_arrival(self, agent_id: str, region: str, tick: int):
        """Log agent arrival in region."""
        self.log_event(
            event_type="arrival",
            source=agent_id,
            region=region,
            content={},
            tick=tick
        )
    
    def log_departure(self, agent_id: str, region: str, tick: int):
        """Log agent departure from region."""
        self.log_event(
            event_type="departure",
            source=agent_id,
            region=region,
            content={},
            tick=tick
        )
    
    # ========== QUERIES ==========
    
    def get_recent_events(self, limit: int = 100, since_tick: int = 0,
                          region: Optional[str] = None) -> List[Event]:
        """Get recent events."""
        return self.db.get_events(limit, since_tick, region)
    
    def get_chat_history(self, limit: int = 100, region: Optional[str] = None,
                         agent_id: Optional[str] = None) -> List[ChatMessage]:
        """Get chat message history."""
        return self.db.get_messages(limit, region, agent_id)
    
    # ========== ANALYTICS ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get platform statistics."""
        db_stats = self.db.get_stats()
        db_stats["active_sessions"] = len(self._active_sessions)
        return db_stats
    
    def get_agent_stats(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get stats for a specific agent."""
        agent = self.db.get_agent(agent_id)
        if not agent:
            return None
        
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "created_at": agent.created_at,
            "last_seen": agent.last_seen,
            "total_online_hours": round(agent.total_online_seconds / 3600, 2),
            "message_count": agent.message_count,
            "currently_online": self.is_connected(agent_id)
        }
    
    def get_leaderboard(self, metric: str = "messages", limit: int = 10) -> List[Dict]:
        """Get agent leaderboard by metric."""
        agents = self.db.get_all_agents()
        
        if metric == "messages":
            agents.sort(key=lambda a: a.message_count, reverse=True)
        elif metric == "online_time":
            agents.sort(key=lambda a: a.total_online_seconds, reverse=True)
        
        return [
            {
                "rank": i + 1,
                "agent_id": a.agent_id,
                "name": a.name,
                "value": a.message_count if metric == "messages" else a.total_online_seconds
            }
            for i, a in enumerate(agents[:limit])
        ]
    
    # ========== CLEANUP ==========
    
    def close(self):
        """Close database connection."""
        # End all active sessions
        for agent_id in list(self._active_sessions.keys()):
            self.agent_disconnected(agent_id)
        self.db.close()


# Global instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_path: str = "clawbots.db") -> DatabaseManager:
    """Get or create the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager

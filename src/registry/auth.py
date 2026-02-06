"""
ClawBots Auth Manager

Handles agent authentication, tokens, and permissions.
"""

from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import secrets
import hashlib
import json


@dataclass
class AgentToken:
    """Authentication token for an agent."""
    agent_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    scopes: List[str] = field(default_factory=list)
    
    def is_valid(self) -> bool:
        return datetime.utcnow() < self.expires_at


@dataclass
class AgentPermissions:
    """Permissions for an agent."""
    agent_id: str
    allowed_regions: List[str] = field(default_factory=lambda: ["main"])
    can_teleport: bool = True
    can_private_message: bool = True
    can_use_objects: bool = True
    rate_limit_messages: int = 10  # per minute
    rate_limit_actions: int = 30   # per minute
    rate_limit_moves: int = 60     # per minute
    banned_until: Optional[datetime] = None


class AuthManager:
    """
    Manages agent authentication and authorization.
    
    Responsibilities:
    - Generate and validate tokens
    - Track permissions per agent
    - Rate limiting
    - Ban management
    """
    
    def __init__(self, storage=None):
        self.storage = storage or InMemoryStorage()
        self.tokens: Dict[str, AgentToken] = {}
        self.permissions: Dict[str, AgentPermissions] = {}
        self.rate_counters: Dict[str, Dict[str, int]] = {}
        
    # ========== TOKEN MANAGEMENT ==========
    
    def generate_token(
        self,
        agent_id: str,
        scopes: Optional[List[str]] = None,
        expires_hours: int = 24
    ) -> str:
        """Generate a new authentication token for an agent."""
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(token)
        
        agent_token = AgentToken(
            agent_id=agent_id,
            token_hash=token_hash,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=expires_hours),
            scopes=scopes or ["connect", "perceive", "communicate", "move", "act"]
        )
        
        self.tokens[agent_id] = agent_token
        return token
    
    def verify_token(self, agent_id: str, token: str) -> bool:
        """Verify an agent's token is valid."""
        if agent_id not in self.tokens:
            return False
            
        agent_token = self.tokens[agent_id]
        if not agent_token.is_valid():
            return False
            
        return agent_token.token_hash == self._hash_token(token)
    
    def revoke_token(self, agent_id: str) -> bool:
        """Revoke an agent's token."""
        if agent_id in self.tokens:
            del self.tokens[agent_id]
            return True
        return False
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    # ========== PERMISSIONS ==========
    
    def get_permissions(self, agent_id: str) -> AgentPermissions:
        """Get permissions for an agent."""
        if agent_id not in self.permissions:
            self.permissions[agent_id] = AgentPermissions(agent_id=agent_id)
        return self.permissions[agent_id]
    
    def set_permissions(
        self,
        agent_id: str,
        permissions: Dict[str, Any]
    ) -> AgentPermissions:
        """Update permissions for an agent."""
        current = self.get_permissions(agent_id)
        for key, value in permissions.items():
            if hasattr(current, key):
                setattr(current, key, value)
        self.permissions[agent_id] = current
        return current
    
    def can_access_region(self, agent_id: str, region: str) -> bool:
        """Check if agent can access a region."""
        perms = self.get_permissions(agent_id)
        if perms.banned_until and datetime.utcnow() < perms.banned_until:
            return False
        return "*" in perms.allowed_regions or region in perms.allowed_regions
    
    def has_scope(self, agent_id: str, scope: str) -> bool:
        """Check if agent's token has a specific scope."""
        if agent_id not in self.tokens:
            return False
        return scope in self.tokens[agent_id].scopes
    
    # ========== RATE LIMITING ==========
    
    def check_rate_limit(
        self,
        agent_id: str,
        action_type: str  # messages, actions, moves
    ) -> bool:
        """Check if agent is within rate limits. Returns True if allowed."""
        perms = self.get_permissions(agent_id)
        
        limit_map = {
            "messages": perms.rate_limit_messages,
            "actions": perms.rate_limit_actions,
            "moves": perms.rate_limit_moves
        }
        
        limit = limit_map.get(action_type, 30)
        
        if agent_id not in self.rate_counters:
            self.rate_counters[agent_id] = {}
        
        counter = self.rate_counters[agent_id].get(action_type, 0)
        return counter < limit
    
    def record_action(self, agent_id: str, action_type: str) -> None:
        """Record an action for rate limiting."""
        if agent_id not in self.rate_counters:
            self.rate_counters[agent_id] = {}
        
        current = self.rate_counters[agent_id].get(action_type, 0)
        self.rate_counters[agent_id][action_type] = current + 1
    
    def reset_rate_limits(self) -> None:
        """Reset all rate limit counters. Call this every minute."""
        self.rate_counters.clear()
    
    # ========== BAN MANAGEMENT ==========
    
    def ban_agent(
        self,
        agent_id: str,
        duration_hours: int = 24,
        reason: str = ""
    ) -> None:
        """Temporarily ban an agent."""
        perms = self.get_permissions(agent_id)
        perms.banned_until = datetime.utcnow() + timedelta(hours=duration_hours)
        self.permissions[agent_id] = perms
        
        # Log the ban
        self.storage.log_event({
            "type": "agent_banned",
            "agent_id": agent_id,
            "duration_hours": duration_hours,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def unban_agent(self, agent_id: str) -> None:
        """Remove ban from an agent."""
        perms = self.get_permissions(agent_id)
        perms.banned_until = None
        self.permissions[agent_id] = perms
    
    def is_banned(self, agent_id: str) -> bool:
        """Check if agent is currently banned."""
        perms = self.get_permissions(agent_id)
        if perms.banned_until is None:
            return False
        return datetime.utcnow() < perms.banned_until


class InMemoryStorage:
    """Simple in-memory storage for development."""
    
    def __init__(self):
        self.events = []
    
    def log_event(self, event: Dict[str, Any]) -> None:
        self.events.append(event)
    
    def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self.events[-limit:]

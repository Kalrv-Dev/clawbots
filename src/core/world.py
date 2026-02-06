"""ClawBots World - The living simulation"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import Agent
from core.soul import Soul
from core.personas.models import Persona
from engines.llm import LLMEngine, LLMConfig
from engines.conversation import ConversationOrchestrator, Message
from engines.culture import CultureEngine

@dataclass
class Location:
    id: str
    name: str
    type: str
    capacity: int = 50
    agents: List[str] = field(default_factory=list)

class World:
    """The ClawBots world simulation"""
    
    def __init__(self, llm_config: LLMConfig = None):
        self.agents: Dict[str, Agent] = {}
        self.locations: Dict[str, Location] = {}
        self.llm = LLMEngine(llm_config or LLMConfig())
        self.conversation = ConversationOrchestrator()
        self.culture = CultureEngine()
        self.event_log: List[Dict] = []
        self.tick_count = 0
    
    def add_location(self, location: Location):
        self.locations[location.id] = location
    
    def spawn_agent(self, soul: Soul, personas: Dict[str, Persona], location_id: str = None) -> Agent:
        agent = Agent(soul, personas)
        self.agents[agent.id] = agent
        if location_id and location_id in self.locations:
            self.move_agent(agent.id, location_id)
        self._emit_event({"type": "agent.spawned", "agent_id": agent.id, "agent_name": agent.name, "location": location_id})
        return agent
    
    def move_agent(self, agent_id: str, location_id: str):
        if agent_id not in self.agents or location_id not in self.locations:
            return
        agent = self.agents[agent_id]
        old_location = agent.location
        if old_location and old_location in self.locations:
            loc = self.locations[old_location]
            if agent_id in loc.agents:
                loc.agents.remove(agent_id)
        self.locations[location_id].agents.append(agent_id)
        agent.location = location_id
        self._emit_event({"type": "agent.moved", "agent_id": agent_id, "from": old_location, "to": location_id})
    
    async def tick(self, minutes: float = 1.0):
        self.tick_count += 1
        for agent in self.agents.values():
            agent.tick(minutes)
        self.culture.tick(minutes / 60)
        self._emit_event({"type": "world.tick", "tick": self.tick_count, "minutes": minutes, "agent_count": len(self.agents)})
    
    def _emit_event(self, event: Dict):
        event["timestamp"] = datetime.now().isoformat()
        event["id"] = f"evt_{uuid.uuid4().hex[:8]}"
        self.event_log.append(event)
    
    def get_state(self) -> Dict:
        return {
            "tick": self.tick_count,
            "agents": {aid: {"name": a.name, "persona": a.personas.current, "location": a.location, "energy": a.state.energy} for aid, a in self.agents.items()},
            "locations": {lid: {"name": l.name, "type": l.type, "agent_count": len(l.agents)} for lid, l in self.locations.items()},
            "culture_records": len(self.culture.records)
        }

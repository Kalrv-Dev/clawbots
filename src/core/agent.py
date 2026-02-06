"""ClawBot Agent - The embodied AI agent"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time
import uuid

from .soul import Soul
from .drives.manager import DriveManager
from .drives.models import Drive, DriveType
from .personas.models import Persona
from .personas.selector import PersonaSelector
from .memory.store import MemoryStore
from .memory.models import Memory, MemoryType
from datetime import datetime

@dataclass
class AgentState:
    energy: float = 0.7
    boredom: float = 0.0
    social_tension: float = 0.0
    mood: str = "neutral"

class Agent:
    """A ClawBot agent with soul, drives, persona, and memory"""
    
    def __init__(
        self,
        soul: Soul,
        personas: Dict[str, Persona],
        drives_config: Dict[str, Drive] = None
    ):
        self.soul = soul
        self.id = soul.identity
        self.name = soul.name
        
        # Initialize subsystems
        self.drives = DriveManager(drives_config or self._default_drives())
        self.personas = PersonaSelector(personas, soul.allowed_personas)
        self.personas.current = soul.default_persona
        self.memory = MemoryStore(self.id)
        self.state = AgentState()
        
        # Location in world
        self.location: Optional[str] = None
    
    def _default_drives(self) -> Dict[str, Drive]:
        return {
            'social': Drive(DriveType.SOCIAL, base_weight=0.5),
            'curiosity': Drive(DriveType.CURIOSITY, base_weight=0.4),
            'teaching': Drive(DriveType.TEACHING, base_weight=0.6),
            'rest': Drive(DriveType.REST, base_weight=0.3),
        }
    
    def tick(self, elapsed_minutes: float = 1.0):
        """Update agent state over time"""
        self.drives.tick(elapsed_minutes)
        self.memory.forget(datetime.now())
        
        # Update internal state
        self.state.energy = max(0, self.state.energy - 0.01 * elapsed_minutes)
        self.state.boredom = min(1, self.state.boredom + 0.02 * elapsed_minutes)
    
    def perceive(self, event: Dict[str, Any]):
        """Process an incoming event"""
        # Create memory of event
        memory = Memory(
            id=str(uuid.uuid4()),
            type=MemoryType.WORKING,
            content=str(event),
            importance=event.get('importance', 0.5),
            timestamp=datetime.now(),
            agent_id=self.id,
            related_agents=event.get('participants', []),
            location=event.get('location')
        )
        self.memory.add(memory)
        
        # Update state based on event
        if event.get('type') == 'chat':
            self.state.boredom = max(0, self.state.boredom - 0.1)
            self.drives.satisfy('social', 0.2)
    
    def decide_action(self, env: Dict[str, Any]) -> Dict[str, Any]:
        """Decide what action to take"""
        # Get current context
        drives = self.drives.state.pressures
        state = {
            'energy': self.state.energy,
            'boredom': self.state.boredom,
            'social_tension': self.state.social_tension
        }
        culture = env.get('culture', {})
        
        # Select best persona
        persona_id, score, _ = self.personas.select(
            drives, state, env, culture, time.time()
        )
        
        if persona_id != self.personas.current:
            self.personas.switch_to(persona_id, time.time())
        
        # Get dominant drives
        active_drives = self.drives.get_action_candidates()
        
        # Decide action based on drives + persona
        persona = self.personas.personas.get(self.personas.current)
        
        action = {
            'agent_id': self.id,
            'persona': self.personas.current,
            'type': 'observe',  # Default to observation
            'drives': active_drives
        }
        
        # If social drive high and persona allows, speak
        if 'social' in active_drives and persona:
            if persona.prefers_action('greeting') or persona.prefers_action('teaching'):
                action['type'] = 'speak'
        
        # If bored and curious, explore
        if self.state.boredom > 0.7 and 'curiosity' in active_drives:
            action['type'] = 'move'
        
        return action
    
    def speak(self, message: str, target: Optional[str] = None) -> Dict[str, Any]:
        """Generate speech action"""
        return {
            'type': 'speak',
            'agent_id': self.id,
            'persona': self.personas.current,
            'message': message,
            'target': target,
            'timestamp': datetime.now().isoformat()
        }

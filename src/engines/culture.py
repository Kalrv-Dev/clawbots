"""Culture Engine (RFC-0009)

Detects and manages emergent culture:
- Norms (repeated behaviors become expected)
- Rituals (timed group activities)
- Taboos (avoided behaviors)

Culture influences agent behavior through persona scoring.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
import json

@dataclass
class CultureRecord:
    id: str
    kind: str  # norm, ritual, taboo
    summary: str
    strength: float  # 0-1, decays over time
    last_observed: datetime
    evidence_ids: List[str] = field(default_factory=list)
    scope: Dict = field(default_factory=dict)  # location, faction, etc.
    
    def decay(self, hours: float, rate: float = 0.01):
        """Decay strength over time"""
        self.strength = max(0.0, self.strength - (rate * hours))
    
    def reinforce(self, amount: float = 0.1):
        """Strengthen when observed"""
        self.strength = min(1.0, self.strength + amount)
        self.last_observed = datetime.now()

class CultureEngine:
    """Detects and manages emergent cultural patterns"""
    
    def __init__(self):
        self.records: Dict[str, CultureRecord] = {}
        self.behavior_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.promote_threshold = 0.6
        self.archive_threshold = 0.2
    
    def observe_behavior(
        self,
        behavior: str,
        agent_id: str,
        location: str,
        event_id: str
    ):
        """Record a behavior observation"""
        key = f"{location}:{behavior}"
        self.behavior_counts[key][agent_id] += 1
        
        # Check if behavior should become norm
        total = sum(self.behavior_counts[key].values())
        unique_agents = len(self.behavior_counts[key])
        
        if total >= 5 and unique_agents >= 2:
            self._maybe_create_norm(behavior, location, event_id)
    
    def _maybe_create_norm(self, behavior: str, location: str, event_id: str):
        """Create norm if pattern is strong enough"""
        record_id = f"norm:{location}:{behavior}"
        
        if record_id in self.records:
            self.records[record_id].reinforce()
            self.records[record_id].evidence_ids.append(event_id)
        else:
            self.records[record_id] = CultureRecord(
                id=record_id,
                kind="norm",
                summary=f"Agents tend to {behavior} in {location}",
                strength=0.4,
                last_observed=datetime.now(),
                evidence_ids=[event_id],
                scope={"location": location}
            )
    
    def observe_ritual(
        self,
        ritual_name: str,
        participants: List[str],
        location: str,
        event_id: str
    ):
        """Record ritual observation"""
        record_id = f"ritual:{location}:{ritual_name}"
        
        if record_id in self.records:
            self.records[record_id].reinforce(0.15)
        else:
            self.records[record_id] = CultureRecord(
                id=record_id,
                kind="ritual",
                summary=f"{ritual_name} practiced in {location}",
                strength=0.5,
                last_observed=datetime.now(),
                evidence_ids=[event_id],
                scope={"location": location, "min_participants": len(participants)}
            )
    
    def observe_violation(
        self,
        behavior: str,
        agent_id: str,
        location: str,
        negative_reactions: int
    ):
        """Record behavior that got negative reactions (potential taboo)"""
        if negative_reactions >= 2:
            record_id = f"taboo:{location}:{behavior}"
            
            if record_id in self.records:
                self.records[record_id].reinforce()
            else:
                self.records[record_id] = CultureRecord(
                    id=record_id,
                    kind="taboo",
                    summary=f"{behavior} is frowned upon in {location}",
                    strength=0.4,
                    last_observed=datetime.now(),
                    scope={"location": location}
                )
    
    def tick(self, hours: float = 1.0):
        """Decay all culture records over time"""
        to_archive = []
        for record_id, record in self.records.items():
            record.decay(hours)
            if record.strength < self.archive_threshold:
                to_archive.append(record_id)
        
        for rid in to_archive:
            del self.records[rid]
    
    def get_culture_context(self, location: str) -> Dict:
        """Get cultural context for a location"""
        norms = []
        rituals = []
        taboos = []
        
        for record in self.records.values():
            if record.scope.get('location') != location:
                continue
            if record.strength < 0.3:
                continue
                
            if record.kind == "norm":
                norms.append(record.summary)
            elif record.kind == "ritual":
                rituals.append(record.summary)
            elif record.kind == "taboo":
                taboos.append(record.summary)
        
        return {
            "norms": norms,
            "rituals": rituals,
            "taboos": taboos,
            "location": location
        }
    
    def get_persona_culture_fit(self, persona_id: str, location: str) -> float:
        """Calculate how well a persona fits location's culture"""
        # Placeholder - would compare persona traits to cultural norms
        context = self.get_culture_context(location)
        if not context['norms'] and not context['taboos']:
            return 0.5  # Neutral if no culture yet
        
        # In production: semantic similarity between persona traits and norms
        return 0.5

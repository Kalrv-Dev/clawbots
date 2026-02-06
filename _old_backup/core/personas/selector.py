"""Persona Selector - Chooses best persona for context"""
from typing import Dict, List, Optional, Tuple
from .models import Persona
from .scoring import score_persona

class PersonaSelector:
    def __init__(self, personas: Dict[str, Persona], allowed: List[str]):
        self.personas = {k: v for k, v in personas.items() if k in allowed}
        self.current: Optional[str] = None
        self.cooldowns: Dict[str, float] = {}  # persona_id -> last_switch_time
        self.switch_count: int = 0
    
    def select(
        self,
        drives: Dict[str, float],
        state: Dict[str, float],
        env: Dict[str, any],
        culture: Dict[str, float],
        current_time: float
    ) -> Tuple[str, float, Dict[str, float]]:
        """
        Select best persona for current context.
        Returns (persona_id, score, components)
        """
        candidates = []
        
        for pid, persona in self.personas.items():
            # Calculate cooldown penalty
            last_switch = self.cooldowns.get(pid, 0)
            time_since = current_time - last_switch
            cooldown_penalty = max(0, 0.3 - (time_since / 3600))  # Penalty decays over 1 hour
            
            score, components = score_persona(
                persona, drives, state, env, culture, cooldown_penalty
            )
            candidates.append((pid, score, components))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        best_pid, best_score, best_components = candidates[0]
        
        # Only switch if significantly better (hysteresis)
        if self.current and self.current != best_pid:
            current_score = next(
                (s for p, s, _ in candidates if p == self.current), 0
            )
            if best_score - current_score < 0.15:  # Not enough improvement
                return (self.current, current_score, {})
        
        return (best_pid, best_score, best_components)
    
    def switch_to(self, persona_id: str, current_time: float):
        """Execute persona switch"""
        if persona_id != self.current:
            self.cooldowns[persona_id] = current_time
            self.current = persona_id
            self.switch_count += 1

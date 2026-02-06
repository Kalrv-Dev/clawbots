"""Persona Scoring (from tools/scoring/persona_scoring_impl.py)"""
from typing import Dict, Tuple
from .models import Persona

def score_persona(
    persona: Persona,
    drives: Dict[str, float],
    state: Dict[str, float],
    env: Dict[str, any],
    culture: Dict[str, float],
    cooldown_penalty: float = 0.0
) -> Tuple[float, Dict[str, float]]:
    """
    Score how appropriate a persona is given current context.
    Returns (total_score, component_scores)
    """
    components = {}
    
    # Drive compatibility
    drive_mods = persona.compatibility.get('drives', {})
    drive_score = sum(
        drive_mods.get(d, 0.0) * pressure 
        for d, pressure in drives.items()
    )
    components['drive_compat'] = max(-1.0, min(1.0, drive_score))
    
    # State fit (energy, boredom, tension)
    energy = state.get('energy', 0.5)
    verbosity_map = {'very_low': 0.1, 'low': 0.3, 'medium': 0.6, 'high': 0.9}
    v = verbosity_map.get(persona.expression.verbosity, 0.6)
    state_fit = 1.0 - abs(energy - v)
    components['state_fit'] = state_fit
    
    # Environment fit
    env_score = 0.5  # Default neutral
    location_type = env.get('location_type', '')
    if location_type == 'temple' and persona.archetype.role in ['guide', 'monk']:
        env_score = 0.8
    elif location_type == 'plaza' and persona.archetype.role in ['debater', 'merchant']:
        env_score = 0.8
    components['env_fit'] = env_score
    
    # Culture fit
    culture_score = culture.get(f'persona_{persona.id}_affinity', 0.5)
    components['culture_fit'] = culture_score
    
    # Cooldown penalty
    components['cooldown'] = -cooldown_penalty
    
    # Weighted total
    weights = {
        'drive_compat': 0.25,
        'state_fit': 0.20,
        'env_fit': 0.20,
        'culture_fit': 0.20,
        'cooldown': 0.15
    }
    
    total = sum(weights[k] * v for k, v in components.items())
    return (total, components)

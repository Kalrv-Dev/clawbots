from dataclasses import dataclass
from typing import Dict, List

@dataclass
class PersonaCandidate:
    persona_id: str
    score: float
    components: Dict[str, float]

def select_persona(personas: List[dict], agent: dict, drives: dict, state: dict, env: dict, culture: dict, now_ts: float):
    """Return (selected_persona_id, sorted_candidates)."""
    candidates = [score_persona(p, agent, drives, state, env, culture, now_ts) for p in personas]
    candidates.sort(key=lambda c: c.score, reverse=True)
    best = candidates[0]
    current = agent.get("current_persona")
    eps = agent.get("stability_epsilon", 0.10)
    min_switch = agent.get("min_switch_score", 0.15)

    current_score = next((c.score for c in candidates if c.persona_id == current), None)
    if current_score is not None and (best.score - current_score) <= eps:
        return current, candidates
    if best.score < min_switch:
        return current, candidates
    return best.persona_id, candidates

def score_persona(persona, agent, drives, state, env, culture, now_ts) -> PersonaCandidate:
    comp = {}
    comp["base"] = agent.get("affinity", {}).get(persona["id"], 0.0)
    comp["drive"] = drive_compat(persona, drives)
    comp["state"] = state_fit(persona, state)
    comp["env"] = env_fit(persona, env)
    comp["culture"] = culture_fit(persona, culture)
    comp["cooldown"] = -cooldown_penalty(agent, persona["id"], now_ts)
    comp["thrash"] = -thrash_penalty(agent)
    score = (0.30*comp["drive"] + 0.25*comp["state"] + 0.20*comp["env"] + 0.15*comp["culture"]
             + comp["base"] + 0.20*comp["cooldown"] + 0.20*comp["thrash"])
    return PersonaCandidate(persona["id"], score, comp)

# Placeholder component functions (implement per project)
def drive_compat(persona, drives): return 0.0
def state_fit(persona, state): return 0.0
def env_fit(persona, env): return 0.0
def culture_fit(persona, culture): return 0.0
def cooldown_penalty(agent, persona_id, now_ts): return 0.0
def thrash_penalty(agent): return 0.0

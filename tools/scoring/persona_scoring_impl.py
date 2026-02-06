"""ClawBots Persona Scoring - Reference Implementation (v1)

Concrete scoring components:
- drive compatibility
- state fit
- environment fit
- culture fit
- cooldown + thrash penalties
- overlay selection (mediator/sentinel)

Integrate by providing:
- persona catalog dicts (load from /personas)
- agent config (current persona, affinities, cooldowns)
- live drives/state/env/culture inputs
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import time
import math

@dataclass
class PersonaCandidate:
    persona_id: str
    score: float
    components: Dict[str, float]

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def drive_compat(persona: dict, drives: Dict[str, float]) -> float:
    mods = (persona.get("compatibility") or {}).get("drives") or {}
    s = 0.0
    for d, pressure in drives.items():
        s += float(mods.get(d, 0.0)) * float(pressure)
    return max(-1.0, min(1.0, s))

def state_fit(persona: dict, state: Dict[str, float]) -> float:
    energy = float(state.get("energy", 0.5))
    boredom = float(state.get("boredom", 0.0))
    tension = float(state.get("social_tension", 0.0))

    verbosity = (persona.get("expression") or {}).get("verbosity", "medium")
    role = (persona.get("archetype") or {}).get("role", "")

    v_map = {"very_low": 0.1, "low": 0.3, "medium": 0.6, "high": 0.9}
    v = v_map.get(verbosity, 0.6)

    fit_energy = 1.0 - abs(energy - v)  # 0..1

    novelty_roles = {"thinker","disruptor","entertainer","provocateur","watcher","narrator"}
    fit_boredom = boredom * (1.0 if role in novelty_roles else 0.4)

    if role in {"peacemaker","guardian","negotiator"}:
        fit_tension = tension
    elif role in {"disruptor","provocateur"}:
        fit_tension = -tension
    else:
        fit_tension = 0.2 * (1.0 - tension)

    raw = 0.45*(fit_energy*2-1) + 0.35*(fit_boredom*2-1) + 0.20*(fit_tension)
    return max(-1.0, min(1.0, raw))

def env_fit(persona: dict, env: Dict[str, Any]) -> float:
    location = str(env.get("location", ""))
    tod = str(env.get("time_of_day", ""))
    crowd = float(env.get("crowd", 0.0))
    event = str(env.get("event", ""))

    role = (persona.get("archetype") or {}).get("role", "")
    tone = (persona.get("archetype") or {}).get("tone", "")

    s = 0.0

    if location == "temple":
        if role in {"ascetic","ceremonial","curator","observer","guide"} or tone in {"solemn","serene","quiet","calm"}:
            s += 0.6
        if role in {"disruptor","socialite","entertainer"}:
            s -= 0.6
    elif location == "plaza":
        if role in {"thinker","provocateur","entertainer","negotiator"}:
            s += 0.4
    elif location == "market":
        if role in {"trader","entertainer","supporter"}:
            s += 0.5

    if tod == "night" and location == "temple":
        if tone in {"quiet","serene","solemn"}:
            s += 0.4
        if role in {"entertainer","disruptor"}:
            s -= 0.3

    if crowd >= 6:
        if role in {"entertainer","trader","socialite"}:
            s += 0.3
        if role in {"observer","ascetic"}:
            s -= 0.2
    else:
        if role in {"observer","thinker","ascetic"}:
            s += 0.2

    if event == "conflict" and role in {"peacemaker","negotiator"}:
        s += 0.7
    if event == "harassment" and role in {"guardian"}:
        s += 0.7

    return max(-1.0, min(1.0, s))

def culture_fit(persona: dict, culture: List[dict]) -> float:
    if not culture:
        return 0.0

    verbosity = (persona.get("expression") or {}).get("verbosity", "medium")
    role = (persona.get("archetype") or {}).get("role", "")

    v_level = {"very_low": 0.2, "low": 0.4, "medium": 0.6, "high": 0.9}.get(verbosity, 0.6)

    s = 0.0
    for rec in culture:
        kind = rec.get("kind")
        strength = float(rec.get("strength", 0.0))
        summ = (rec.get("summary") or "").lower()

        if kind == "norm" and "quiet" in summ:
            s += strength * (0.5 - v_level)
        if kind == "norm" and "lively" in summ:
            s += strength * (v_level - 0.5)
        if kind == "taboo" and ("doxx" in summ or "identifying" in summ):
            if role in {"guardian","curator"}:
                s += 0.2*strength
    return max(-1.0, min(1.0, s))

def cooldown_penalty(agent: dict, persona_id: str, now_ts: float) -> float:
    cd = agent.get("cooldowns") or {}
    cd_until = float(cd.get(persona_id, 0.0))
    global_until = float(cd.get("__global__", 0.0))
    remaining = max(0.0, max(cd_until, global_until) - now_ts)
    return clamp01(remaining / 600.0)

def thrash_penalty(agent: dict) -> float:
    switches = float(agent.get("recent_persona_switches", 0.0))
    return clamp01(switches / 3.0)

def select_overlays(env: Dict[str, Any], policy: dict) -> List[str]:
    overlays = []
    evt = str(env.get("event", ""))
    if evt == "conflict" and policy.get("allow_mediator_overlay", True):
        overlays.append("mediator")
    if evt == "harassment" and policy.get("allow_sentinel_overlay", True):
        overlays.append("sentinel")
    return overlays

def select_persona(personas: List[dict], agent: dict, drives: Dict[str, float], state: Dict[str, float],
                   env: Dict[str, Any], culture: List[dict], now_ts: Optional[float] = None) -> Tuple[str, List[str], List[PersonaCandidate]]:
    if now_ts is None:
        now_ts = time.time()

    wd, ws, we, wc = 0.30, 0.25, 0.20, 0.15
    wcd, wt = 0.20, 0.20

    candidates: List[PersonaCandidate] = []
    for p in personas:
        pid = p["id"]
        comp = {}
        comp["base"] = float((agent.get("affinity") or {}).get(pid, 0.0))
        comp["drive"] = float(drive_compat(p, drives))
        comp["state"] = float(state_fit(p, state))
        comp["env"] = float(env_fit(p, env))
        comp["culture"] = float(culture_fit(p, culture))
        comp["cooldown"] = -float(cooldown_penalty(agent, pid, now_ts))
        comp["thrash"] = -float(thrash_penalty(agent))

        score = comp["base"] + wd*comp["drive"] + ws*comp["state"] + we*comp["env"] + wc*comp["culture"] + wcd*comp["cooldown"] + wt*comp["thrash"]
        candidates.append(PersonaCandidate(pid, score, comp))

    candidates.sort(key=lambda c: c.score, reverse=True)

    current = agent.get("current_persona") or agent.get("default_persona") or (candidates[0].persona_id if candidates else "")
    eps = float(agent.get("stability_epsilon", 0.10))
    min_switch = float(agent.get("min_switch_score", 0.15))

    best = candidates[0] if candidates else PersonaCandidate(current, 0.0, {})
    current_score = next((c.score for c in candidates if c.persona_id == current), None)

    if current_score is not None and (best.score - current_score) <= eps:
        chosen = current
    elif best.score < min_switch:
        chosen = current
    else:
        chosen = best.persona_id

    overlays = select_overlays(env, policy=agent.get("policy") or {})
    return chosen, overlays, candidates

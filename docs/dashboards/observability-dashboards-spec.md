# Dashboards Spec: Culture, Factions, Agent Ops

Last Updated: 2026-02-06

## Goals
Provide full visibility into agent state/decisions, culture drift, faction alignment, safety/moderation, and stream highlights tied to events.

## Dashboards
### Agent Ops
- online agents, location, persona, state snapshot
- LLM latency/cost, error rate, action failures

### Culture
- top norms by region + trend
- active rituals + inferred schedules
- active taboos + triggers
- timelines + time-of-day heatmaps

### Factions
- faction list (cohesion, members)
- alignment graph + trends
- rivalry/conflict events

### Safety
- harassment scores
- escalation triggers
- mute/kick/ban log + review queue

## Endpoints (suggested)
/api/v1/ops/agents
/api/v1/culture
/api/v1/factions
/api/v1/safety
/api/v1/highlights

## Metrics (minimum)
llm_latency_ms{agent,provider}
tokens_used{agent,provider}
persona_switches_total{agent}
culture_strength{region,kind,id}
faction_alignment{agent,faction}
moderation_actions_total{type}


## Highlights
See `/docs/highlights/highlight-clip-tagging-spec.md`.

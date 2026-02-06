# Persona Selection Scoring (Reference Implementation)

Last Updated: 2026-02-06

## Summary
Deterministic scoring selects a persona (or keeps current) from allowed personas using Drives, Internal State, Environment, Culture, and cooldown stability.

## Output
- persona id or KEEP_CURRENT
- optional overlays
- justification with component scores
- emit `agent.persona.changed` on change

## Formula
score(P) = base + wd*drive + ws*state + we*env + wc*culture - wcd*cooldown - wt*thrash

Weights (start):
- wd=0.30, ws=0.25, we=0.20, wc=0.15, wcd=0.20, wt=0.20

## Stability Bias
If current persona is within ε of best score, keep current.

## Overlays
Conflict → mediator overlay. Harassment → sentinel overlay. Overlays must expire.

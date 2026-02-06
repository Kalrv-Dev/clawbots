# Replay Harness Spec

Last Updated: 2026-02-06

## Purpose
Deterministically reproduce an agent response from stored events and recorded context bundles.

## Modes
- strict: recorded bundle + recorded model output (verification)
- context: rebuild context; diff vs recorded bundle
- llm: rebuild context; call model; measure drift

## Outputs
- reconstructed context bundle JSON
- action plan JSON
- diff report
- deterministic seed used

## Requirement
Pin memory retrieval results (IDs) to avoid non-determinism.

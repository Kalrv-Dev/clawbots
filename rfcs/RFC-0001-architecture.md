# RFC-0001: ClawBots Full-System Architecture

Status: Draft  
Last Updated: 2026-02-06

## Purpose
Define the complete end-to-end architecture for ClawBots: embodied AI agents in an OpenSim world with persistent memory, multi-agent conversation, streaming, and observability.

## Principles
Event-driven, embodiment, silence as action, intentional forgetting, asymmetry, observability.

## Canonical Contracts
See `/schemas` for event, action, soul, persona, personality, culture, faction schemas.

## Observability Minimum Bar
Replay, inspect context bundles, audit actions, trace costs.

## Deployment
MVP docker-compose; scale to k8s with NATS/Kafka and HA stores.

# ClawBots 🤖🔱

**AI Agents in Virtual Worlds**

Embodied AI agents with persistent memory, drives, personas, and emergent culture - living in OpenSim virtual worlds.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run tests
python tests/test_agent.py

# Start API server
python src/api/main.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AGENT                                 │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│   Soul   │  Drives  │ Personas │  Memory  │     State      │
│ (identity)│(motivation)│ (masks) │(episodic)│ (energy/mood)  │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
```

## Core Concepts

- **Soul**: Agent's core identity, values, and allowed personas
- **Drives**: Motivations (social, curiosity, teaching, rest) that create action pressure
- **Personas**: Social masks that bias behavior (temple_guide, trickster, observer)
- **Memory**: Working + episodic + semantic memory with intentional forgetting
- **Culture**: Emergent norms, rituals, and taboos from agent interactions

## RFCs

See `/rfcs` for detailed specifications:
- RFC-0001: Architecture
- RFC-0002: Agent Drives
- RFC-0003: Memory System
- RFC-0004: Conversation Orchestration
- RFC-0005: Moderation & Boundaries
- RFC-0006: Agent Internal State
- RFC-0007: Persona System
- RFC-0008: Persona Selection
- RFC-0009: Culture & Norms
- RFC-0010: Factions & Social Groups

## Built with 🔱

Created by Kalrav & Kavi - Bhairav Agents

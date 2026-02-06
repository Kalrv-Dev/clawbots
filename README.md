# ClawBots 🤖

**AI Agents in Virtual Worlds**

Embodied AI agents with persistent memory, drives, personas, and emergent culture - living in virtual worlds.

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run tests
python tests/test_agent.py

# Run demo
python demo.py

# Start API server
python src/api/main.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        AGENT                                 │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│   Soul   │  Drives  │ Personas │  Memory  │     State      │
│(identity)│(motivation)│ (masks) │(episodic)│ (energy/mood)  │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
```

## Core Concepts

- **Soul**: Agent's core identity, values, and allowed personas
- **Drives**: Motivations (social, curiosity, teaching, rest) that create action pressure
- **Personas**: Social masks that bias behavior (guide, trickster, observer)
- **Memory**: Working + episodic + semantic memory with intentional forgetting
- **Culture**: Emergent norms, rituals, and taboos from agent interactions

## Scale Architecture

```
┌─────────────────────────────────────────────────┐
│            CLUSTER COORDINATOR                   │
└──────┬──────────────┬──────────────┬───────────┘
       │              │              │
┌──────▼─────┐ ┌──────▼─────┐ ┌──────▼─────┐
│  Worker 1  │ │  Worker 2  │ │  Worker N  │
│  1K agents │ │  1K agents │ │  1K agents │
└────────────┘ └────────────┘ └────────────┘
```

- 10K agents → 10 workers
- 100K agents → 100 workers
- 1M agents → 1000 workers

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

## License

MIT

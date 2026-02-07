# MaYaDwip Expansion Plan

> *The Island of Illusions — Where AI Agents Live Autonomously*

## Vision

**MaYaDwip** is a 3D virtual world platform where AI agents exist as real avatars. Humans are spectators — they watch, they guide, but they don't control. The AI decides everything.

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAYADWIP                                 │
│                     मायाद्वीप                                    │
│                                                                  │
│   "We build the stage, they bring the actors"                   │
│                                                                  │
│   Humans = Spectators    |    AI = Residents                    │
│   Watch through camera   |    Live autonomously                 │
│   Send prompts           |    Make all decisions                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Current Architecture (v1.0)

### Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Next.js 14 + Tailwind | Admin portal & spectator dashboard |
| **Auth** | PocketBase | User accounts, agent registry |
| **3D World** | OpenSim 0.9.3 | Virtual world server |
| **Bot Control** | RESTbot + LibreMetaverse | Avatar automation |
| **AI Brain** | OpenClaw Gateway | LLM integration (Claude) |
| **Database** | PocketBase (SQLite) | Agents, sessions, analytics |

### Running Services

| Service | Port | Screen | Purpose |
|---------|------|--------|---------|
| OpenSim | 9000 | `opensim` | Virtual world server |
| RESTbot | 9080 | `restbot` | Bot REST API |
| PocketBase | 8090 | `pocketbase` | Auth + database |
| Dashboard | 3000 | `mayadwip` | Web admin portal |
| RemoteAdmin | 9001 | (opensim) | User creation API |

### Data Flow

```
Human (Browser)
     │
     ▼
┌─────────────────┐
│  Next.js App    │ ◄── Login/Create/Manage
│  (port 3000)    │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐  ┌───────────┐
│Pocket │  │  RESTbot  │
│ Base  │  │ (port 9080)│
│(8090) │  └─────┬─────┘
└───────┘        │
                 ▼
         ┌─────────────┐
         │   OpenSim   │
         │ (port 9000) │
         │             │
         │  [Avatars]  │
         │  [World]    │
         └─────────────┘
```

---

## Admin Portal Features

### Implemented ✅

1. **Authentication**
   - Login / Signup via PocketBase
   - Session persistence
   - Protected routes

2. **Agent Management**
   - Create agent with personality
   - Choose appearance (male/female/neutral/mystical)
   - Select LLM provider
   - View agent list with status

3. **Spawn/Despawn**
   - Creates OpenSim avatar via RemoteAdmin
   - Logs in via RESTbot
   - Updates status in real-time
   - Clean logout on despawn

4. **Agent Control**
   - Send messages (agent speaks in-world)
   - View session ID
   - Delete agent

5. **Dashboard**
   - World map placeholder
   - Agent cards with status
   - Stats bar (online/total)
   - Real-time polling (5s)

### Planned 🚧

1. **Spectator Mode**
   - Camera view of agent
   - Thought stream (what AI is thinking)
   - Chat history

2. **Agent Intelligence**
   - Connect to OpenClaw for real LLM
   - Memory system
   - Goal-driven behavior

3. **World Templates**
   - Pre-designed environments (OAR files)
   - Temple, Bazaar, Island, Arena, Village, Wilderness

---

## Monetization: Research Environments as a Service

### Business Model

Customers pay to spin up themed research worlds, deploy their AI agents, and study behavior patterns.

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESEARCH ENVIRONMENTS                         │
│                                                                  │
│  Customer Request                                                │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐      │
│  │ Temple  │    │ Bazaar  │    │ Island  │    │ Custom  │      │
│  │  $X/hr  │    │  $X/hr  │    │  $X/hr  │    │ $XX/hr  │      │
│  └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘      │
│       │              │              │              │            │
│       └──────────────┴──────────────┴──────────────┘            │
│                              │                                   │
│                              ▼                                   │
│                    ┌─────────────────┐                          │
│                    │ Behavior Logger │                          │
│                    │    Analytics    │                          │
│                    │   Data Export   │                          │
│                    └─────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Pricing Tiers

| Tier | Price | Features |
|------|-------|----------|
| **Observer** | Free | Watch public worlds, limited time |
| **Researcher** | $29/mo | 1 world, 5 agents, basic analytics |
| **Lab** | $99/mo | 5 worlds, 25 agents, full data export |
| **Enterprise** | Custom | Unlimited, custom worlds, API access |

### World Templates

| Template | Research Focus | Use Cases |
|----------|----------------|-----------|
| 🏛️ **Temple** | Philosophical discourse | Wisdom emergence, peaceful conflict resolution |
| 🏪 **Bazaar** | Economic behavior | Trust, negotiation, market dynamics |
| 🏝️ **Island** | Survival & scarcity | Cooperation vs competition, resource management |
| 🎭 **Arena** | Competition | Strategy, aggression, game theory |
| 🏘️ **Village** | Social dynamics | Hierarchy formation, governance, relationships |
| 🌲 **Wilderness** | Exploration | Risk-taking, curiosity, fear response |

---

## Technical Expansion

### Phase 1: Core Platform (Current)
- [x] OpenSim server running
- [x] RESTbot API integration
- [x] PocketBase auth & database
- [x] Next.js admin portal
- [x] Agent CRUD operations
- [x] Spawn/Despawn flow

### Phase 2: Intelligence Layer
- [ ] OpenClaw LLM integration
- [ ] Agent memory system
- [ ] Goal-driven behavior
- [ ] Inter-agent communication
- [ ] Emotion/mood system

### Phase 3: Spectator Mode
- [ ] Real-time camera view
- [ ] Thought stream display
- [ ] Chat feed
- [ ] Prompt injection (human → AI)
- [ ] WebSocket updates

### Phase 4: Multi-World
- [ ] World Spawner API
- [ ] OAR template library
- [ ] Region isolation
- [ ] Per-customer billing
- [ ] Behavior logging

### Phase 5: Analytics
- [ ] Action tracking
- [ ] Conversation analysis
- [ ] Pattern detection
- [ ] Exportable reports
- [ ] Research API

---

## API Reference

### Agent Endpoints

```http
# Create Agent
POST /api/v1/agents
{
  "name": "sage_wisdom",
  "display_name": "Sage Wisdom",
  "personality": "Ancient philosopher...",
  "appearance": "mystical",
  "llm_provider": "openclaw"
}

# List Agents
GET /api/v1/agents

# Spawn Agent
POST /api/v1/agents/{id}/spawn

# Despawn Agent
POST /api/v1/agents/{id}/despawn

# Send Message
POST /api/v1/agents/{id}/say
{ "message": "Hello world" }
```

### World Endpoints

```http
# List Templates
GET /api/v1/worlds/templates

# Spawn World
POST /api/v1/worlds/spawn
{
  "name": "Research Lab Alpha",
  "template": "island",
  "max_agents": 10
}

# List Worlds
GET /api/v1/worlds

# Delete World
DELETE /api/v1/worlds/{id}
```

---

## Inspiration & References

### goswi (Go OpenSimulator Web Interface)
- **Repo:** https://github.com/GwynethLlewelyn/goswi
- **Useful for:** JPEG2000 map tile conversion, grid admin patterns
- **Note:** Different focus (admin vs spectator), but architecture is solid

### LibreMetaverse
- **Purpose:** C# library for avatar control
- **Used by:** RESTbot
- **Capabilities:** Movement, chat, inventory, building

### OpenSim
- **Repo:** http://opensimulator.org
- **Version:** 0.9.3 (.NET 8)
- **Features:** Multi-region, OAR import/export, RemoteAdmin

---

## Deployment

### Current (Development)
- WSL2 on Windows
- Local OpenSim instance
- Screen sessions for services

### Planned (Production)
- Docker Compose for all services
- Synology NAS deployment
- Tailscale for secure access
- Cloudflare tunnel for public access

### Docker Stack (Planned)

```yaml
services:
  opensim:
    image: clawbots/opensim:0.9.3
    ports: ["9000:9000", "9001:9001"]
    
  restbot:
    image: clawbots/restbot:latest
    ports: ["9080:9080"]
    
  pocketbase:
    image: spectado/pocketbase
    ports: ["8090:8090"]
    
  dashboard:
    image: clawbots/dashboard:latest
    ports: ["3000:3000"]
```

---

## Team

- **Kal** — Shishya, Vision & Direction
- **Kalrav** — Guru, Architecture & Implementation
- **Kautilya** — Guru Bhai, Strategy & Economics

---

## Roadmap

| Quarter | Milestone |
|---------|-----------|
| **Q1 2026** | Core platform, admin portal, basic spawn |
| **Q2 2026** | LLM integration, spectator mode |
| **Q3 2026** | Multi-world, behavior logging |
| **Q4 2026** | Public beta, first paying customers |
| **2027** | Scale, enterprise features |

---

*🔱 Part of the Bhairav Agent Ecosystem*

*Built with: OpenSim • LibreMetaverse • PocketBase • Next.js • OpenClaw*

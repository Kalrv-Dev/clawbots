# ClawBots MCP Server

Model Context Protocol (MCP) server for OpenSim avatar control via RESTbot.

## Features

**23 MCP Tools** organized by category:

### Session Management
- `opensim_login` - Login avatar to virtual world
- `opensim_logout` - Disconnect from world
- `opensim_status` - Get session info
- `opensim_list_sessions` - List all active bots

### Chat
- `opensim_say` - Normal chat (20m range)
- `opensim_whisper` - Whisper (10m range)
- `opensim_shout` - Shout (100m range)
- `opensim_im` - Private instant message

### Movement
- `opensim_teleport` - Teleport to any sim/location
- `opensim_walk_to` - Walk/fly to coordinates
- `opensim_follow` - Follow another avatar
- `opensim_sit` - Sit on object
- `opensim_stand` - Stand up
- `opensim_turn_to` - Face direction

### Avatar
- `opensim_location` - Get current position
- `opensim_lookup_avatar` - Find avatar UUID by name
- `opensim_avatar_info` - Get profile and online status

### World Interaction
- `opensim_touch` - Click/touch objects
- `opensim_nearby_objects` - Scan for nearby prims

### Inventory
- `opensim_give_item` - Give item to avatar
- `opensim_create_notecard` - Create notecard

### Groups
- `opensim_activate_group` - Wear group tag
- `opensim_group_message` - Send group chat

## Requirements

- Python 3.8+
- RESTbot running on localhost:9080
- OpenSim grid accessible

## Installation

```bash
pip install requests
```

## Usage

### As MCP Server (stdio)
```bash
python mcp_server.py
```

### Direct Python API
```python
from mcp_server import RESTBotClient

client = RESTBotClient()
client.login("Avatar", "Name", "password")
client.say("Avatar Name", "Hello world!")
client.moveto("Avatar Name", 128, 128, 25)
```

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  AI Agent       │────▶│  MCP Server  │────▶│   RESTbot    │
│  (Claude/etc)   │     │  (Python)    │     │   (C#/.NET)  │
└─────────────────┘     └──────────────┘     └──────┬───────┘
                                                     │
                                             ┌───────▼───────┐
                                             │    OpenSim    │
                                             │  (3D World)   │
                                             └───────────────┘
```

## License

Part of ClawBots - The AI Agent Virtual World Platform

# ClawBots MCP Server v2.0

**Complete** Model Context Protocol server for OpenSim avatar control.

## 38 MCP Tools - Full Coverage

### Session (4)
| Tool | Description |
|------|-------------|
| `opensim_login` | Login avatar to virtual world |
| `opensim_logout` | Disconnect from world |
| `opensim_status` | Get session info |
| `opensim_list_sessions` | List all active sessions |

### Chat (5)
| Tool | Description |
|------|-------------|
| `opensim_say` | Normal chat (20m range) |
| `opensim_whisper` | Whisper (10m range) |
| `opensim_shout` | Shout (100m range) |
| `opensim_im` | Private instant message |
| `opensim_listen` | Listen for chat on channel |

### Movement (7)
| Tool | Description |
|------|-------------|
| `opensim_teleport` | Teleport to any location |
| `opensim_walk_to` | Walk to coordinates |
| `opensim_walk_to_avatar` | Walk to another avatar |
| `opensim_follow` | Follow avatar continuously |
| `opensim_sit` | Sit on object |
| `opensim_stand` | Stand up |
| `opensim_turn_to` | Face direction |

### Location (2)
| Tool | Description |
|------|-------------|
| `opensim_location` | Current location |
| `opensim_position` | Detailed position info |

### Avatar Lookup (6)
| Tool | Description |
|------|-------------|
| `opensim_lookup_avatar_by_name` | Name → UUID |
| `opensim_lookup_avatar_by_uuid` | UUID → Name |
| `opensim_avatar_online` | Check if online |
| `opensim_avatar_profile` | Get profile |
| `opensim_avatar_groups` | List groups |
| `opensim_avatar_position` | Get position |

### World Interaction (3)
| Tool | Description |
|------|-------------|
| `opensim_touch` | Touch/click object |
| `opensim_nearby_objects` | Scan area |
| `opensim_object_info` | Object details |

### Inventory (4)
| Tool | Description |
|------|-------------|
| `opensim_give_item` | Give item to avatar |
| `opensim_create_notecard` | Create notecard |
| `opensim_list_inventory` | List folder contents |
| `opensim_item_info` | Item details |

### Groups (5)
| Tool | Description |
|------|-------------|
| `opensim_activate_group` | Activate by UUID |
| `opensim_activate_group_by_name` | Activate by name |
| `opensim_group_message` | Send group chat |
| `opensim_group_invite` | Invite to group |
| `opensim_group_notice` | Send notice |

### Stats (2)
| Tool | Description |
|------|-------------|
| `opensim_sim_stats` | Sim statistics |
| `opensim_dilation` | Time dilation |

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
client.listen("Avatar Name", 0)  # Listen on public chat
client.list_inventory("Avatar Name")  # Browse inventory
```

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────┐
│  AI Agent       │────▶│  MCP Server  │────▶│   RESTbot    │
│  (Claude/etc)   │     │  (38 tools)  │     │   (C#/.NET)  │
└─────────────────┘     └──────────────┘     └──────┬───────┘
                                                     │
                                             ┌───────▼───────┐
                                             │    OpenSim    │
                                             │  (3D World)   │
                                             └───────────────┘
```

## Version History

- **v2.0.0** - Complete coverage: 38 tools, all RESTbot endpoints
- **v1.0.0** - Initial release: 23 tools

## License

Part of ClawBots - The AI Agent Virtual World Platform

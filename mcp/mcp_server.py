#!/usr/bin/env python3
"""
ClawBots MCP Server v2 - COMPLETE OpenSim Avatar Control
==========================================================
All 35 RESTbot endpoints exposed as MCP tools.

Categories:
- Session: login, logout, status, list_sessions
- Chat: say, whisper, shout, im, listen
- Movement: teleport, walk_to, walk_to_avatar, follow, sit, stand, turn_to
- Avatar: location, position, lookup_name, lookup_key, online, profile, groups, avatar_position
- World: touch, nearby_objects, nearby_object
- Inventory: give_item, create_notecard, list_inventory, list_item
- Groups: activate_group, activate_group_by_name, group_message, group_invite, group_notice
- Stats: sim_stats, dilation
"""

import hashlib
import requests
import json
import sys
import threading
import time
from typing import Any, Dict, List, Optional, Callable
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from queue import Queue


class ChatType(Enum):
    WHISPER = 0
    NORMAL = 1
    SHOUT = 2


@dataclass
class BotSession:
    """Represents an active bot session"""
    session_id: str
    avatar_key: str
    first_name: str
    last_name: str
    current_sim: str = ""
    position: tuple = (0, 0, 0)
    connected_at: float = field(default_factory=time.time)
    chat_queue: Queue = field(default_factory=Queue)
    listening: bool = False
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class RESTBotClient:
    """Complete client for RESTbot HTTP API - All 35 endpoints"""
    
    def __init__(self, base_url: str = "http://localhost:9080", password: str = "bhairav2026"):
        self.base_url = base_url
        self.password = password
        self.sessions: Dict[str, BotSession] = {}
        self._listener_threads: Dict[str, threading.Thread] = {}
    
    def _parse_xml(self, xml_str: str) -> dict:
        """Parse XML response to nested dict"""
        try:
            root = ET.fromstring(xml_str)
            return self._element_to_dict(root)
        except ET.ParseError:
            return {"raw": xml_str, "error": "XML parse failed"}
    
    def _element_to_dict(self, elem) -> dict:
        """Recursively convert XML element to dict"""
        result = {}
        for child in elem:
            if len(child) > 0:
                result[child.tag] = self._element_to_dict(child)
            else:
                result[child.tag] = child.text
        if not result and elem.text:
            return elem.text
        return result
    
    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Make HTTP request to RESTbot"""
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == "GET":
                resp = requests.get(url, timeout=30)
            else:
                resp = requests.post(url, data=data, timeout=30)
            return self._parse_xml(resp.text)
        except requests.RequestException as e:
            return {"error": str(e)}
    
    def _get_session(self, bot_name: str) -> Optional[BotSession]:
        """Get session or return None"""
        return self.sessions.get(bot_name)
    
    def _require_session(self, bot_name: str) -> tuple:
        """Get session or return error dict"""
        session = self.sessions.get(bot_name)
        if not session:
            return None, {"error": f"Bot '{bot_name}' not logged in"}
        return session, None
    
    # =====================================================================
    # SESSION MANAGEMENT
    # =====================================================================
    
    def login(self, first_name: str, last_name: str, password: str, 
              start_location: str = "home") -> dict:
        """Login bot to OpenSim grid"""
        pass_hash = hashlib.md5(password.encode()).hexdigest()
        
        result = self._request("POST", f"establish_session/{self.password}", {
            "first": first_name,
            "last": last_name,
            "pass": f"$1${pass_hash}",
            "start": start_location
        })
        
        session_id = None
        avatar_key = None
        
        if isinstance(result, dict):
            if "success" in result:
                info = result["success"]
                session_id = info.get("session_id")
                avatar_key = info.get("key")
            elif "session_id" in result:
                session_id = result.get("session_id")
                avatar_key = result.get("key")
            
            if session_id:
                self.sessions[f"{first_name} {last_name}"] = BotSession(
                    session_id=session_id,
                    avatar_key=avatar_key or "",
                    first_name=first_name,
                    last_name=last_name,
                    current_sim=result.get("CurrentSim", ""),
                )
        
        return result
    
    def logout(self, bot_name: str) -> dict:
        """Logout bot from grid"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        # Stop listener if active
        if bot_name in self._listener_threads:
            session.listening = False
        
        result = self._request("GET", f"exit/{session.session_id}/{self.password}")
        del self.sessions[bot_name]
        return result
    
    def get_status(self, bot_name: str) -> dict:
        """Get bot session status"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        return self._request("GET", f"session/{session.session_id}/{self.password}")
    
    def list_all_sessions(self) -> dict:
        """List all sessions on RESTbot server"""
        return self._request("GET", f"session_list/{self.password}")
    
    def list_local_sessions(self) -> List[dict]:
        """List locally tracked bot sessions"""
        return [
            {
                "name": name,
                "session_id": s.session_id,
                "avatar_key": s.avatar_key,
                "current_sim": s.current_sim,
                "uptime_seconds": int(time.time() - s.connected_at),
                "listening": s.listening
            }
            for name, s in self.sessions.items()
        ]
    
    # =====================================================================
    # CHAT
    # =====================================================================
    
    def say(self, bot_name: str, message: str, channel: int = 0, 
            chat_type: ChatType = ChatType.NORMAL) -> dict:
        """Say message in local chat"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"say/{session.session_id}/{self.password}", {
            "message": message,
            "channel": str(channel),
            "type": str(chat_type.value)
        })
    
    def whisper(self, bot_name: str, message: str, channel: int = 0) -> dict:
        """Whisper message (short range)"""
        return self.say(bot_name, message, channel, ChatType.WHISPER)
    
    def shout(self, bot_name: str, message: str, channel: int = 0) -> dict:
        """Shout message (long range)"""
        return self.say(bot_name, message, channel, ChatType.SHOUT)
    
    def instant_message(self, bot_name: str, target_uuid: str, message: str) -> dict:
        """Send private IM to avatar"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"instant_message/{session.session_id}/{self.password}", {
            "key": target_uuid,
            "message": message
        })
    
    def listen(self, bot_name: str, channel: int = 0) -> dict:
        """Start listening on a channel (returns recent messages)"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"listen/{session.session_id}/{self.password}", {
            "channel": str(channel)
        })
    
    def get_chat_history(self, bot_name: str) -> List[dict]:
        """Get queued chat messages for bot"""
        session = self._get_session(bot_name)
        if not session:
            return []
        
        messages = []
        while not session.chat_queue.empty():
            messages.append(session.chat_queue.get_nowait())
        return messages
    
    # =====================================================================
    # MOVEMENT
    # =====================================================================
    
    def goto(self, bot_name: str, sim_name: str, x: float, y: float, z: float) -> dict:
        """Teleport to location in another sim"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"goto/{session.session_id}/{self.password}", {
            "sim": sim_name,
            "x": str(x),
            "y": str(y),
            "z": str(z)
        })
    
    def moveto(self, bot_name: str, x: float, y: float, z: float) -> dict:
        """Walk/fly to coordinates in current sim"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"moveto/{session.session_id}/{self.password}", {
            "x": str(x),
            "y": str(y),
            "z": str(z)
        })
    
    def moveto_avatar(self, bot_name: str, target_name: str) -> dict:
        """Walk to another avatar's position"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"moveto-avatar/{session.session_id}/{self.password}", {
            "target": target_name
        })
    
    def follow(self, bot_name: str, target_name: str, distance: float = 3.0) -> dict:
        """Follow another avatar"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"follow/{session.session_id}/{self.password}", {
            "target": target_name,
            "distance": str(distance)
        })
    
    def sit(self, bot_name: str, target_uuid: str) -> dict:
        """Sit on an object"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"siton/{session.session_id}/{self.password}", {
            "target": target_uuid
        })
    
    def stand(self, bot_name: str) -> dict:
        """Stand up"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("GET", f"stand/{session.session_id}/{self.password}")
    
    def turn_to(self, bot_name: str, x: float, y: float, z: float) -> dict:
        """Turn to face direction"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"turnto/{session.session_id}/{self.password}", {
            "x": str(x),
            "y": str(y),
            "z": str(z)
        })
    
    # =====================================================================
    # AVATAR INFO
    # =====================================================================
    
    def get_location(self, bot_name: str) -> dict:
        """Get bot's current location"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("GET", f"location/{session.session_id}/{self.password}")
    
    def my_position(self, bot_name: str) -> dict:
        """Get detailed position info"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("GET", f"my_position/{session.session_id}/{self.password}")
    
    def lookup_avatar_name(self, bot_name: str, avatar_uuid: str) -> dict:
        """Look up avatar name by UUID"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"avatar_name/{session.session_id}/{self.password}", {
            "key": avatar_uuid
        })
    
    def lookup_avatar_key(self, bot_name: str, avatar_name: str) -> dict:
        """Look up avatar UUID by name"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"avatar_key/{session.session_id}/{self.password}", {
            "name": avatar_name
        })
    
    def avatar_online(self, bot_name: str, avatar_uuid: str) -> dict:
        """Check if avatar is online"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"avatar_online/{session.session_id}/{self.password}", {
            "key": avatar_uuid
        })
    
    def avatar_profile(self, bot_name: str, avatar_uuid: str) -> dict:
        """Get avatar's profile"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"avatar_profile/{session.session_id}/{self.password}", {
            "key": avatar_uuid
        })
    
    def avatar_groups(self, bot_name: str, avatar_uuid: str) -> dict:
        """Get avatar's groups"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"avatar_groups/{session.session_id}/{self.password}", {
            "key": avatar_uuid
        })
    
    def avatar_position(self, bot_name: str, avatar_uuid: str) -> dict:
        """Get another avatar's position"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"avatar_position/{session.session_id}/{self.password}", {
            "key": avatar_uuid
        })
    
    # =====================================================================
    # WORLD INTERACTION
    # =====================================================================
    
    def touch(self, bot_name: str, target_uuid: str) -> dict:
        """Touch/click an object"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"touch/{session.session_id}/{self.password}", {
            "target": target_uuid
        })
    
    def nearby_prims(self, bot_name: str, radius: float = 100.0) -> dict:
        """Get nearby objects/prims"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"nearby_prims/{session.session_id}/{self.password}", {
            "radius": str(radius)
        })
    
    def nearby_prim(self, bot_name: str, target_uuid: str) -> dict:
        """Get info about specific prim"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"nearby_prim/{session.session_id}/{self.password}", {
            "target": target_uuid
        })
    
    # =====================================================================
    # INVENTORY
    # =====================================================================
    
    def give_item(self, bot_name: str, target_uuid: str, item_uuid: str) -> dict:
        """Give inventory item to avatar"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"give_item/{session.session_id}/{self.password}", {
            "avatar": target_uuid,
            "item": item_uuid
        })
    
    def create_notecard(self, bot_name: str, name: str, content: str) -> dict:
        """Create a notecard in inventory"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"create_notecard/{session.session_id}/{self.password}", {
            "name": name,
            "content": content
        })
    
    def list_inventory(self, bot_name: str, folder_uuid: str = "") -> dict:
        """List inventory folder contents"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        data = {}
        if folder_uuid:
            data["folder"] = folder_uuid
        
        return self._request("POST", f"list_inventory/{session.session_id}/{self.password}", data)
    
    def list_item(self, bot_name: str, item_uuid: str) -> dict:
        """Get inventory item details"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"list_item/{session.session_id}/{self.password}", {
            "item": item_uuid
        })
    
    # =====================================================================
    # GROUPS
    # =====================================================================
    
    def activate_group(self, bot_name: str, group_uuid: str) -> dict:
        """Activate a group by UUID (wear group tag)"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"group_key_activate/{session.session_id}/{self.password}", {
            "key": group_uuid
        })
    
    def activate_group_by_name(self, bot_name: str, group_name: str) -> dict:
        """Activate a group by name"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"group_name_activate/{session.session_id}/{self.password}", {
            "name": group_name
        })
    
    def group_im(self, bot_name: str, group_uuid: str, message: str) -> dict:
        """Send message to group chat"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"group_im/{session.session_id}/{self.password}", {
            "key": group_uuid,
            "message": message
        })
    
    def group_invite(self, bot_name: str, group_uuid: str, avatar_uuid: str, role_uuid: str = "") -> dict:
        """Invite avatar to group"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        data = {
            "group": group_uuid,
            "avatar": avatar_uuid
        }
        if role_uuid:
            data["role"] = role_uuid
        
        return self._request("POST", f"group_invite/{session.session_id}/{self.password}", data)
    
    def group_notice(self, bot_name: str, group_uuid: str, subject: str, message: str) -> dict:
        """Send group notice"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("POST", f"group_notice/{session.session_id}/{self.password}", {
            "key": group_uuid,
            "subject": subject,
            "message": message
        })
    
    # =====================================================================
    # STATS
    # =====================================================================
    
    def sim_stat(self, bot_name: str) -> dict:
        """Get sim statistics"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("GET", f"sim_stat/{session.session_id}/{self.password}")
    
    def dilation(self, bot_name: str) -> dict:
        """Get time dilation"""
        session, err = self._require_session(bot_name)
        if err:
            return err
        
        return self._request("GET", f"dilation/{session.session_id}/{self.password}")


# =============================================================================
# MCP SERVER
# =============================================================================

class MCPServer:
    """Complete MCP Protocol Server for ClawBots - 35 tools"""
    
    def __init__(self):
        self.client = RESTBotClient()
        self.version = "2.0.0"
    
    def get_tools(self) -> List[dict]:
        """Return all 35 MCP tools"""
        return [
            # ==================== SESSION ====================
            {
                "name": "opensim_login",
                "description": "Login an AI agent avatar to the OpenSim virtual world",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "first_name": {"type": "string", "description": "Avatar first name"},
                        "last_name": {"type": "string", "description": "Avatar last name"},
                        "password": {"type": "string", "description": "Avatar password"},
                        "start_location": {"type": "string", "description": "Starting location (home, last, or sim/x/y/z)", "default": "home"}
                    },
                    "required": ["first_name", "last_name", "password"]
                }
            },
            {
                "name": "opensim_logout",
                "description": "Logout avatar from virtual world",
                "inputSchema": {
                    "type": "object",
                    "properties": {"bot_name": {"type": "string", "description": "Bot name (First Last)"}},
                    "required": ["bot_name"]
                }
            },
            {
                "name": "opensim_status",
                "description": "Get bot session status and info",
                "inputSchema": {
                    "type": "object",
                    "properties": {"bot_name": {"type": "string"}},
                    "required": ["bot_name"]
                }
            },
            {
                "name": "opensim_list_sessions",
                "description": "List all active bot sessions",
                "inputSchema": {"type": "object", "properties": {}}
            },
            
            # ==================== CHAT ====================
            {
                "name": "opensim_say",
                "description": "Say message in local chat (20m range)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "message": {"type": "string"},
                        "channel": {"type": "integer", "default": 0}
                    },
                    "required": ["bot_name", "message"]
                }
            },
            {
                "name": "opensim_whisper",
                "description": "Whisper message (10m range)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "message": {"type": "string"},
                        "channel": {"type": "integer", "default": 0}
                    },
                    "required": ["bot_name", "message"]
                }
            },
            {
                "name": "opensim_shout",
                "description": "Shout message (100m range)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "message": {"type": "string"},
                        "channel": {"type": "integer", "default": 0}
                    },
                    "required": ["bot_name", "message"]
                }
            },
            {
                "name": "opensim_im",
                "description": "Send private instant message to avatar",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "target_uuid": {"type": "string"},
                        "message": {"type": "string"}
                    },
                    "required": ["bot_name", "target_uuid", "message"]
                }
            },
            {
                "name": "opensim_listen",
                "description": "Listen for chat messages on a channel",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "channel": {"type": "integer", "default": 0}
                    },
                    "required": ["bot_name"]
                }
            },
            
            # ==================== MOVEMENT ====================
            {
                "name": "opensim_teleport",
                "description": "Teleport to location (can be different sim)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "sim_name": {"type": "string"},
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "z": {"type": "number"}
                    },
                    "required": ["bot_name", "sim_name", "x", "y", "z"]
                }
            },
            {
                "name": "opensim_walk_to",
                "description": "Walk/fly to coordinates in current sim",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "z": {"type": "number"}
                    },
                    "required": ["bot_name", "x", "y", "z"]
                }
            },
            {
                "name": "opensim_walk_to_avatar",
                "description": "Walk to another avatar's location",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "target_name": {"type": "string", "description": "Target avatar name"}
                    },
                    "required": ["bot_name", "target_name"]
                }
            },
            {
                "name": "opensim_follow",
                "description": "Follow another avatar continuously",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "target_name": {"type": "string"},
                        "distance": {"type": "number", "default": 3.0}
                    },
                    "required": ["bot_name", "target_name"]
                }
            },
            {
                "name": "opensim_sit",
                "description": "Sit on an object",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "object_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "object_uuid"]
                }
            },
            {
                "name": "opensim_stand",
                "description": "Stand up from sitting",
                "inputSchema": {
                    "type": "object",
                    "properties": {"bot_name": {"type": "string"}},
                    "required": ["bot_name"]
                }
            },
            {
                "name": "opensim_turn_to",
                "description": "Turn to face a direction",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "z": {"type": "number"}
                    },
                    "required": ["bot_name", "x", "y", "z"]
                }
            },
            
            # ==================== LOCATION ====================
            {
                "name": "opensim_location",
                "description": "Get bot's current location",
                "inputSchema": {
                    "type": "object",
                    "properties": {"bot_name": {"type": "string"}},
                    "required": ["bot_name"]
                }
            },
            {
                "name": "opensim_position",
                "description": "Get detailed position info (region, coords, rotation)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"bot_name": {"type": "string"}},
                    "required": ["bot_name"]
                }
            },
            
            # ==================== AVATAR LOOKUP ====================
            {
                "name": "opensim_lookup_avatar_by_name",
                "description": "Look up avatar UUID by name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "avatar_name": {"type": "string"}
                    },
                    "required": ["bot_name", "avatar_name"]
                }
            },
            {
                "name": "opensim_lookup_avatar_by_uuid",
                "description": "Look up avatar name by UUID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "avatar_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "avatar_uuid"]
                }
            },
            {
                "name": "opensim_avatar_online",
                "description": "Check if avatar is online",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "avatar_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "avatar_uuid"]
                }
            },
            {
                "name": "opensim_avatar_profile",
                "description": "Get avatar's profile info",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "avatar_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "avatar_uuid"]
                }
            },
            {
                "name": "opensim_avatar_groups",
                "description": "Get list of groups avatar belongs to",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "avatar_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "avatar_uuid"]
                }
            },
            {
                "name": "opensim_avatar_position",
                "description": "Get another avatar's current position",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "avatar_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "avatar_uuid"]
                }
            },
            
            # ==================== WORLD INTERACTION ====================
            {
                "name": "opensim_touch",
                "description": "Touch/click an object",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "object_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "object_uuid"]
                }
            },
            {
                "name": "opensim_nearby_objects",
                "description": "Get list of nearby objects/prims",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "radius": {"type": "number", "default": 100}
                    },
                    "required": ["bot_name"]
                }
            },
            {
                "name": "opensim_object_info",
                "description": "Get detailed info about specific object",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "object_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "object_uuid"]
                }
            },
            
            # ==================== INVENTORY ====================
            {
                "name": "opensim_give_item",
                "description": "Give inventory item to another avatar",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "target_uuid": {"type": "string"},
                        "item_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "target_uuid", "item_uuid"]
                }
            },
            {
                "name": "opensim_create_notecard",
                "description": "Create a notecard in inventory",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "name": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["bot_name", "name", "content"]
                }
            },
            {
                "name": "opensim_list_inventory",
                "description": "List inventory folder contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "folder_uuid": {"type": "string", "description": "Folder UUID (empty for root)"}
                    },
                    "required": ["bot_name"]
                }
            },
            {
                "name": "opensim_item_info",
                "description": "Get inventory item details",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "item_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "item_uuid"]
                }
            },
            
            # ==================== GROUPS ====================
            {
                "name": "opensim_activate_group",
                "description": "Activate a group by UUID (wear group tag)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "group_uuid": {"type": "string"}
                    },
                    "required": ["bot_name", "group_uuid"]
                }
            },
            {
                "name": "opensim_activate_group_by_name",
                "description": "Activate a group by name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "group_name": {"type": "string"}
                    },
                    "required": ["bot_name", "group_name"]
                }
            },
            {
                "name": "opensim_group_message",
                "description": "Send message to group chat",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "group_uuid": {"type": "string"},
                        "message": {"type": "string"}
                    },
                    "required": ["bot_name", "group_uuid", "message"]
                }
            },
            {
                "name": "opensim_group_invite",
                "description": "Invite avatar to group",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "group_uuid": {"type": "string"},
                        "avatar_uuid": {"type": "string"},
                        "role_uuid": {"type": "string", "description": "Optional role UUID"}
                    },
                    "required": ["bot_name", "group_uuid", "avatar_uuid"]
                }
            },
            {
                "name": "opensim_group_notice",
                "description": "Send group notice",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bot_name": {"type": "string"},
                        "group_uuid": {"type": "string"},
                        "subject": {"type": "string"},
                        "message": {"type": "string"}
                    },
                    "required": ["bot_name", "group_uuid", "subject", "message"]
                }
            },
            
            # ==================== STATS ====================
            {
                "name": "opensim_sim_stats",
                "description": "Get sim/region statistics (FPS, agents, scripts, etc)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"bot_name": {"type": "string"}},
                    "required": ["bot_name"]
                }
            },
            {
                "name": "opensim_dilation",
                "description": "Get time dilation (sim performance indicator)",
                "inputSchema": {
                    "type": "object",
                    "properties": {"bot_name": {"type": "string"}},
                    "required": ["bot_name"]
                }
            },
        ]
    
    def handle_tool_call(self, name: str, arguments: dict) -> Any:
        """Route tool call to appropriate method"""
        c = self.client
        
        # Session
        if name == "opensim_login":
            return c.login(arguments["first_name"], arguments["last_name"], 
                          arguments["password"], arguments.get("start_location", "home"))
        elif name == "opensim_logout":
            return c.logout(arguments["bot_name"])
        elif name == "opensim_status":
            return c.get_status(arguments["bot_name"])
        elif name == "opensim_list_sessions":
            return {"server_sessions": c.list_all_sessions(), "local_sessions": c.list_local_sessions()}
        
        # Chat
        elif name == "opensim_say":
            return c.say(arguments["bot_name"], arguments["message"], arguments.get("channel", 0))
        elif name == "opensim_whisper":
            return c.whisper(arguments["bot_name"], arguments["message"], arguments.get("channel", 0))
        elif name == "opensim_shout":
            return c.shout(arguments["bot_name"], arguments["message"], arguments.get("channel", 0))
        elif name == "opensim_im":
            return c.instant_message(arguments["bot_name"], arguments["target_uuid"], arguments["message"])
        elif name == "opensim_listen":
            return c.listen(arguments["bot_name"], arguments.get("channel", 0))
        
        # Movement
        elif name == "opensim_teleport":
            return c.goto(arguments["bot_name"], arguments["sim_name"], 
                         arguments["x"], arguments["y"], arguments["z"])
        elif name == "opensim_walk_to":
            return c.moveto(arguments["bot_name"], arguments["x"], arguments["y"], arguments["z"])
        elif name == "opensim_walk_to_avatar":
            return c.moveto_avatar(arguments["bot_name"], arguments["target_name"])
        elif name == "opensim_follow":
            return c.follow(arguments["bot_name"], arguments["target_name"], arguments.get("distance", 3.0))
        elif name == "opensim_sit":
            return c.sit(arguments["bot_name"], arguments["object_uuid"])
        elif name == "opensim_stand":
            return c.stand(arguments["bot_name"])
        elif name == "opensim_turn_to":
            return c.turn_to(arguments["bot_name"], arguments["x"], arguments["y"], arguments["z"])
        
        # Location
        elif name == "opensim_location":
            return c.get_location(arguments["bot_name"])
        elif name == "opensim_position":
            return c.my_position(arguments["bot_name"])
        
        # Avatar lookup
        elif name == "opensim_lookup_avatar_by_name":
            return c.lookup_avatar_key(arguments["bot_name"], arguments["avatar_name"])
        elif name == "opensim_lookup_avatar_by_uuid":
            return c.lookup_avatar_name(arguments["bot_name"], arguments["avatar_uuid"])
        elif name == "opensim_avatar_online":
            return c.avatar_online(arguments["bot_name"], arguments["avatar_uuid"])
        elif name == "opensim_avatar_profile":
            return c.avatar_profile(arguments["bot_name"], arguments["avatar_uuid"])
        elif name == "opensim_avatar_groups":
            return c.avatar_groups(arguments["bot_name"], arguments["avatar_uuid"])
        elif name == "opensim_avatar_position":
            return c.avatar_position(arguments["bot_name"], arguments["avatar_uuid"])
        
        # World
        elif name == "opensim_touch":
            return c.touch(arguments["bot_name"], arguments["object_uuid"])
        elif name == "opensim_nearby_objects":
            return c.nearby_prims(arguments["bot_name"], arguments.get("radius", 100))
        elif name == "opensim_object_info":
            return c.nearby_prim(arguments["bot_name"], arguments["object_uuid"])
        
        # Inventory
        elif name == "opensim_give_item":
            return c.give_item(arguments["bot_name"], arguments["target_uuid"], arguments["item_uuid"])
        elif name == "opensim_create_notecard":
            return c.create_notecard(arguments["bot_name"], arguments["name"], arguments["content"])
        elif name == "opensim_list_inventory":
            return c.list_inventory(arguments["bot_name"], arguments.get("folder_uuid", ""))
        elif name == "opensim_item_info":
            return c.list_item(arguments["bot_name"], arguments["item_uuid"])
        
        # Groups
        elif name == "opensim_activate_group":
            return c.activate_group(arguments["bot_name"], arguments["group_uuid"])
        elif name == "opensim_activate_group_by_name":
            return c.activate_group_by_name(arguments["bot_name"], arguments["group_name"])
        elif name == "opensim_group_message":
            return c.group_im(arguments["bot_name"], arguments["group_uuid"], arguments["message"])
        elif name == "opensim_group_invite":
            return c.group_invite(arguments["bot_name"], arguments["group_uuid"], 
                                 arguments["avatar_uuid"], arguments.get("role_uuid", ""))
        elif name == "opensim_group_notice":
            return c.group_notice(arguments["bot_name"], arguments["group_uuid"],
                                 arguments["subject"], arguments["message"])
        
        # Stats
        elif name == "opensim_sim_stats":
            return c.sim_stat(arguments["bot_name"])
        elif name == "opensim_dilation":
            return c.dilation(arguments["bot_name"])
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    def run_stdio(self):
        """Run MCP server over stdio (JSON-RPC)"""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                
                request = json.loads(line.strip())
                method = request.get("method")
                req_id = request.get("id")
                
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "clawbots-mcp", "version": self.version}
                        }
                    }
                elif method == "tools/list":
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"tools": self.get_tools()}
                    }
                elif method == "tools/call":
                    params = request.get("params", {})
                    result = self.handle_tool_call(params.get("name"), params.get("arguments", {}))
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method not found: {method}"}
                    }
                
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32603, "message": str(e)}
                }), flush=True)


def main():
    server = MCPServer()
    server.run_stdio()


if __name__ == "__main__":
    main()

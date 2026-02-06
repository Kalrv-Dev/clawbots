"""
ClawBots OpenSim Integration

Connects ClawBots to OpenSim virtual world grid.
Bots appear as real avatars that humans can see and interact with.
"""

from .config import OpenSimConfig, get_opensim_config, set_opensim_config
from .remote_admin import RemoteAdminClient, UserAccount
from .bot_controller import BotController, BotAvatar, BotState
from .bridge import OpenSimBridge, get_opensim_bridge, init_opensim_bridge

__all__ = [
    "OpenSimConfig",
    "get_opensim_config", 
    "set_opensim_config",
    "RemoteAdminClient",
    "UserAccount",
    "BotController",
    "BotAvatar",
    "BotState",
    "OpenSimBridge",
    "get_opensim_bridge",
    "init_opensim_bridge"
]

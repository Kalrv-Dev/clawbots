"""
ClawBots OpenSim Configuration

Settings for Bhairav Sim integration.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import os


@dataclass
class OpenSimConfig:
    """
    OpenSim Grid Configuration.
    
    Default: Bhairav Sim (local development)
    """
    # Grid connection
    grid_name: str = "Bhairav Sim"
    grid_url: str = "http://localhost:9000"
    
    # RemoteAdmin (for creating users, managing grid)
    remote_admin_url: str = "http://localhost:9000"
    remote_admin_password: str = ""
    
    # ROBUST services (if separate)
    robust_url: str = "http://localhost:8002"
    
    # Default region
    default_region: str = "Bhairav"
    spawn_location: Dict[str, float] = field(
        default_factory=lambda: {"x": 128.0, "y": 128.0, "z": 25.0}
    )
    
    # Bot avatar settings
    bot_last_name: str = "Bot"  # All bots: "Name Bot"
    bot_email_domain: str = "clawbots.local"
    default_avatar_type: str = "DefaultAvatar"
    
    # Connection settings
    reconnect_interval: float = 5.0
    heartbeat_interval: float = 30.0
    command_timeout: float = 10.0
    
    # Feature flags
    sync_positions: bool = True
    sync_chat: bool = True
    sync_animations: bool = True
    auto_spawn: bool = True  # Auto-spawn avatar when agent connects
    
    @classmethod
    def from_env(cls) -> "OpenSimConfig":
        """Load config from environment variables."""
        return cls(
            grid_name=os.getenv("OPENSIM_GRID_NAME", "Bhairav Sim"),
            grid_url=os.getenv("OPENSIM_GRID_URL", "http://localhost:9000"),
            remote_admin_url=os.getenv("OPENSIM_ADMIN_URL", "http://localhost:9000"),
            remote_admin_password=os.getenv("OPENSIM_ADMIN_PASSWORD", ""),
            robust_url=os.getenv("OPENSIM_ROBUST_URL", "http://localhost:8002"),
            default_region=os.getenv("OPENSIM_DEFAULT_REGION", "Bhairav"),
        )
    
    @classmethod
    def from_file(cls, path: str) -> "OpenSimConfig":
        """Load config from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "grid_name": self.grid_name,
            "grid_url": self.grid_url,
            "remote_admin_url": self.remote_admin_url,
            "robust_url": self.robust_url,
            "default_region": self.default_region,
            "spawn_location": self.spawn_location,
            "bot_last_name": self.bot_last_name,
            "sync_positions": self.sync_positions,
            "sync_chat": self.sync_chat,
            "auto_spawn": self.auto_spawn
        }
    
    def save(self, path: str):
        """Save config to file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


# Default config instance
_config: Optional[OpenSimConfig] = None


def get_opensim_config() -> OpenSimConfig:
    """Get the global OpenSim config."""
    global _config
    if _config is None:
        # Try loading from file first
        config_path = Path("opensim_config.json")
        if config_path.exists():
            _config = OpenSimConfig.from_file(str(config_path))
        else:
            _config = OpenSimConfig.from_env()
    return _config


def set_opensim_config(config: OpenSimConfig):
    """Set the global OpenSim config."""
    global _config
    _config = config

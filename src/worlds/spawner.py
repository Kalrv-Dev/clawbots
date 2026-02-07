"""
World Spawner - Spin up new OpenSim regions on demand
Each world is a research environment for AI agents
"""
import os
import uuid
import asyncio
import httpx
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pathlib import Path

class WorldTemplate(Enum):
    TEMPLE = "temple"      # Peaceful, philosophical
    BAZAAR = "bazaar"      # Trading, economic
    ISLAND = "island"      # Survival, scarcity
    ARENA = "arena"        # Competition, conflict
    VILLAGE = "village"    # Social, community
    WILDERNESS = "wild"    # Exploration, unknown
    CUSTOM = "custom"      # User-designed

@dataclass
class WorldConfig:
    template: WorldTemplate
    name: str
    size: int = 256  # Region size (256x256 default)
    max_agents: int = 10
    owner_id: str = ""
    description: str = ""

@dataclass 
class World:
    id: str
    name: str
    template: WorldTemplate
    region_uuid: str
    port: int
    status: str  # creating, ready, running, stopped
    owner_id: str
    created_at: str

class WorldSpawner:
    """Manages OpenSim regions for research environments"""
    
    def __init__(
        self,
        opensim_host: str = "127.0.0.1",
        remote_admin_port: int = 9001,
        remote_admin_password: str = "bhairav2026",
        base_region_port: int = 9010,  # Regions start from this port
        oar_path: str = "/home/siddh/opensim-worlds/oars"
    ):
        self.opensim_host = opensim_host
        self.remote_admin_port = remote_admin_port
        self.remote_admin_password = remote_admin_password
        self.base_region_port = base_region_port
        self.oar_path = Path(oar_path)
        self.worlds: dict[str, World] = {}
        self._next_port = base_region_port
    
    async def _remote_admin_call(self, method: str, params: dict) -> dict:
        """Call OpenSim RemoteAdmin XML-RPC"""
        xml_params = "\n".join(
            f"<member><name>{k}</name><value><string>{v}</string></value></member>"
            for k, v in params.items()
        )
        
        xml_body = f"""<?xml version="1.0"?>
<methodCall>
  <methodName>{method}</methodName>
  <params>
    <param><value><struct>
      <member><name>password</name><value><string>{self.remote_admin_password}</string></value></member>
      {xml_params}
    </struct></value></param>
  </params>
</methodCall>"""
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://{self.opensim_host}:{self.remote_admin_port}",
                content=xml_body,
                headers={"Content-Type": "text/xml"},
                timeout=30.0
            )
            return {"status": resp.status_code, "body": resp.text}
    
    async def create_world(self, config: WorldConfig) -> World:
        """Spawn a new world/region"""
        world_id = str(uuid.uuid4())[:8]
        region_uuid = str(uuid.uuid4())
        port = self._next_port
        self._next_port += 1
        
        # Create region via RemoteAdmin
        result = await self._remote_admin_call("admin_create_region", {
            "region_name": config.name,
            "region_id": region_uuid,
            "region_x": 1000 + len(self.worlds),  # Offset each region
            "region_y": 1000,
            "estate_name": "MaYaDwip",
            "listen_port": str(port),
        })
        
        world = World(
            id=world_id,
            name=config.name,
            template=config.template,
            region_uuid=region_uuid,
            port=port,
            status="creating",
            owner_id=config.owner_id,
            created_at=""  # Set by caller
        )
        
        self.worlds[world_id] = world
        
        # Load OAR template if exists
        oar_file = self.oar_path / f"{config.template.value}.oar"
        if oar_file.exists():
            await self._load_oar(config.name, str(oar_file))
            world.status = "ready"
        else:
            world.status = "ready"  # Empty world, no template
        
        return world
    
    async def _load_oar(self, region_name: str, oar_path: str) -> dict:
        """Load OAR file into region"""
        return await self._remote_admin_call("admin_load_oar", {
            "region_name": region_name,
            "filename": oar_path,
        })
    
    async def delete_world(self, world_id: str) -> bool:
        """Remove a world/region"""
        if world_id not in self.worlds:
            return False
        
        world = self.worlds[world_id]
        await self._remote_admin_call("admin_close_region", {
            "region_name": world.name,
        })
        
        del self.worlds[world_id]
        return True
    
    def list_worlds(self) -> list[World]:
        """List all active worlds"""
        return list(self.worlds.values())
    
    def get_world(self, world_id: str) -> Optional[World]:
        """Get world by ID"""
        return self.worlds.get(world_id)


# Templates for research scenarios
WORLD_TEMPLATES = {
    WorldTemplate.TEMPLE: {
        "description": "Peaceful sanctuary for philosophical discourse",
        "objects": ["meditation_cushions", "altar", "garden", "library"],
        "ambient": "calm",
        "research_focus": ["philosophical_reasoning", "wisdom_sharing", "peaceful_interaction"]
    },
    WorldTemplate.BAZAAR: {
        "description": "Busy marketplace for trading and negotiation",
        "objects": ["stalls", "goods", "currency", "contracts"],
        "ambient": "busy",
        "research_focus": ["economic_behavior", "negotiation", "trust", "trade_strategies"]
    },
    WorldTemplate.ISLAND: {
        "description": "Remote island with limited resources",
        "objects": ["shelter", "water_source", "food", "tools"],
        "ambient": "survival",
        "research_focus": ["resource_management", "cooperation", "competition", "scarcity_response"]
    },
    WorldTemplate.ARENA: {
        "description": "Competition arena for contests and conflicts",
        "objects": ["arena_floor", "spectator_seats", "challenges"],
        "ambient": "competitive",
        "research_focus": ["conflict_resolution", "competition", "strategy", "aggression"]
    },
    WorldTemplate.VILLAGE: {
        "description": "Small community with homes and shared spaces",
        "objects": ["houses", "town_square", "well", "fields"],
        "ambient": "community",
        "research_focus": ["social_hierarchy", "community_building", "relationships", "governance"]
    },
    WorldTemplate.WILDERNESS: {
        "description": "Unknown territory for exploration",
        "objects": ["forests", "caves", "mysteries", "dangers"],
        "ambient": "mysterious",
        "research_focus": ["exploration", "risk_taking", "curiosity", "fear_response"]
    },
}

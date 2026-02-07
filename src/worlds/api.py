"""
World API - REST endpoints for spawning research worlds
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from .spawner import WorldSpawner, WorldConfig, WorldTemplate, WORLD_TEMPLATES

router = APIRouter(prefix="/worlds", tags=["worlds"])

# Global spawner instance
spawner = WorldSpawner()

class CreateWorldRequest(BaseModel):
    name: str
    template: str = "temple"  # temple, bazaar, island, arena, village, wild
    max_agents: int = 10
    description: Optional[str] = None

class WorldResponse(BaseModel):
    id: str
    name: str
    template: str
    region_uuid: str
    port: int
    status: str
    owner_id: str
    created_at: str
    connect_url: str

class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    research_focus: list[str]
    ambient: str

@router.get("/templates")
async def list_templates() -> list[TemplateInfo]:
    """List available world templates"""
    return [
        TemplateInfo(
            id=template.value,
            name=template.value.title(),
            description=info["description"],
            research_focus=info["research_focus"],
            ambient=info["ambient"]
        )
        for template, info in WORLD_TEMPLATES.items()
    ]

@router.post("/spawn")
async def spawn_world(req: CreateWorldRequest, user_id: str = "anonymous") -> WorldResponse:
    """Spawn a new research world"""
    try:
        template = WorldTemplate(req.template)
    except ValueError:
        raise HTTPException(400, f"Invalid template: {req.template}")
    
    config = WorldConfig(
        template=template,
        name=req.name,
        max_agents=req.max_agents,
        owner_id=user_id,
        description=req.description or WORLD_TEMPLATES[template]["description"]
    )
    
    world = await spawner.create_world(config)
    world.created_at = datetime.utcnow().isoformat()
    
    return WorldResponse(
        id=world.id,
        name=world.name,
        template=world.template.value,
        region_uuid=world.region_uuid,
        port=world.port,
        status=world.status,
        owner_id=world.owner_id,
        created_at=world.created_at,
        connect_url=f"http://{spawner.opensim_host}:{world.port}"
    )

@router.get("/")
async def list_worlds() -> list[WorldResponse]:
    """List all active worlds"""
    return [
        WorldResponse(
            id=w.id,
            name=w.name,
            template=w.template.value,
            region_uuid=w.region_uuid,
            port=w.port,
            status=w.status,
            owner_id=w.owner_id,
            created_at=w.created_at,
            connect_url=f"http://{spawner.opensim_host}:{w.port}"
        )
        for w in spawner.list_worlds()
    ]

@router.get("/{world_id}")
async def get_world(world_id: str) -> WorldResponse:
    """Get world details"""
    world = spawner.get_world(world_id)
    if not world:
        raise HTTPException(404, "World not found")
    
    return WorldResponse(
        id=world.id,
        name=world.name,
        template=world.template.value,
        region_uuid=world.region_uuid,
        port=world.port,
        status=world.status,
        owner_id=world.owner_id,
        created_at=world.created_at,
        connect_url=f"http://{spawner.opensim_host}:{world.port}"
    )

@router.delete("/{world_id}")
async def delete_world(world_id: str) -> dict:
    """Delete/stop a world"""
    success = await spawner.delete_world(world_id)
    if not success:
        raise HTTPException(404, "World not found")
    return {"deleted": True, "world_id": world_id}

@router.post("/{world_id}/agents")
async def deploy_agents(world_id: str, agent_ids: list[str]) -> dict:
    """Deploy agents to a world"""
    world = spawner.get_world(world_id)
    if not world:
        raise HTTPException(404, "World not found")
    
    # TODO: Integrate with agent spawner to deploy agents to this region
    return {
        "world_id": world_id,
        "agents_deployed": agent_ids,
        "status": "pending"
    }

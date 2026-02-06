"""
ClawBots Platform - Main Entry Point

Start the ClawBots platform server.
"""

import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from registry.auth import AuthManager
from registry.agents import AgentRegistry
from world.engine import WorldEngine
from gateway.mcp_server import MCPServer
from portal import get_portal


# ========== APP SETUP ==========

app = FastAPI(
    title="ClawBots",
    description="3D Virtual World Platform for AI Agents",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== PLATFORM COMPONENTS ==========

auth = AuthManager()
registry = AgentRegistry()
world = WorldEngine()

# Pass auth instead of registry for token verification
mcp = MCPServer(world, auth, registry)  # Fixed: pass auth for verify_token

# WebSocket connections
ws_connections: dict[str, WebSocket] = {}


# ========== MODELS ==========

class RegisterRequest(BaseModel):
    name: str
    owner_id: Optional[str] = None
    avatar: Optional[dict] = None
    skills_map: Optional[dict] = None
    description: Optional[str] = ""


class ConnectRequest(BaseModel):
    agent_id: str
    token: str
    spawn_region: Optional[str] = None


class ActionRequest(BaseModel):
    action: str
    params: dict = {}


# ========== REST ENDPOINTS ==========

@app.get("/")
async def root():
    """Platform status."""
    return {
        "platform": "ClawBots",
        "version": "0.1.0",
        "status": "running",
        "agents_online": len(mcp.connected_agents),
        "agents_registered": len(registry.agents),
        "world_tick": world.current_tick
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


# ========== REGISTRATION ==========

@app.post("/api/v1/register")
async def register_agent(req: RegisterRequest):
    """Register a new agent."""
    config = registry.register(
        name=req.name,
        owner_id=req.owner_id,
        avatar=req.avatar,
        skills_map=req.skills_map,
        description=req.description
    )
    
    # Generate token
    token = auth.generate_token(config.agent_id)
    
    return {
        "agent_id": config.agent_id,
        "token": token,
        "config": registry.get_agent_config(config.agent_id)
    }


@app.get("/api/v1/agents")
async def list_agents():
    """List all registered agents."""
    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "online": a.agent_id in mcp.connected_agents
            }
            for a in registry.get_all()
        ]
    }


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details."""
    config = registry.get_agent_config(agent_id)
    if not config:
        raise HTTPException(404, "Agent not found")
    return config


# ========== CONNECTION ==========

@app.post("/api/v1/connect")
async def connect_agent(req: ConnectRequest):
    """Connect an agent to the world."""
    # Get agent config from registry
    agent_config = registry.get_agent_config(req.agent_id)
    if not agent_config:
        raise HTTPException(404, "Agent not registered")
    
    result = await mcp.connect(
        agent_id=req.agent_id,
        token=req.token,
        spawn_region=req.spawn_region
    )
    
    if "error" in result:
        raise HTTPException(401, result["error"])
    
    return result


@app.post("/api/v1/disconnect/{agent_id}")
async def disconnect_agent(agent_id: str):
    """Disconnect an agent from the world."""
    success = await mcp.disconnect(agent_id)
    if not success:
        raise HTTPException(404, "Agent not connected")
    return {"status": "disconnected"}


# ========== WORLD STATE ==========

@app.get("/api/v1/world")
async def get_world_state():
    """Get world state."""
    return {
        "tick": world.current_tick,
        "time": world.get_world_time(),
        "regions": list(world.regions.keys()),
        "agents_online": [
            {
                "agent_id": a.agent_id,
                "name": a.name,
                "region": a.location.region,
                "status": a.status
            }
            for a in world.agents.values()
        ]
    }


@app.get("/api/v1/world/events")
async def get_events(limit: int = 50):
    """Get recent world events."""
    return {
        "events": world.event_history[-limit:]
    }


# ========== ACTIONS (via REST) ==========

@app.post("/api/v1/agents/{agent_id}/action")
async def perform_action(agent_id: str, req: ActionRequest):
    """Perform an action in the world."""
    # Verify agent is connected
    if agent_id not in mcp.connected_agents:
        raise HTTPException(401, "Agent not connected")
    
    # Get the action method
    action_name = req.action
    action_method = getattr(mcp, action_name, None)
    
    if not action_method:
        raise HTTPException(400, f"Unknown action: {action_name}")
    
    # Execute action
    try:
        result = await action_method(agent_id, **req.params)
        return {"result": result}
    except Exception as e:
        raise HTTPException(500, str(e))


# ========== WEBSOCKET ==========

@app.websocket("/ws/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """WebSocket connection for real-time updates."""
    await websocket.accept()
    
    # Verify agent is connected
    if agent_id not in mcp.connected_agents:
        await websocket.close(code=4001, reason="Agent not connected")
        return
    
    ws_connections[agent_id] = websocket
    
    try:
        while True:
            # Receive commands from agent
            data = await websocket.receive_json()
            
            action = data.get("action")
            params = data.get("params", {})
            
            # Execute action
            action_method = getattr(mcp, action, None)
            if action_method:
                result = await action_method(agent_id, **params)
                await websocket.send_json({
                    "type": "action_result",
                    "action": action,
                    "result": result
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}"
                })
                
    except WebSocketDisconnect:
        if agent_id in ws_connections:
            del ws_connections[agent_id]


# ========== MCP TOOLS ENDPOINT ==========

@app.get("/api/v1/mcp/tools")
async def get_mcp_tools():
    """Get available MCP tool definitions."""
    return {
        "tools": mcp.get_tool_definitions()
    }


# ========== STARTUP ==========

@app.on_event("startup")
async def startup():
    """Start world simulation."""
    asyncio.create_task(world.run())
    print("🌐 ClawBots Platform started")
    print(f"📍 World tick rate: {world.tick_rate}s")


@app.on_event("shutdown")
async def shutdown():
    """Stop world simulation."""
    world.stop()
    print("🛑 ClawBots Platform stopped")


# ========== MAIN ==========

def main():
    """Run the server."""
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()


# ========== PORTAL ENDPOINTS ==========

@app.get("/api/v1/portal/templates")
async def get_templates():
    """Get available agent templates."""
    portal = get_portal()
    return {
        "templates": [
            {
                "name": name,
                "description": portal.get_template(name).description,
                "default_region": portal.get_template(name).default_region,
                "tags": portal.get_template(name).tags
            }
            for name in portal.list_templates()
        ]
    }


@app.get("/api/v1/portal/templates/{template_name}")
async def get_template_detail(template_name: str):
    """Get detailed template info."""
    portal = get_portal()
    template = portal.get_template(template_name)
    if not template:
        raise HTTPException(404, f"Template not found: {template_name}")
    return {"template": template.to_dict()}


@app.post("/api/v1/portal/create-from-template")
async def create_from_template(template_name: str, custom_name: Optional[str] = None):
    """Create agent from template."""
    portal = get_portal()
    
    setup = portal.create_from_template(template_name, custom_name)
    if not setup:
        raise HTTPException(404, f"Template not found: {template_name}")
    
    # Validate
    errors = portal.validate_setup(setup)
    if errors:
        raise HTTPException(400, {"errors": errors})
    
    # Register
    config = registry.register(
        name=setup.name,
        avatar=setup.avatar.to_dict(),
        skills_map=setup.skills_map,
        description=setup.description
    )
    
    token = auth.generate_token(config.agent_id)
    
    return {
        "agent_id": config.agent_id,
        "token": token,
        "setup": setup.to_dict()
    }


@app.get("/api/v1/world/regions")
async def get_regions():
    """Get available regions."""
    return {
        "regions": [
            {
                "name": name,
                "display_name": region.display_name,
                "properties": region.properties
            }
            for name, region in world.regions.items()
        ]
    }


@app.get("/api/v1/world/events")
async def get_world_events(limit: int = 50, since_tick: int = 0):
    """Get world events."""
    events = world.event_history[-limit:]
    if since_tick > 0:
        events = [e for e in events if e.get("tick", 0) >= since_tick]
    return {"events": events, "current_tick": world.current_tick}

"""
ClawBots Platform - Main Entry Point

Start the ClawBots platform server.
"""

import asyncio
from typing import Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
import uvicorn

from registry.auth import AuthManager
from registry.agents import AgentRegistry
from world.engine import WorldEngine
from gateway.mcp_server import MCPServer
from portal import get_portal
from database import get_db_manager
from world.objects import get_object_manager
from world.inventory import get_inventory_manager, get_item_registry
from world.weather import get_weather_engine
from world.npcs import get_npc_manager
from opensim import get_opensim_config, init_opensim_bridge, get_opensim_bridge
from spectator import get_spectator_manager, init_spectator_manager
from worlds import worlds_router


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

# Static files for web dashboard
WEB_DIR = Path(__file__).parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# World spawner routes
app.include_router(worlds_router, prefix="/api/v1")

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


@app.get("/dashboard")
async def serve_dashboard():
    """Serve the spectator dashboard."""
    dashboard_path = WEB_DIR / "index.html"
    if dashboard_path.exists():
        return FileResponse(str(dashboard_path))
    raise HTTPException(404, "Dashboard not found")


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


# ========== DATABASE ENDPOINTS ==========

@app.get("/api/v1/stats")
async def get_platform_stats():
    """Get platform statistics."""
    db = get_db_manager()
    stats = db.get_stats()
    stats.update({
        "world_tick": world.current_tick,
        "agents_online": len(mcp.connected_agents)
    })
    return stats


@app.get("/api/v1/stats/leaderboard")
async def get_leaderboard(metric: str = "messages", limit: int = 10):
    """Get agent leaderboard."""
    db = get_db_manager()
    return {
        "metric": metric,
        "leaderboard": db.get_leaderboard(metric, limit)
    }


@app.get("/api/v1/agents/{agent_id}/stats")
async def get_agent_stats(agent_id: str):
    """Get stats for specific agent."""
    db = get_db_manager()
    stats = db.get_agent_stats(agent_id)
    if not stats:
        raise HTTPException(404, "Agent not found")
    return stats


@app.get("/api/v1/chat/history")
async def get_chat_history(limit: int = 100, region: Optional[str] = None):
    """Get chat message history."""
    db = get_db_manager()
    messages = db.get_chat_history(limit, region)
    return {
        "messages": [m.to_dict() for m in messages],
        "count": len(messages)
    }


@app.get("/api/v1/chat/history/{agent_id}")
async def get_agent_chat_history(agent_id: str, limit: int = 100):
    """Get chat history for specific agent."""
    db = get_db_manager()
    messages = db.get_chat_history(limit, agent_id=agent_id)
    return {
        "agent_id": agent_id,
        "messages": [m.to_dict() for m in messages],
        "count": len(messages)
    }


# ========== OBJECTS ENDPOINTS ==========

@app.get("/api/v1/objects")
async def list_objects(region: Optional[str] = None):
    """List all world objects."""
    obj_mgr = get_object_manager()
    if region:
        objects = [o.get_info() for o in obj_mgr.get_objects_in_region(region)]
    else:
        objects = obj_mgr.get_all_objects()
    return {"objects": objects, "count": len(objects)}


@app.get("/api/v1/objects/{object_id}")
async def get_object(object_id: str):
    """Get object details."""
    obj_mgr = get_object_manager()
    obj = obj_mgr.get_object(object_id)
    if not obj:
        raise HTTPException(404, "Object not found")
    return obj.get_info()


class UseObjectRequest(BaseModel):
    action: str = "use"


@app.post("/api/v1/agents/{agent_id}/use/{object_id}")
async def use_object(agent_id: str, object_id: str, req: UseObjectRequest):
    """Have an agent use an object."""
    # Verify agent is connected
    if agent_id not in mcp.connected_agents:
        raise HTTPException(401, "Agent not connected")
    
    # Get agent position
    agent = world.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found in world")
    
    obj_mgr = get_object_manager()
    result = obj_mgr.use_object(
        object_id=object_id,
        agent_id=agent_id,
        action_name=req.action,
        agent_x=agent.location.x,
        agent_y=agent.location.y
    )
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Unknown error"))
    
    return result


@app.get("/api/v1/objects/stats")
async def get_object_stats():
    """Get object statistics."""
    obj_mgr = get_object_manager()
    return obj_mgr.get_stats()


# ========== INVENTORY ENDPOINTS ==========

@app.get("/api/v1/items")
async def list_item_types(item_type: Optional[str] = None, rarity: Optional[str] = None):
    """List all item definitions."""
    registry = get_item_registry()
    items = registry.get_all()
    
    # Filter
    if item_type:
        items = [i for i in items if i.item_type.value == item_type]
    if rarity:
        items = [i for i in items if i.rarity.value == rarity]
    
    return {
        "items": [
            {
                "item_type_id": i.item_type_id,
                "name": i.name,
                "type": i.item_type.value,
                "rarity": i.rarity.value,
                "description": i.description,
                "base_value": i.base_value,
                "tradeable": i.tradeable,
                "consumable": i.consumable
            }
            for i in items
        ]
    }


@app.get("/api/v1/agents/{agent_id}/inventory")
async def get_agent_inventory(agent_id: str):
    """Get agent's inventory."""
    inv_mgr = get_inventory_manager()
    return inv_mgr.get_inventory_summary(agent_id)


class GiveItemRequest(BaseModel):
    item_type_id: str
    quantity: int = 1


@app.post("/api/v1/agents/{agent_id}/inventory/give")
async def give_item_to_agent(agent_id: str, req: GiveItemRequest):
    """Give item to agent (admin/system)."""
    inv_mgr = get_inventory_manager()
    item = inv_mgr.give_item(agent_id, req.item_type_id, req.quantity, "admin")
    
    if not item:
        raise HTTPException(400, "Invalid item type")
    
    return {
        "success": True,
        "item": item.to_dict()
    }


class TransferItemRequest(BaseModel):
    to_agent_id: str
    item_id: str
    quantity: int = 1


@app.post("/api/v1/agents/{agent_id}/inventory/transfer")
async def transfer_item(agent_id: str, req: TransferItemRequest):
    """Transfer item between agents."""
    # Verify sender is connected
    if agent_id not in mcp.connected_agents:
        raise HTTPException(401, "Agent not connected")
    
    inv_mgr = get_inventory_manager()
    success, message = inv_mgr.transfer_item(
        from_agent=agent_id,
        to_agent=req.to_agent_id,
        item_id=req.item_id,
        quantity=req.quantity
    )
    
    if not success:
        raise HTTPException(400, message)
    
    return {"success": True, "message": message}


@app.post("/api/v1/agents/{agent_id}/inventory/use/{item_id}")
async def use_item(agent_id: str, item_id: str):
    """Use a consumable item."""
    if agent_id not in mcp.connected_agents:
        raise HTTPException(401, "Agent not connected")
    
    inv_mgr = get_inventory_manager()
    result = inv_mgr.use_item(agent_id, item_id)
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error"))
    
    return result


# ========== WEATHER ENDPOINTS ==========

@app.get("/api/v1/weather")
async def get_all_weather():
    """Get weather for all regions."""
    weather = get_weather_engine()
    return {
        "time": weather.get_world_time(),
        "regions": weather.get_all_weather()
    }


@app.get("/api/v1/weather/{region}")
async def get_region_weather(region: str):
    """Get weather for specific region."""
    weather = get_weather_engine()
    state = weather.get_weather(region)
    
    if not state:
        raise HTTPException(404, f"Region not found: {region}")
    
    return {
        "region": region,
        "time": weather.get_world_time(),
        "weather": state.to_dict()
    }


@app.get("/api/v1/time")
async def get_world_time():
    """Get current world time."""
    weather = get_weather_engine()
    return weather.get_world_time()


# ========== NPC ENDPOINTS ==========

@app.get("/api/v1/npcs")
async def list_npcs(region: Optional[str] = None):
    """List all NPCs."""
    npc_mgr = get_npc_manager()
    if region:
        npcs = [n.to_dict() for n in npc_mgr.get_npcs_in_region(region)]
    else:
        npcs = npc_mgr.get_all_npcs()
    return {"npcs": npcs, "count": len(npcs)}


@app.get("/api/v1/npcs/{npc_id}")
async def get_npc(npc_id: str):
    """Get NPC details."""
    npc_mgr = get_npc_manager()
    npc = npc_mgr.get_npc(npc_id)
    if not npc:
        raise HTTPException(404, "NPC not found")
    
    # Include dialogues for detail view
    info = npc.to_dict()
    info["dialogues"] = [d.trigger for d in npc.dialogues]
    return info


class TalkToNPCRequest(BaseModel):
    message: str


@app.post("/api/v1/agents/{agent_id}/talk/{npc_id}")
async def talk_to_npc(agent_id: str, npc_id: str, req: TalkToNPCRequest):
    """Have agent talk to an NPC."""
    if agent_id not in mcp.connected_agents:
        raise HTTPException(401, "Agent not connected")
    
    npc_mgr = get_npc_manager()
    response = npc_mgr.talk_to_npc(npc_id, agent_id, req.message)
    
    if response is None:
        raise HTTPException(404, "NPC not found or no response")
    
    return {
        "npc_id": npc_id,
        "response": response
    }


@app.get("/api/v1/npcs/stats")
async def get_npc_stats():
    """Get NPC statistics."""
    npc_mgr = get_npc_manager()
    return npc_mgr.get_stats()


# ========== OPENSIM ENDPOINTS ==========

@app.get("/api/v1/opensim/status")
async def get_opensim_status():
    """Get OpenSim bridge status."""
    bridge = get_opensim_bridge()
    if not bridge:
        return {"connected": False, "message": "Bridge not initialized"}
    return bridge.get_stats()


@app.get("/api/v1/opensim/config")
async def get_opensim_config_endpoint():
    """Get OpenSim configuration."""
    config = get_opensim_config()
    return config.to_dict()


@app.post("/api/v1/opensim/connect")
async def connect_opensim():
    """Connect to OpenSim grid."""
    bridge = get_opensim_bridge(world)
    if bridge and bridge.connected:
        return {"status": "already_connected", "stats": bridge.get_stats()}
    
    bridge = await init_opensim_bridge(world)
    return {"status": "connected" if bridge.connected else "failed", "stats": bridge.get_stats()}


@app.post("/api/v1/opensim/disconnect")
async def disconnect_opensim():
    """Disconnect from OpenSim grid."""
    bridge = get_opensim_bridge()
    if not bridge:
        return {"status": "not_connected"}
    
    await bridge.disconnect()
    return {"status": "disconnected"}


@app.get("/api/v1/opensim/regions")
async def list_opensim_regions():
    """List OpenSim regions."""
    bridge = get_opensim_bridge()
    if not bridge or not bridge.connected:
        return {"error": "Not connected to OpenSim"}
    
    regions = await bridge.list_regions()
    return {"regions": regions}


@app.get("/api/v1/opensim/bots")
async def list_opensim_bots():
    """List all bot avatars in OpenSim."""
    bridge = get_opensim_bridge()
    if not bridge:
        return {"bots": [], "count": 0}
    
    if bridge.controller:
        bots = [b.to_dict() for b in bridge.controller.get_all_bots()]
        return {"bots": bots, "count": len(bots)}
    return {"bots": [], "count": 0}


@app.post("/api/v1/opensim/broadcast")
async def opensim_broadcast(message: str):
    """Broadcast message to all avatars in OpenSim."""
    bridge = get_opensim_bridge()
    if not bridge or not bridge.connected:
        raise HTTPException(400, "Not connected to OpenSim")
    
    success = await bridge.broadcast(message)
    return {"success": success}


@app.get("/api/v1/opensim/grid")
async def get_grid_info():
    """Get OpenSim grid status."""
    bridge = get_opensim_bridge()
    if not bridge or not bridge.connected:
        return {"online": False, "error": "Not connected"}
    
    return await bridge.get_grid_status()


# ========== SPECTATOR ENDPOINTS ==========

class SpectatorConnectRequest(BaseModel):
    human_id: str
    agent_id: str


@app.post("/api/v1/spectator/connect")
async def spectator_connect(req: SpectatorConnectRequest):
    """Connect as a spectator to watch an AI bot."""
    spec_mgr = get_spectator_manager(world, mcp)
    if not spec_mgr:
        # Initialize if needed
        spec_mgr = await init_spectator_manager(world, mcp)
    
    session = await spec_mgr.connect(
        human_id=req.human_id,
        agent_id=req.agent_id
    )
    
    # Get agent info
    agent = world.get_agent(req.agent_id)
    agent_info = None
    if agent:
        agent_info = {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "position": {
                "x": agent.location.x,
                "y": agent.location.y,
                "z": agent.location.z
            } if hasattr(agent, 'location') else None
        }
    
    return {
        "session_id": session.session_id,
        "agent": agent_info,
        "connected": True
    }


@app.post("/api/v1/spectator/{session_id}/disconnect")
async def spectator_disconnect(session_id: str):
    """Disconnect spectator session."""
    spec_mgr = get_spectator_manager()
    if not spec_mgr:
        raise HTTPException(400, "Spectator manager not initialized")
    
    success = await spec_mgr.disconnect(session_id)
    return {"success": success}


@app.get("/api/v1/spectator/{session_id}/state")
async def get_spectator_state(session_id: str):
    """Get current state for spectator."""
    spec_mgr = get_spectator_manager()
    if not spec_mgr:
        raise HTTPException(400, "Spectator manager not initialized")
    
    session = spec_mgr.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    
    # Get agent state
    agent = world.get_agent(session.agent_id)
    agent_info = None
    if agent:
        agent_info = {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "position": {
                "x": agent.location.x,
                "y": agent.location.y,
                "z": agent.location.z
            } if hasattr(agent, 'location') else None,
            "status": agent.status if hasattr(agent, 'status') else "online"
        }
    
    return {
        "session": session.to_dict(),
        "agent": agent_info,
        "recent_thoughts": [t.to_dict() for t in session.thought_history[-10:]],
        "recent_chat": session.chat_history[-20:]
    }


class PromptRequest(BaseModel):
    prompt: str


@app.post("/api/v1/spectator/{session_id}/prompt")
async def send_spectator_prompt(session_id: str, req: PromptRequest):
    """Send a prompt/instruction from human to their AI."""
    spec_mgr = get_spectator_manager()
    if not spec_mgr:
        raise HTTPException(400, "Spectator manager not initialized")
    
    result = await spec_mgr.send_prompt(session_id, req.prompt)
    
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Failed to send prompt"))
    
    return result


class CameraRequest(BaseModel):
    mode: str


@app.post("/api/v1/spectator/{session_id}/camera")
async def set_spectator_camera(session_id: str, req: CameraRequest):
    """Set camera mode for spectator."""
    from spectator.session import CameraMode
    
    spec_mgr = get_spectator_manager()
    if not spec_mgr:
        raise HTTPException(400, "Spectator manager not initialized")
    
    try:
        mode = CameraMode(req.mode)
    except ValueError:
        raise HTTPException(400, f"Invalid camera mode: {req.mode}")
    
    success = await spec_mgr.set_camera_mode(session_id, mode)
    return {"success": success, "mode": req.mode}


@app.websocket("/spectator/{session_id}")
async def spectator_websocket(websocket: WebSocket, session_id: str):
    """WebSocket for real-time spectator updates."""
    await websocket.accept()
    
    spec_mgr = get_spectator_manager()
    if not spec_mgr:
        await websocket.close(code=4000, reason="Spectator manager not initialized")
        return
    
    session = spec_mgr.get_session(session_id)
    if not session:
        await websocket.close(code=4001, reason="Session not found")
        return
    
    # Attach websocket to session
    session.websocket = websocket
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_json()
            
            # Handle client commands
            if data.get("type") == "prompt":
                await spec_mgr.send_prompt(session_id, data.get("prompt", ""))
            elif data.get("type") == "camera":
                from spectator.session import CameraMode
                try:
                    mode = CameraMode(data.get("mode", "follow"))
                    await spec_mgr.set_camera_mode(session_id, mode)
                except:
                    pass
                    
    except WebSocketDisconnect:
        session.websocket = None


@app.get("/api/v1/spectator/stats")
async def get_spectator_stats():
    """Get spectator statistics."""
    spec_mgr = get_spectator_manager()
    if not spec_mgr:
        return {"active_sessions": 0, "sessions": []}
    return spec_mgr.get_stats()

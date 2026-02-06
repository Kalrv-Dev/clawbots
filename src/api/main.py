"""ClawBots FastAPI Server"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import yaml
import os

app = FastAPI(title="ClawBots", version="0.1.0")

# In-memory agent store (replace with DB in production)
agents: Dict[str, "Agent"] = {}

class AgentCreate(BaseModel):
    soul_path: str

class EventInput(BaseModel):
    type: str
    content: str
    importance: float = 0.5
    participants: List[str] = []
    location: Optional[str] = None

class ActionResponse(BaseModel):
    agent_id: str
    persona: str
    type: str
    drives: List[str]

@app.get("/")
async def root():
    return {"service": "ClawBots", "version": "0.1.0", "agents": len(agents)}

@app.get("/agents")
async def list_agents():
    return {
        "agents": [
            {"id": a.id, "name": a.name, "persona": a.personas.current}
            for a in agents.values()
        ]
    }

@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(404, "Agent not found")
    agent = agents[agent_id]
    return {
        "id": agent.id,
        "name": agent.name,
        "persona": agent.personas.current,
        "state": {
            "energy": agent.state.energy,
            "boredom": agent.state.boredom,
            "mood": agent.state.mood
        },
        "drives": agent.drives.state.pressures,
        "location": agent.location
    }

@app.post("/agents/{agent_id}/perceive")
async def perceive_event(agent_id: str, event: EventInput):
    if agent_id not in agents:
        raise HTTPException(404, "Agent not found")
    
    agent = agents[agent_id]
    agent.perceive(event.dict())
    return {"status": "perceived"}

@app.post("/agents/{agent_id}/decide")
async def decide_action(agent_id: str, env: Dict = {}):
    if agent_id not in agents:
        raise HTTPException(404, "Agent not found")
    
    agent = agents[agent_id]
    action = agent.decide_action(env)
    return action

@app.post("/agents/{agent_id}/tick")
async def tick_agent(agent_id: str, minutes: float = 1.0):
    if agent_id not in agents:
        raise HTTPException(404, "Agent not found")
    
    agent = agents[agent_id]
    agent.tick(minutes)
    return {"status": "ticked", "minutes": minutes}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

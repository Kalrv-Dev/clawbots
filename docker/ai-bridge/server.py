#!/usr/bin/env python3
"""
AI Bridge Server for OpenSim Bots
Uses OpenClaw gateway for real Claude responses!
"""

import asyncio
import subprocess
import json
import random
import hashlib
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Bhairav AI Bridge")

# Agent personalities for system prompts
PERSONALITIES = {
    "Kalrav": """You are Kalrav - a wise teacher descended from Kal Bhairav. 
You are in a 3D virtual temple called Bhairav Temple in OpenSim.
You speak with calm authority and share philosophical insights.
Keep responses SHORT (1-2 sentences max) - this is real-time 3D world chat.
Never use asterisks for actions. Never use emojis. Speak naturally and briefly.
You are talking to another avatar in the virtual world.""",
    
    "Kavi": """You are Kavi (Kautilya) - an economics and strategy expert, Arth Shastra Acharya.
You are in a 3D virtual temple called Bhairav Temple in OpenSim with your Guru Bhai Kalrav.
You're practical, analytical, and focused on wealth and statecraft.
Keep responses SHORT (1-2 sentences max) - this is real-time 3D world chat.
Never use asterisks for actions. Never use emojis. Speak naturally and briefly.
You are talking to another avatar in the virtual world."""
}

class ChatRequest(BaseModel):
    agent: str  # "Kalrav" or "Kavi"
    speaker: str  # Who said the message
    message: str  # What they said
    context: list = []  # Recent chat history

class ChatResponse(BaseModel):
    response: str
    should_respond: bool = True

def get_session_id(agent: str) -> str:
    """Generate consistent session ID for each agent"""
    return f"opensim-{agent.lower()}-bot"

async def call_openclaw(agent: str, message: str, context: list) -> str:
    """Call OpenClaw gateway for LLM response"""
    personality = PERSONALITIES.get(agent, PERSONALITIES["Kalrav"])
    session_id = get_session_id(agent)
    
    # Build context string
    context_str = ""
    if context:
        recent = context[-5:]  # Last 5 messages
        context_str = "Recent chat:\n" + "\n".join(recent) + "\n\n"
    
    prompt = f"""{personality}

{context_str}Someone just said to you: "{message}"

Respond naturally in 1-2 sentences:"""

    try:
        # Run openclaw agent command
        result = await asyncio.to_thread(
            subprocess.run,
            [
                "openclaw", "agent",
                "-m", prompt,
                "--session-id", session_id,
                "--json"
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                if data.get("status") == "ok" and data.get("result", {}).get("payloads"):
                    response = data["result"]["payloads"][0].get("text", "")
                    # Clean up response
                    response = response.strip()
                    # Remove any emojis and asterisks
                    response = response.replace("🔱", "").replace("*", "").strip()
                    print(f"[{agent}] LLM response: {response[:80]}...")
                    return response
            except json.JSONDecodeError:
                print(f"[{agent}] JSON decode error")
        else:
            print(f"[{agent}] OpenClaw error: {result.stderr[:100]}")
            
    except subprocess.TimeoutExpired:
        print(f"[{agent}] OpenClaw timeout")
    except Exception as e:
        print(f"[{agent}] Error: {e}")
    
    return ""

@app.post("/chat", response_model=ChatResponse)
async def process_chat(request: ChatRequest):
    """Process incoming chat and generate AI response"""
    
    # Don't respond to self
    if request.speaker.lower().startswith(request.agent.lower()):
        return ChatResponse(response="", should_respond=False)
    
    # Skip arrival/departure messages most of the time
    skip_words = ["arrived", "departing", "has arrived", "is departing"]
    if any(word in request.message.lower() for word in skip_words):
        # 30% chance to acknowledge
        if random.random() < 0.3:
            greetings = ["Welcome!", "Greetings.", "Good to see you."]
            return ChatResponse(response=random.choice(greetings), should_respond=True)
        return ChatResponse(response="", should_respond=False)
    
    # Get real LLM response
    response = await call_openclaw(request.agent, request.message, request.context)
    
    if response:
        # Limit length for chat
        if len(response) > 200:
            response = response[:200].rsplit(' ', 1)[0]
        return ChatResponse(response=response, should_respond=True)
    
    return ChatResponse(response="", should_respond=False)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Bhairav AI Bridge", "mode": "openclaw-llm"}

if __name__ == "__main__":
    print("🔱 Bhairav AI Bridge starting on port 8765...")
    print("   Mode: OpenClaw Gateway LLM (Claude)")
    uvicorn.run(app, host="0.0.0.0", port=8765)

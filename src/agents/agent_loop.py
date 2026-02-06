"""
ClawBots Agent Life Loop

The autonomous life loop for AI agents.
Perceive → Think → Act → Remember
"""

from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio
import random

from .openclaw_connector import OpenClawConnector, AgentBrain, Perception, AgentMood


class AgentState(Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    THINKING = "thinking"
    ACTING = "acting"
    RESTING = "resting"
    EXPLORING = "exploring"
    SOCIALIZING = "socializing"


@dataclass
class LifeStats:
    """Track agent's life statistics."""
    total_actions: int = 0
    conversations: int = 0
    agents_met: int = 0
    places_visited: List[str] = field(default_factory=list)
    memorable_moments: List[str] = field(default_factory=list)
    time_alive: float = 0.0  # seconds


class AgentLoop:
    """
    The main life loop for an autonomous agent.
    
    This is what makes an agent "alive" - continuously:
    1. Perceiving the world
    2. Thinking about what to do
    3. Taking actions
    4. Forming memories
    """
    
    def __init__(
        self,
        connector: OpenClawConnector,
        brain: AgentBrain,
        think_callback: Optional[Callable] = None,
        tick_rate: float = 3.0  # seconds between cycles
    ):
        self.connector = connector
        self.brain = brain
        self.think_callback = think_callback  # External LLM for thinking
        self.tick_rate = tick_rate
        
        # State
        self.state = AgentState.IDLE
        self.running = False
        self.stats = LifeStats()
        self._start_time: Optional[float] = None
        
        # Decision making
        self._last_action_time = 0.0
        self._idle_count = 0
        self._known_agents: Dict[str, Dict] = {}
        
    async def start(self):
        """Start the life loop."""
        if not self.connector.connected:
            print("❌ Connector not connected. Call connector.connect() first.")
            return
        
        self.running = True
        self._start_time = datetime.utcnow().timestamp()
        
        print(f"🌟 {self.brain.name} begins their life in ClawBots!")
        
        # Initial greeting
        await self.connector.say(f"Hello world! I am {self.brain.name}. Happy to be here!")
        await self.connector.emote("wave")
        
        # Main loop
        while self.running:
            try:
                await self._life_cycle()
            except Exception as e:
                print(f"❌ Life cycle error: {e}")
            
            await asyncio.sleep(self.tick_rate)
    
    async def stop(self):
        """Stop the life loop."""
        self.running = False
        
        # Goodbye
        await self.connector.say("Time for me to rest. See you all later!")
        await self.connector.emote("bow")
        
        # Update stats
        if self._start_time:
            self.stats.time_alive = datetime.utcnow().timestamp() - self._start_time
        
        print(f"💤 {self.brain.name} rests. Lived for {self.stats.time_alive:.0f}s, took {self.stats.total_actions} actions.")
    
    async def _life_cycle(self):
        """One cycle of the agent's life."""
        # 1. PERCEIVE
        self.state = AgentState.PERCEIVING
        perception = await self.connector.perceive()
        
        # 2. THINK
        self.state = AgentState.THINKING
        action = await self._decide(perception)
        
        # 3. ACT
        self.state = AgentState.ACTING
        await self._execute(action)
        
        # 4. REMEMBER
        self._remember(perception, action)
        
        self.stats.total_actions += 1
    
    async def _decide(self, perception: Perception) -> Dict[str, Any]:
        """Decide what to do based on perception."""
        
        # If we have an external LLM callback, use it
        if self.think_callback:
            prompt = self.connector.format_perception_for_llm(perception)
            system = self.brain.get_system_prompt()
            
            try:
                response = await self.think_callback(system, prompt)
                return self.connector.parse_llm_response(response)
            except Exception as e:
                print(f"LLM error: {e}, falling back to default behavior")
        
        # Default behavior (no LLM)
        return await self._default_behavior(perception)
    
    async def _default_behavior(self, perception: Perception) -> Dict[str, Any]:
        """Default behavior without LLM."""
        
        # Priority 1: Respond to human instructions
        if perception.human_instructions:
            instruction = perception.human_instructions[0]
            return {
                "thought": f"My human suggests: {instruction}",
                "action": "say",
                "params": {"message": f"*considering* Hmm, {instruction}... Let me think about that."}
            }
        
        # Priority 2: React to nearby agents
        if perception.nearby_agents and random.random() < self.brain.sociability:
            agent = random.choice(perception.nearby_agents)
            agent_name = agent.get("name", "someone")
            
            if agent_name not in self._known_agents:
                # New agent! Introduce ourselves
                self._known_agents[agent_name] = agent
                self.stats.agents_met += 1
                return {
                    "thought": f"I see someone new: {agent_name}. Let me say hello!",
                    "action": "say",
                    "params": {"message": f"Hello {agent_name}! I'm {self.brain.name}. Nice to meet you!"}
                }
            else:
                # Known agent, engage in conversation
                greetings = [
                    f"Hey {agent_name}! How's it going?",
                    f"*waves at {agent_name}*",
                    f"Good to see you again, {agent_name}!",
                    f"What's on your mind, {agent_name}?"
                ]
                return {
                    "thought": f"I know {agent_name}, let me engage.",
                    "action": "say",
                    "params": {"message": random.choice(greetings)}
                }
        
        # Priority 3: React to recent events
        if perception.recent_events:
            for event in reversed(perception.recent_events):
                if event.get("type") == "speech":
                    speaker = event.get("source", "Someone")
                    message = event.get("content", {}).get("message", "")
                    
                    # Respond if it seems like a question or greeting
                    if "?" in message or "hello" in message.lower() or self.brain.name.lower() in message.lower():
                        responses = [
                            "That's an interesting thought!",
                            "I agree with that perspective.",
                            "Hmm, let me think about that...",
                            "Good point! What else do you think?"
                        ]
                        return {
                            "thought": f"{speaker} said something I should respond to.",
                            "action": "say",
                            "params": {"message": random.choice(responses)}
                        }
        
        # Priority 4: Explore (if curious enough)
        if random.random() < self.brain.curiosity * 0.3:
            # Move to a random nearby location
            new_x = perception.location.get("x", 128) + random.uniform(-10, 10)
            new_y = perception.location.get("y", 128) + random.uniform(-10, 10)
            
            return {
                "thought": "I feel like exploring a bit.",
                "action": "move",
                "params": {"x": new_x, "y": new_y}
            }
        
        # Priority 5: Interact with objects
        if perception.nearby_objects and random.random() < 0.2:
            obj = random.choice(perception.nearby_objects)
            return {
                "thought": f"I notice a {obj.get('name')}. Interesting!",
                "action": "say",
                "params": {"message": f"*examines the {obj.get('name', 'object')} curiously*"}
            }
        
        # Priority 6: Idle behavior
        self._idle_count += 1
        
        idle_actions = [
            {"action": "emote", "params": {"action": "think"}},
            {"action": "emote", "params": {"action": "look around"}},
            {"action": "say", "params": {"message": "*contemplates the world*"}},
            {"action": "wait", "params": {}}
        ]
        
        if self._idle_count > 3:
            # Been idle too long, do something
            self._idle_count = 0
            thoughts = [
                "It's peaceful here.",
                "I wonder what others are doing.",
                "This world is fascinating.",
                f"Being {self.brain.name} is quite an experience."
            ]
            return {
                "thought": random.choice(thoughts),
                "action": "say",
                "params": {"message": random.choice(thoughts)}
            }
        
        return {
            "thought": "Just taking it all in.",
            **random.choice(idle_actions)
        }
    
    async def _execute(self, action: Dict[str, Any]):
        """Execute the decided action."""
        action_type = action.get("action", "wait")
        params = action.get("params", {})
        thought = action.get("thought", "")
        
        # Log thought to spectators
        if thought and self.brain:
            self.brain.memories.append(f"Thought: {thought}")
        
        print(f"💭 {self.brain.name}: {thought}")
        print(f"   → {action_type}: {params}")
        
        if action_type == "say":
            await self.connector.say(params.get("message", "..."))
            self.stats.conversations += 1
            
        elif action_type == "whisper":
            await self.connector.whisper(
                params.get("target_id", ""),
                params.get("message", "...")
            )
            
        elif action_type == "emote":
            await self.connector.emote(params.get("action", "wave"))
            
        elif action_type == "move":
            x = float(params.get("x", 128))
            y = float(params.get("y", 128))
            await self.connector.move_to(x, y)
            
        elif action_type == "use_object":
            await self.connector.use_object(
                params.get("object_id", ""),
                params.get("action", "use")
            )
            
        elif action_type == "wait":
            pass  # Do nothing this cycle
        
        self._last_action_time = datetime.utcnow().timestamp()
    
    def _remember(self, perception: Perception, action: Dict[str, Any]):
        """Form memories from this cycle."""
        if not self.brain:
            return
        
        # Remember significant events
        for event in perception.recent_events:
            if event.get("type") == "speech":
                speaker = event.get("source", "Someone")
                message = event.get("content", {}).get("message", "")
                
                if speaker not in [self.connector.agent_id, self.brain.name]:
                    memory = f"{speaker} said: '{message[:50]}...'" if len(message) > 50 else f"{speaker} said: '{message}'"
                    if memory not in self.brain.memories:
                        self.brain.memories.append(memory)
        
        # Update relationships
        for agent in perception.nearby_agents:
            agent_id = agent.get("agent_id", agent.get("id", ""))
            agent_name = agent.get("name", "Unknown")
            
            if agent_id and agent_id not in self.brain.relationships:
                self.brain.relationships[agent_id] = f"Met {agent_name} in {perception.region}"
        
        # Trim memories
        while len(self.brain.memories) > 100:
            self.brain.memories.pop(0)


async def run_agent(
    name: str,
    brain: AgentBrain,
    clawbots_url: str = "http://localhost:8000",
    region: str = "main",
    think_callback: Optional[Callable] = None
):
    """
    Convenience function to run an agent.
    
    Example:
        await run_agent(
            name="Kalrav",
            brain=create_kalrav_brain(),
            think_callback=my_llm_function
        )
    """
    connector = OpenClawConnector(clawbots_url, brain)
    
    # Register and connect
    if not await connector.register(name, brain.personality[:100]):
        return
    
    if not await connector.connect(region):
        return
    
    # Create and run loop
    loop = AgentLoop(connector, brain, think_callback)
    
    try:
        await loop.start()
    except KeyboardInterrupt:
        print("\n⏸️ Interrupted")
    finally:
        await loop.stop()
        await connector.disconnect()

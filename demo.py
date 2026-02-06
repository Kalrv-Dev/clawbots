#!/usr/bin/env python3
"""ClawBots Demo - Watch agents come alive!

Run: python demo.py
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from core.soul import Soul
from core.world import World, Location
from core.personas.models import Persona, Archetype, Expression
from engines.llm import LLMConfig

# Demo personas
PERSONAS = {
    "temple_guide": Persona(
        id="temple_guide",
        display_name="Temple Guide",
        archetype=Archetype(role="guide", tone="calm", social_position="respected"),
        expression=Expression(verbosity="medium", humor="low", formality="high"),
        preferred_actions=["greeting", "teaching", "explaining"],
        avoids=["mockery", "chaos"]
    ),
    "trickster": Persona(
        id="trickster", 
        display_name="Playful Trickster",
        archetype=Archetype(role="entertainer", tone="playful", social_position="neutral"),
        expression=Expression(verbosity="high", humor="high", formality="low"),
        preferred_actions=["joking", "teasing", "storytelling"],
        avoids=["solemnity", "lectures"]
    ),
    "observer": Persona(
        id="observer",
        display_name="Silent Observer",
        archetype=Archetype(role="watcher", tone="quiet", social_position="mysterious"),
        expression=Expression(verbosity="very_low", humor="low", formality="medium"),
        preferred_actions=["watching", "reflecting", "brief_insight"],
        avoids=["long_speeches", "small_talk"]
    )
}

async def main():
    print("🤖 ClawBots Demo Starting...")
    print("=" * 50)
    
    # Create world (without LLM for demo - would need API key)
    world = World(LLMConfig(provider="anthropic"))
    
    # Add locations
    world.add_location(Location(
        id="temple",
        name="Ancient Temple",
        type="temple",
        capacity=20
    ))
    world.add_location(Location(
        id="plaza",
        name="Central Plaza", 
        type="plaza",
        capacity=100
    ))
    
    # Create example souls (generic - not real identities)
    guide_soul = Soul(
        name="Sage",
        identity="sage_001",
        personality="calm_teacher",
        drives="default",
        default_persona="temple_guide",
        allowed_personas=["temple_guide", "observer"],
        values=["wisdom", "patience", "truth"],
        relationships={}
    )
    
    seeker_soul = Soul(
        name="Nova",
        identity="nova_001",
        personality="curious_explorer",
        drives="default",
        default_persona="trickster",
        allowed_personas=["trickster", "observer"],
        values=["curiosity", "adventure", "creativity"],
        relationships={}
    )
    
    # Spawn agents
    sage = world.spawn_agent(guide_soul, PERSONAS, "temple")
    nova = world.spawn_agent(seeker_soul, PERSONAS, "temple")
    
    print(f"\n✅ Spawned: {sage.name} at {sage.location}")
    print(f"✅ Spawned: {nova.name} at {nova.location}")
    
    # Show initial state
    print(f"\n📊 World State:")
    state = world.get_state()
    for aid, info in state["agents"].items():
        print(f"  - {info['name']}: {info['persona']} @ {info['location']} (energy: {info['energy']:.0%})")
    
    # Simulate a few ticks
    print("\n⏱️ Running simulation...")
    for i in range(3):
        print(f"\n--- Tick {i+1} ---")
        
        # Manual drive increase for demo
        sage.drives.state.pressures['social'] = 0.7 + (i * 0.1)
        sage.drives.state.pressures['teaching'] = 0.6
        
        await world.tick(1.0)
        
        # Show drive states
        print(f"  {sage.name} drives: social={sage.drives.state.pressures.get('social', 0):.0%}")
        print(f"  {nova.name} drives: social={nova.drives.state.pressures.get('social', 0):.0%}")
    
    # Show events
    print(f"\n📜 Events ({len(world.event_log)}):")
    for event in world.event_log[-5:]:
        print(f"  [{event['type']}] {event.get('agent_name', '')}")
    
    print("\n🤖 Demo complete! Add ANTHROPIC_API_KEY to enable LLM responses.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())

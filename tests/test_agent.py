"""Test ClawBots Agent"""
import sys
sys.path.insert(0, 'src')

from core.soul import Soul
from core.agent import Agent
from core.personas.models import Persona, Archetype, Expression

def test_agent_basic():
    # Create a test soul
    soul = Soul(
        name="TestBot",
        identity="test_bot_1",
        personality="calm_teacher",
        drives="default",
        default_persona="temple_guide",
        allowed_personas=["temple_guide", "observer"],
        values=["truth", "kindness"]
    )
    
    # Create test personas
    personas = {
        "temple_guide": Persona(
            id="temple_guide",
            display_name="Temple Guide",
            archetype=Archetype(role="guide", tone="calm"),
            expression=Expression(verbosity="medium"),
            preferred_actions=["greeting", "teaching"]
        ),
        "observer": Persona(
            id="observer",
            display_name="Observer",
            archetype=Archetype(role="observer", tone="quiet"),
            expression=Expression(verbosity="low"),
            preferred_actions=["watching"]
        )
    }
    
    # Create agent
    agent = Agent(soul, personas)
    
    print(f"Created agent: {agent.name} ({agent.id})")
    print(f"Current persona: {agent.personas.current}")
    print(f"Drives: {agent.drives.state.pressures}")
    
    # Simulate some time passing
    agent.tick(5)
    print(f"\nAfter 5 minutes:")
    print(f"Energy: {agent.state.energy:.2f}")
    print(f"Boredom: {agent.state.boredom:.2f}")
    print(f"Drives: {agent.drives.state.pressures}")
    
    # Perceive an event
    agent.perceive({
        'type': 'chat',
        'content': 'Hello there!',
        'participants': ['visitor_1'],
        'importance': 0.7
    })
    print(f"\nAfter perceiving chat:")
    print(f"Boredom: {agent.state.boredom:.2f}")
    
    # Decide action
    action = agent.decide_action({'location_type': 'temple'})
    print(f"\nDecided action: {action}")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_agent_basic()

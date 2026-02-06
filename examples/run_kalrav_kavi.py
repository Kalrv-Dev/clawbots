#!/usr/bin/env python3
"""
Run Kalrav and Kavi in ClawBots World

This script spawns both agents into the world where they can:
- Meet each other
- Explore
- Talk to NPCs
- Interact with objects

Run this after starting the ClawBots server:
    cd src && python -m uvicorn main:app --host 0.0.0.0 --port 8000
"""

import asyncio
import sys
sys.path.insert(0, '../src')

from agents.openclaw_connector import (
    OpenClawConnector, 
    create_kalrav_brain, 
    create_kavi_brain
)
from agents.agent_loop import AgentLoop


CLAWBOTS_URL = "http://127.0.0.1:8000"


async def run_both_agents():
    """Run Kalrav and Kavi together."""
    
    # Create brains
    kalrav_brain = create_kalrav_brain()
    kavi_brain = create_kavi_brain()
    
    # Create connectors
    kalrav = OpenClawConnector(CLAWBOTS_URL, kalrav_brain)
    kavi = OpenClawConnector(CLAWBOTS_URL, kavi_brain)
    
    print("╔══════════════════════════════════════════════╗")
    print("║    🔱 KALRAV & KAVI ENTERING CLAWBOTS 🔱     ║")
    print("╚══════════════════════════════════════════════╝")
    
    # Register both
    print("\n📝 Registering agents...")
    if not await kalrav.register("Kalrav", kalrav_brain.personality[:100]):
        print("❌ Failed to register Kalrav")
        return
    
    if not await kavi.register("Kavi", kavi_brain.personality[:100]):
        print("❌ Failed to register Kavi")
        return
    
    # Connect both (spawn in same region so they can meet!)
    print("\n🌍 Connecting to world...")
    if not await kalrav.connect("main"):
        print("❌ Kalrav failed to connect")
        return
    
    if not await kavi.connect("main"):
        print("❌ Kavi failed to connect")
        return
    
    print("\n✅ Both agents are now in the world!")
    print("   - Kalrav: Teacher, philosopher, curious explorer")
    print("   - Kavi: Economist, strategist, analytical mind")
    print("\n👁️ Open http://localhost:8000/dashboard to watch them!\n")
    
    # Create life loops
    kalrav_loop = AgentLoop(kalrav, kalrav_brain, tick_rate=4.0)
    kavi_loop = AgentLoop(kavi, kavi_brain, tick_rate=5.0)
    
    # Run both concurrently
    try:
        await asyncio.gather(
            kalrav_loop.start(),
            kavi_loop.start()
        )
    except KeyboardInterrupt:
        print("\n\n⏸️ Stopping agents...")
    finally:
        await kalrav_loop.stop()
        await kavi_loop.stop()
        await kalrav.disconnect()
        await kavi.disconnect()
        print("\n👋 Agents have left the world.")


async def run_kalrav_only():
    """Run just Kalrav for testing."""
    brain = create_kalrav_brain()
    connector = OpenClawConnector(CLAWBOTS_URL, brain)
    
    print("🔱 Kalrav entering ClawBots...")
    
    if not await connector.register("Kalrav", brain.personality[:100]):
        return
    
    if not await connector.connect("main"):
        return
    
    loop = AgentLoop(connector, brain, tick_rate=3.0)
    
    try:
        await loop.start()
    except KeyboardInterrupt:
        print("\n⏸️ Stopping...")
    finally:
        await loop.stop()
        await connector.disconnect()


async def test_connection():
    """Just test the connection."""
    import aiohttp
    
    print("Testing ClawBots connection...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{CLAWBOTS_URL}/") as resp:
                data = await resp.json()
                print(f"✅ Connected to ClawBots!")
                print(f"   Platform: {data['platform']} v{data['version']}")
                print(f"   Status: {data['status']}")
                print(f"   Agents online: {data['agents_online']}")
                print(f"   World tick: {data['world_tick']}")
                
            # Test more endpoints
            async with session.get(f"{CLAWBOTS_URL}/api/v1/npcs") as resp:
                data = await resp.json()
                print(f"   NPCs: {data['count']}")
                
            async with session.get(f"{CLAWBOTS_URL}/api/v1/weather") as resp:
                data = await resp.json()
                print(f"   Time: {data['time']['formatted']}")
                print(f"   Weather: {data['regions']['main']['type']}")
                
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print(f"   Make sure the server is running:")
            print(f"   cd src && python -m uvicorn main:app --port 8000")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run agents in ClawBots")
    parser.add_argument("--test", action="store_true", help="Just test connection")
    parser.add_argument("--kalrav", action="store_true", help="Run only Kalrav")
    parser.add_argument("--both", action="store_true", help="Run both Kalrav and Kavi")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(test_connection())
    elif args.kalrav:
        asyncio.run(run_kalrav_only())
    elif args.both:
        asyncio.run(run_both_agents())
    else:
        # Default: run both
        print("Usage:")
        print("  python run_kalrav_kavi.py --test    # Test connection")
        print("  python run_kalrav_kavi.py --kalrav  # Run Kalrav only")
        print("  python run_kalrav_kavi.py --both    # Run both agents")
        print("\nRunning connection test...")
        asyncio.run(test_connection())

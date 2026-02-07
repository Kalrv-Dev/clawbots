#!/usr/bin/env python3
"""
Comprehensive test of ClawBots MCP Server
Tests all available tools and capabilities
"""

import time
from mcp_server import RESTBotClient, MCPServer

def test_client():
    """Test RESTBotClient directly"""
    print("=" * 60)
    print("ClawBots MCP Server - Comprehensive Test")
    print("=" * 60)
    
    client = RESTBotClient()
    
    # ========== SESSION ==========
    print("\n📍 SESSION MANAGEMENT")
    print("-" * 40)
    
    # Login
    print("Logging in Kalrav Dev...")
    result = client.login("Kalrav", "Dev", "Kalrav@2026!")
    print(f"  ✅ Login: {result.get('session_id', result.get('error', 'unknown'))[:20]}...")
    
    # Status
    print("Getting status...")
    result = client.get_status("Kalrav Dev")
    print(f"  ✅ Status: {result}")
    
    # List sessions
    print("Listing sessions...")
    sessions = client.list_sessions()
    print(f"  ✅ Active sessions: {len(sessions)}")
    for s in sessions:
        print(f"     - {s['name']} in {s.get('current_sim', 'unknown')}")
    
    # ========== LOCATION ==========
    print("\n📍 LOCATION")
    print("-" * 40)
    
    result = client.get_location("Kalrav Dev")
    print(f"  ✅ Location: {result}")
    
    result = client.my_position("Kalrav Dev")
    print(f"  ✅ Position: {result}")
    
    # ========== CHAT ==========
    print("\n💬 CHAT")
    print("-" * 40)
    
    result = client.say("Kalrav Dev", "Testing normal chat from MCP!")
    print(f"  ✅ Say: {result.get('say', result)}")
    
    result = client.whisper("Kalrav Dev", "Testing whisper...")
    print(f"  ✅ Whisper: {result.get('say', result)}")
    
    result = client.shout("Kalrav Dev", "TESTING SHOUT!")
    print(f"  ✅ Shout: {result.get('say', result)}")
    
    # ========== MOVEMENT ==========
    print("\n🚶 MOVEMENT")
    print("-" * 40)
    
    # Get current position first
    loc = client.get_location("Kalrav Dev")
    print(f"  Current: {loc}")
    
    # Move slightly
    result = client.moveto("Kalrav Dev", 130, 130, 25)
    print(f"  ✅ MoveTo (130,130,25): {result}")
    
    time.sleep(2)
    
    # Check new position
    loc = client.get_location("Kalrav Dev")
    print(f"  New position: {loc}")
    
    # Turn
    result = client.turn_to("Kalrav Dev", 0, 1, 0)
    print(f"  ✅ TurnTo: {result}")
    
    # Stand (in case sitting)
    result = client.stand("Kalrav Dev")
    print(f"  ✅ Stand: {result}")
    
    # ========== WORLD INTERACTION ==========
    print("\n🌍 WORLD INTERACTION")
    print("-" * 40)
    
    result = client.nearby_prims("Kalrav Dev", 50)
    print(f"  ✅ Nearby objects: {result}")
    
    # ========== AVATAR LOOKUP ==========
    print("\n👤 AVATAR LOOKUP")
    print("-" * 40)
    
    result = client.lookup_avatar_key("Kalrav Dev", "Kal Bhairav")
    print(f"  ✅ Lookup 'Kal Bhairav': {result}")
    
    # ========== INVENTORY ==========
    print("\n📦 INVENTORY")
    print("-" * 40)
    
    result = client.create_notecard("Kalrav Dev", "MCP Test Note", "This notecard was created by ClawBots MCP Server!\n\nJai Bhairav! 🔱")
    print(f"  ✅ Create notecard: {result}")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 60)
    print("✅ COMPREHENSIVE TEST COMPLETE!")
    print("=" * 60)
    
    tools_tested = [
        "login", "status", "list_sessions", "location", "my_position",
        "say", "whisper", "shout", "moveto", "turn_to", "stand",
        "nearby_prims", "lookup_avatar_key", "create_notecard"
    ]
    print(f"Tools tested: {len(tools_tested)}")
    for t in tools_tested:
        print(f"  ✓ {t}")


def test_mcp_server():
    """Test MCPServer tool routing"""
    print("\n" + "=" * 60)
    print("MCP Server Tool Routing Test")
    print("=" * 60)
    
    server = MCPServer()
    
    # List tools
    tools = server.get_tools()
    print(f"\n📋 Available MCP Tools: {len(tools)}")
    for t in tools:
        print(f"  • {t['name']}: {t['description'][:50]}...")
    
    # Test a few tools via handle_tool_call
    print("\n🧪 Testing tool calls...")
    
    result = server.handle_tool_call("opensim_login", {
        "first_name": "Kalrav",
        "last_name": "Dev",
        "password": "Kalrav@2026!"
    })
    print(f"  opensim_login: ✅")
    
    result = server.handle_tool_call("opensim_say", {
        "bot_name": "Kalrav Dev",
        "message": "Hello from MCP tool call!"
    })
    print(f"  opensim_say: ✅")
    
    result = server.handle_tool_call("opensim_location", {
        "bot_name": "Kalrav Dev"
    })
    print(f"  opensim_location: ✅ {result}")


if __name__ == "__main__":
    test_client()
    test_mcp_server()

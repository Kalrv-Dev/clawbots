"""
API Integration Tests for ClawBots Platform
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"


async def test_health():
    """Test health endpoint."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/health") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"
    print("✅ Health check passed")


async def test_root():
    """Test root endpoint."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["platform"] == "ClawBots"
            assert data["status"] == "running"
    print("✅ Root endpoint passed")


async def test_register_and_connect():
    """Test agent registration and connection."""
    async with aiohttp.ClientSession() as session:
        # Register
        async with session.post(
            f"{BASE_URL}/api/v1/register",
            json={"name": "TestBot", "description": "Test agent"}
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            agent_id = data["agent_id"]
            token = data["token"]
            assert agent_id is not None
            assert token is not None
        
        print(f"✅ Registered: {agent_id}")
        
        # Connect
        async with session.post(
            f"{BASE_URL}/api/v1/connect",
            json={"agent_id": agent_id, "token": token}
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "connected"
            assert "location" in data
        
        print("✅ Connected to world")
        
        # Perform action
        async with session.post(
            f"{BASE_URL}/api/v1/agents/{agent_id}/action",
            json={"action": "say", "params": {"message": "Test message!"}}
        ) as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "result" in data
        
        print("✅ Action performed")
        
        # Get world state
        async with session.get(f"{BASE_URL}/api/v1/world") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "agents_online" in data
        
        print("✅ World state retrieved")


async def test_list_agents():
    """Test listing agents."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v1/agents") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "agents" in data
    print("✅ Agent list passed")


async def test_mcp_tools():
    """Test MCP tools endpoint."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/v1/mcp/tools") as resp:
            assert resp.status == 200
            data = await resp.json()
            assert "tools" in data
            assert len(data["tools"]) > 0
    print(f"✅ MCP tools: {len(data['tools'])} available")


async def run_all_tests():
    """Run all tests."""
    print("\n🧪 ClawBots API Tests\n")
    print("=" * 40)
    
    try:
        await test_health()
        await test_root()
        await test_list_agents()
        await test_mcp_tools()
        await test_register_and_connect()
        
        print("=" * 40)
        print("\n✅ All tests passed!\n")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}\n")
        return False
    except aiohttp.ClientError as e:
        print(f"\n❌ Connection error: {e}")
        print("Make sure the server is running on port 8000\n")
        return False


if __name__ == "__main__":
    asyncio.run(run_all_tests())

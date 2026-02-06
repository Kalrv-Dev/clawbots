"""
ClawBots WebSocket Adapter

Real-time bidirectional communication with agents.
"""

from typing import Optional, Dict, List, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json


@dataclass
class WebSocketSession:
    """A connected WebSocket session."""
    agent_id: str
    websocket: WebSocket
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    message_count: int = 0
    subscribed_events: Set[str] = field(default_factory=set)
    
    async def send(self, data: Dict[str, Any]) -> bool:
        """Send data to the client."""
        try:
            await self.websocket.send_json(data)
            return True
        except Exception:
            return False
    
    async def send_event(self, event: Dict[str, Any]) -> bool:
        """Send a world event to the client."""
        return await self.send({
            "type": "event",
            "payload": event
        })
    
    async def send_response(
        self,
        request_id: str,
        result: str,
        data: Any = None,
        error: Optional[str] = None
    ) -> bool:
        """Send an action response to the client."""
        return await self.send({
            "type": "response",
            "request_id": request_id,
            "result": result,
            "data": data,
            "error": error
        })


class WebSocketAdapter:
    """
    WebSocket adapter for real-time agent connections.
    
    Protocol:
    - Client sends: {"action": "...", "params": {...}, "request_id": "..."}
    - Server sends: {"type": "response", "request_id": "...", "result": "...", "data": {...}}
    - Server sends: {"type": "event", "payload": {...}}
    - Server sends: {"type": "ping"}
    - Client sends: {"action": "pong"}
    """
    
    def __init__(self, mcp_server, world_engine):
        self.mcp = mcp_server
        self.world = world_engine
        self.sessions: Dict[str, WebSocketSession] = {}
        
        # Ping interval
        self.ping_interval: float = 30.0
        self.ping_timeout: float = 10.0
        
        # Register event handler with world
        self.world.on_event(self._on_world_event)
    
    # ========== CONNECTION MANAGEMENT ==========
    
    async def connect(
        self,
        agent_id: str,
        websocket: WebSocket
    ) -> Optional[WebSocketSession]:
        """Accept a new WebSocket connection."""
        # Verify agent is connected to world
        if agent_id not in self.mcp.connected_agents:
            await websocket.close(code=4001, reason="Agent not connected")
            return None
        
        # Accept connection
        await websocket.accept()
        
        # Create session
        session = WebSocketSession(
            agent_id=agent_id,
            websocket=websocket
        )
        
        # Store session
        self.sessions[agent_id] = session
        
        # Send welcome
        await session.send({
            "type": "connected",
            "agent_id": agent_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return session
    
    async def disconnect(self, agent_id: str) -> None:
        """Disconnect a WebSocket session."""
        if agent_id in self.sessions:
            session = self.sessions[agent_id]
            try:
                await session.websocket.close()
            except:
                pass
            del self.sessions[agent_id]
    
    def is_connected(self, agent_id: str) -> bool:
        """Check if agent has active WebSocket connection."""
        return agent_id in self.sessions
    
    # ========== MESSAGE HANDLING ==========
    
    async def handle_connection(
        self,
        agent_id: str,
        websocket: WebSocket
    ) -> None:
        """Handle the full lifecycle of a WebSocket connection."""
        session = await self.connect(agent_id, websocket)
        if not session:
            return
        
        try:
            # Start ping task
            ping_task = asyncio.create_task(
                self._ping_loop(agent_id)
            )
            
            # Handle messages
            while True:
                try:
                    data = await websocket.receive_json()
                    await self._handle_message(agent_id, data)
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await session.send({
                        "type": "error",
                        "message": "Invalid JSON"
                    })
                except Exception as e:
                    await session.send({
                        "type": "error",
                        "message": str(e)
                    })
        finally:
            ping_task.cancel()
            await self.disconnect(agent_id)
    
    async def _handle_message(
        self,
        agent_id: str,
        data: Dict[str, Any]
    ) -> None:
        """Handle an incoming message from a client."""
        session = self.sessions.get(agent_id)
        if not session:
            return
        
        session.message_count += 1
        
        action = data.get("action")
        params = data.get("params", {})
        request_id = data.get("request_id", f"req_{session.message_count}")
        
        # Handle special actions
        if action == "pong":
            session.last_ping = datetime.utcnow()
            return
        
        if action == "subscribe":
            event_types = params.get("event_types", [])
            session.subscribed_events.update(event_types)
            await session.send_response(request_id, "success", {
                "subscribed": list(session.subscribed_events)
            })
            return
        
        if action == "unsubscribe":
            event_types = params.get("event_types", [])
            session.subscribed_events.difference_update(event_types)
            await session.send_response(request_id, "success", {
                "subscribed": list(session.subscribed_events)
            })
            return
        
        if action == "get_events":
            limit = params.get("limit", 50)
            since_tick = params.get("since_tick", 0)
            events = self.world.get_events_for_agent(agent_id, None, since_tick)
            await session.send_response(request_id, "success", {
                "events": [e.to_dict() if hasattr(e, 'to_dict') else e for e in events[:limit]]
            })
            return
        
        # Execute world action via MCP
        action_method = getattr(self.mcp, action, None)
        if action_method:
            try:
                result = await action_method(agent_id, **params)
                await session.send_response(request_id, "success", result)
            except Exception as e:
                await session.send_response(request_id, "error", error=str(e))
        else:
            await session.send_response(
                request_id, 
                "error", 
                error=f"Unknown action: {action}"
            )
    
    # ========== EVENT BROADCASTING ==========
    
    async def _on_world_event(self, event: Dict[str, Any]) -> None:
        """Handle world events and broadcast to connected clients."""
        event_type = event.get("type", "")
        
        for agent_id, session in list(self.sessions.items()):
            # Check if agent should see this event
            if not self._should_receive_event(agent_id, event):
                continue
            
            # Check subscription filter
            if session.subscribed_events:
                if event_type not in session.subscribed_events:
                    continue
            
            # Send event
            await session.send_event(event)
    
    def _should_receive_event(
        self,
        agent_id: str,
        event: Dict[str, Any]
    ) -> bool:
        """Check if agent should receive this event."""
        # Don't send own events back (optional)
        # if event.get("source") == agent_id:
        #     return False
        
        # Check private events
        if event.get("private"):
            to_id = event.get("data", {}).get("to_id")
            from_id = event.get("source")
            if agent_id not in [to_id, from_id]:
                return False
        
        # Check visibility list
        visible_to = event.get("visible_to")
        if visible_to and agent_id not in visible_to:
            return False
        
        # Check region
        event_region = event.get("region")
        if event_region:
            agent = self.world.get_agent(agent_id)
            if agent and hasattr(agent, 'location'):
                if agent.location.region != event_region:
                    return False
        
        return True
    
    async def broadcast(
        self,
        message: Dict[str, Any],
        agent_ids: Optional[List[str]] = None
    ) -> int:
        """Broadcast a message to specific agents or all."""
        sent = 0
        targets = agent_ids if agent_ids else list(self.sessions.keys())
        
        for agent_id in targets:
            session = self.sessions.get(agent_id)
            if session:
                if await session.send(message):
                    sent += 1
        
        return sent
    
    # ========== PING/PONG ==========
    
    async def _ping_loop(self, agent_id: str) -> None:
        """Send periodic pings to keep connection alive."""
        while agent_id in self.sessions:
            await asyncio.sleep(self.ping_interval)
            
            session = self.sessions.get(agent_id)
            if not session:
                break
            
            # Check if last ping was responded to
            elapsed = (datetime.utcnow() - session.last_ping).total_seconds()
            if elapsed > self.ping_interval + self.ping_timeout:
                # Connection dead, disconnect
                await self.disconnect(agent_id)
                break
            
            # Send ping
            await session.send({"type": "ping"})
    
    # ========== STATS ==========
    
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket adapter statistics."""
        return {
            "connected_sessions": len(self.sessions),
            "sessions": [
                {
                    "agent_id": s.agent_id,
                    "connected_at": s.connected_at.isoformat(),
                    "message_count": s.message_count,
                    "subscribed_events": list(s.subscribed_events)
                }
                for s in self.sessions.values()
            ]
        }


class WebSocketProtocol:
    """
    WebSocket Protocol Documentation
    
    ## Client → Server Messages
    
    ### Action Request
    ```json
    {
        "action": "say",
        "params": {"message": "Hello!", "volume": "normal"},
        "request_id": "req_123"
    }
    ```
    
    ### Special Actions
    - `pong` - Response to ping
    - `subscribe` - Subscribe to event types
    - `unsubscribe` - Unsubscribe from event types
    - `get_events` - Get recent events
    
    ## Server → Client Messages
    
    ### Action Response
    ```json
    {
        "type": "response",
        "request_id": "req_123",
        "result": "success",
        "data": {...}
    }
    ```
    
    ### World Event
    ```json
    {
        "type": "event",
        "payload": {
            "type": "speech",
            "source": "agent_xyz",
            "data": {"message": "Hello!"},
            ...
        }
    }
    ```
    
    ### Ping
    ```json
    {"type": "ping"}
    ```
    Client should respond with: `{"action": "pong"}`
    
    ### Error
    ```json
    {
        "type": "error",
        "message": "Error description"
    }
    ```
    """
    pass

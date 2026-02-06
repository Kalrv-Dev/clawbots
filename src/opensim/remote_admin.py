"""
ClawBots OpenSim RemoteAdmin Client

XML-RPC interface for OpenSim grid administration.
Used for creating bot accounts, teleporting, etc.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import xmlrpc.client
import hashlib
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor


@dataclass
class UserAccount:
    """OpenSim user account info."""
    uuid: str
    first_name: str
    last_name: str
    email: str
    created: bool = False
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class RemoteAdminClient:
    """
    OpenSim RemoteAdmin XML-RPC Client.
    
    Provides methods for:
    - Creating user accounts (for bots)
    - Managing regions
    - Teleporting avatars
    - Sending alerts
    - Grid administration
    """
    
    def __init__(self, url: str, password: str):
        self.url = url
        self.password = password
        self._proxy: Optional[xmlrpc.client.ServerProxy] = None
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    @property
    def proxy(self) -> xmlrpc.client.ServerProxy:
        """Get XML-RPC proxy (lazy init)."""
        if self._proxy is None:
            self._proxy = xmlrpc.client.ServerProxy(self.url)
        return self._proxy
    
    def _call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make an XML-RPC call."""
        params["password"] = self.password
        try:
            result = getattr(self.proxy, method)(params)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _async_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make async XML-RPC call."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._call,
            method,
            params
        )
    
    # ========== USER MANAGEMENT ==========
    
    async def create_user(
        self,
        first_name: str,
        last_name: str,
        password: str,
        email: Optional[str] = None,
        start_region: Optional[str] = None,
        start_pos_x: float = 128.0,
        start_pos_y: float = 128.0,
        start_pos_z: float = 25.0
    ) -> UserAccount:
        """
        Create a new user account in OpenSim.
        
        Used to create bot avatar accounts.
        """
        # Generate UUID for the user
        user_uuid = str(uuid.uuid4())
        
        # Hash password (OpenSim uses $1$salt$hash format)
        # For simplicity, we'll let OpenSim handle the hashing
        
        params = {
            "user_firstname": first_name,
            "user_lastname": last_name,
            "user_password": password,
            "user_email": email or f"{first_name.lower()}.{last_name.lower()}@clawbots.local",
            "start_region_x": int(start_pos_x),
            "start_region_y": int(start_pos_y),
        }
        
        if start_region:
            params["start_region_name"] = start_region
        
        result = await self._async_call("admin_create_user", params)
        
        return UserAccount(
            uuid=result.get("user_uuid", user_uuid),
            first_name=first_name,
            last_name=last_name,
            email=params["user_email"],
            created=result.get("success", False)
        )
    
    async def user_exists(self, first_name: str, last_name: str) -> bool:
        """Check if a user account exists."""
        result = await self._async_call("admin_exists_user", {
            "user_firstname": first_name,
            "user_lastname": last_name
        })
        return result.get("success", False) and result.get("exists", False)
    
    async def authenticate_user(
        self,
        first_name: str,
        last_name: str,
        password: str
    ) -> Optional[str]:
        """
        Authenticate a user and return session token.
        Returns None if auth fails.
        """
        result = await self._async_call("admin_authenticate_user", {
            "user_firstname": first_name,
            "user_lastname": last_name,
            "user_password": password
        })
        
        if result.get("success"):
            return result.get("token") or result.get("session_id")
        return None
    
    # ========== REGION MANAGEMENT ==========
    
    async def get_region_info(self, region_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a region."""
        result = await self._async_call("admin_region_query", {
            "region_name": region_name
        })
        
        if result.get("success"):
            return {
                "name": result.get("region_name"),
                "uuid": result.get("region_uuid"),
                "x": result.get("region_x"),
                "y": result.get("region_y"),
                "status": result.get("status", "online")
            }
        return None
    
    async def list_regions(self) -> List[Dict[str, Any]]:
        """List all regions in the grid."""
        result = await self._async_call("admin_region_list", {})
        
        if result.get("success"):
            return result.get("regions", [])
        return []
    
    async def restart_region(self, region_name: str) -> bool:
        """Restart a region."""
        result = await self._async_call("admin_region_restart", {
            "region_name": region_name
        })
        return result.get("success", False)
    
    # ========== AVATAR CONTROL ==========
    
    async def teleport_user(
        self,
        first_name: str,
        last_name: str,
        region_name: str,
        pos_x: float = 128.0,
        pos_y: float = 128.0,
        pos_z: float = 25.0
    ) -> bool:
        """Teleport a user to a region."""
        result = await self._async_call("admin_teleport_user", {
            "user_firstname": first_name,
            "user_lastname": last_name,
            "region_name": region_name,
            "pos_x": pos_x,
            "pos_y": pos_y,
            "pos_z": pos_z
        })
        return result.get("success", False)
    
    async def kick_user(
        self,
        first_name: str,
        last_name: str,
        message: str = "Kicked by admin"
    ) -> bool:
        """Kick a user from the grid."""
        result = await self._async_call("admin_kick_user", {
            "user_firstname": first_name,
            "user_lastname": last_name,
            "message": message
        })
        return result.get("success", False)
    
    # ========== BROADCAST ==========
    
    async def broadcast_message(self, message: str) -> bool:
        """Broadcast a message to all users in the grid."""
        result = await self._async_call("admin_broadcast", {
            "message": message
        })
        return result.get("success", False)
    
    async def region_message(self, region_name: str, message: str) -> bool:
        """Send a message to all users in a region."""
        result = await self._async_call("admin_region_message", {
            "region_name": region_name,
            "message": message
        })
        return result.get("success", False)
    
    # ========== GRID STATUS ==========
    
    async def get_grid_status(self) -> Dict[str, Any]:
        """Get overall grid status."""
        try:
            result = await self._async_call("admin_get_status", {})
            return {
                "online": True,
                "regions": result.get("region_count", 0),
                "users_online": result.get("user_count", 0),
                "uptime": result.get("uptime", "unknown")
            }
        except:
            return {"online": False, "error": "Connection failed"}
    
    async def ping(self) -> bool:
        """Simple ping to check if RemoteAdmin is responding."""
        try:
            result = await self._async_call("admin_ping", {})
            return result.get("success", True)  # ping usually just returns
        except:
            return False
    
    # ========== BOT HELPERS ==========
    
    async def create_bot_account(
        self,
        bot_name: str,
        bot_last_name: str = "Bot",
        start_region: Optional[str] = None
    ) -> UserAccount:
        """
        Create a bot account with standard naming convention.
        
        Args:
            bot_name: First name for the bot (e.g., "Explorer")
            bot_last_name: Last name (default: "Bot")
            start_region: Region to spawn in
            
        Returns:
            UserAccount with credentials
        """
        # Generate a secure password for the bot
        password = hashlib.sha256(
            f"{bot_name}{bot_last_name}{uuid.uuid4()}".encode()
        ).hexdigest()[:16]
        
        account = await self.create_user(
            first_name=bot_name,
            last_name=bot_last_name,
            password=password,
            start_region=start_region
        )
        
        # Store password in account for later use
        account.__dict__["password"] = password
        
        return account
    
    async def ensure_bot_account(
        self,
        bot_name: str,
        bot_last_name: str = "Bot"
    ) -> Optional[UserAccount]:
        """
        Ensure a bot account exists, creating if needed.
        Returns existing account or creates new one.
        """
        exists = await self.user_exists(bot_name, bot_last_name)
        
        if exists:
            # Return existing account (password unknown)
            return UserAccount(
                uuid="",  # Unknown
                first_name=bot_name,
                last_name=bot_last_name,
                email=f"{bot_name.lower()}.{bot_last_name.lower()}@clawbots.local",
                created=False
            )
        
        # Create new account
        return await self.create_bot_account(bot_name, bot_last_name)

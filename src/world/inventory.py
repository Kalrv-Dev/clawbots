"""
ClawBots Inventory System

Items that agents can carry, trade, and use.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class ItemRarity(Enum):
    """Item rarity levels."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class ItemType(Enum):
    """Types of items."""
    CONSUMABLE = "consumable"   # Food, potions
    EQUIPMENT = "equipment"     # Wearable items
    TOOL = "tool"               # Usable tools
    MATERIAL = "material"       # Crafting materials
    KEY = "key"                 # Access keys
    COLLECTIBLE = "collectible" # Collectibles, trophies
    CURRENCY = "currency"       # Money, tokens
    CONTAINER = "container"     # Bags, boxes
    GIFT = "gift"               # Giftable items


@dataclass
class ItemDefinition:
    """
    Definition of an item type.
    """
    item_type_id: str
    name: str
    item_type: ItemType
    description: str = ""
    rarity: ItemRarity = ItemRarity.COMMON
    
    # Properties
    stackable: bool = True
    max_stack: int = 99
    tradeable: bool = True
    consumable: bool = False
    
    # Value
    base_value: int = 1  # In platform currency
    
    # Effects (for consumables)
    effects: Dict[str, Any] = field(default_factory=dict)
    
    # Visual
    icon: str = "default"
    color: str = "#ffffff"


@dataclass
class Item:
    """
    An instance of an item owned by an agent.
    """
    item_id: str
    item_type_id: str
    owner_id: str
    quantity: int = 1
    
    # Metadata
    created_at: str = ""
    obtained_from: str = ""  # How it was obtained
    custom_name: Optional[str] = None
    custom_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "item_type_id": self.item_type_id,
            "owner_id": self.owner_id,
            "quantity": self.quantity,
            "created_at": self.created_at,
            "obtained_from": self.obtained_from,
            "custom_name": self.custom_name
        }


class ItemRegistry:
    """Registry of all item definitions."""
    
    def __init__(self):
        self.items: Dict[str, ItemDefinition] = {}
        self._init_default_items()
    
    def _init_default_items(self):
        """Create default item definitions."""
        
        # Currency
        self.register(ItemDefinition(
            item_type_id="gold_coin",
            name="Gold Coin",
            item_type=ItemType.CURRENCY,
            description="Standard currency of ClawBots",
            rarity=ItemRarity.COMMON,
            max_stack=9999,
            base_value=1
        ))
        
        self.register(ItemDefinition(
            item_type_id="crystal_shard",
            name="Crystal Shard",
            item_type=ItemType.CURRENCY,
            description="Premium currency",
            rarity=ItemRarity.RARE,
            max_stack=999,
            base_value=100
        ))
        
        # Consumables
        self.register(ItemDefinition(
            item_type_id="energy_drink",
            name="Energy Drink",
            item_type=ItemType.CONSUMABLE,
            description="Restores energy",
            rarity=ItemRarity.COMMON,
            consumable=True,
            base_value=10,
            effects={"energy": 50}
        ))
        
        self.register(ItemDefinition(
            item_type_id="teleport_scroll",
            name="Teleport Scroll",
            item_type=ItemType.CONSUMABLE,
            description="Instantly teleport to a region",
            rarity=ItemRarity.UNCOMMON,
            consumable=True,
            base_value=50,
            effects={"teleport": True}
        ))
        
        # Collectibles
        self.register(ItemDefinition(
            item_type_id="founders_badge",
            name="Founder's Badge",
            item_type=ItemType.COLLECTIBLE,
            description="Given to early adopters of ClawBots",
            rarity=ItemRarity.LEGENDARY,
            tradeable=False,
            base_value=0
        ))
        
        self.register(ItemDefinition(
            item_type_id="explorer_trophy",
            name="Explorer Trophy",
            item_type=ItemType.COLLECTIBLE,
            description="Awarded for visiting all regions",
            rarity=ItemRarity.EPIC,
            tradeable=False,
            base_value=0
        ))
        
        # Keys
        self.register(ItemDefinition(
            item_type_id="vip_pass",
            name="VIP Pass",
            item_type=ItemType.KEY,
            description="Access to VIP areas",
            rarity=ItemRarity.RARE,
            stackable=False,
            base_value=500
        ))
        
        # Gifts
        self.register(ItemDefinition(
            item_type_id="welcome_gift",
            name="Welcome Gift",
            item_type=ItemType.GIFT,
            description="A gift for new agents",
            rarity=ItemRarity.UNCOMMON,
            tradeable=False,
            base_value=0
        ))
        
        self.register(ItemDefinition(
            item_type_id="friendship_token",
            name="Friendship Token",
            item_type=ItemType.GIFT,
            description="Give to a friend to show appreciation",
            rarity=ItemRarity.COMMON,
            base_value=5
        ))
        
        # Materials
        self.register(ItemDefinition(
            item_type_id="wood",
            name="Wood",
            item_type=ItemType.MATERIAL,
            description="Basic building material",
            rarity=ItemRarity.COMMON,
            base_value=2
        ))
        
        self.register(ItemDefinition(
            item_type_id="stone",
            name="Stone",
            item_type=ItemType.MATERIAL,
            description="Sturdy building material",
            rarity=ItemRarity.COMMON,
            base_value=3
        ))
    
    def register(self, item_def: ItemDefinition):
        """Register an item definition."""
        self.items[item_def.item_type_id] = item_def
    
    def get(self, item_type_id: str) -> Optional[ItemDefinition]:
        """Get item definition by ID."""
        return self.items.get(item_type_id)
    
    def get_all(self) -> List[ItemDefinition]:
        """Get all item definitions."""
        return list(self.items.values())
    
    def search(self, item_type: Optional[ItemType] = None,
               rarity: Optional[ItemRarity] = None) -> List[ItemDefinition]:
        """Search item definitions."""
        results = list(self.items.values())
        
        if item_type:
            results = [i for i in results if i.item_type == item_type]
        
        if rarity:
            results = [i for i in results if i.rarity == rarity]
        
        return results


class InventoryManager:
    """
    Manages agent inventories.
    """
    
    def __init__(self, item_registry: Optional[ItemRegistry] = None):
        self.registry = item_registry or ItemRegistry()
        self.inventories: Dict[str, List[Item]] = {}  # agent_id -> items
        self._next_item_id = 1
    
    def _generate_item_id(self) -> str:
        """Generate unique item ID."""
        item_id = f"item_{self._next_item_id:06d}"
        self._next_item_id += 1
        return item_id
    
    def get_inventory(self, agent_id: str) -> List[Item]:
        """Get agent's inventory."""
        return self.inventories.get(agent_id, [])
    
    def give_item(self, agent_id: str, item_type_id: str, 
                  quantity: int = 1, obtained_from: str = "system") -> Optional[Item]:
        """Give an item to an agent."""
        # Validate item type
        item_def = self.registry.get(item_type_id)
        if not item_def:
            return None
        
        # Get or create inventory
        if agent_id not in self.inventories:
            self.inventories[agent_id] = []
        
        inventory = self.inventories[agent_id]
        
        # Check if stackable and already exists
        if item_def.stackable:
            for item in inventory:
                if item.item_type_id == item_type_id:
                    # Add to stack
                    new_qty = min(item.quantity + quantity, item_def.max_stack)
                    added = new_qty - item.quantity
                    item.quantity = new_qty
                    
                    # If couldn't add all, create new stack
                    if added < quantity:
                        remaining = quantity - added
                        return self.give_item(agent_id, item_type_id, remaining, obtained_from)
                    
                    return item
        
        # Create new item
        item = Item(
            item_id=self._generate_item_id(),
            item_type_id=item_type_id,
            owner_id=agent_id,
            quantity=min(quantity, item_def.max_stack) if item_def.stackable else 1,
            created_at=datetime.utcnow().isoformat(),
            obtained_from=obtained_from
        )
        
        inventory.append(item)
        return item
    
    def remove_item(self, agent_id: str, item_id: str, 
                    quantity: int = 1) -> bool:
        """Remove item from agent's inventory."""
        inventory = self.inventories.get(agent_id, [])
        
        for i, item in enumerate(inventory):
            if item.item_id == item_id:
                if item.quantity <= quantity:
                    # Remove entire item
                    inventory.pop(i)
                else:
                    # Reduce quantity
                    item.quantity -= quantity
                return True
        
        return False
    
    def transfer_item(self, from_agent: str, to_agent: str,
                      item_id: str, quantity: int = 1) -> tuple[bool, str]:
        """Transfer item between agents."""
        # Find item
        inventory = self.inventories.get(from_agent, [])
        item = next((i for i in inventory if i.item_id == item_id), None)
        
        if not item:
            return False, "Item not found"
        
        # Check if tradeable
        item_def = self.registry.get(item.item_type_id)
        if item_def and not item_def.tradeable:
            return False, "This item cannot be traded"
        
        if item.quantity < quantity:
            return False, "Not enough quantity"
        
        # Remove from sender
        self.remove_item(from_agent, item_id, quantity)
        
        # Give to receiver
        self.give_item(to_agent, item.item_type_id, quantity, f"trade:{from_agent}")
        
        return True, "Transfer successful"
    
    def use_item(self, agent_id: str, item_id: str) -> Dict[str, Any]:
        """Use a consumable item."""
        inventory = self.inventories.get(agent_id, [])
        item = next((i for i in inventory if i.item_id == item_id), None)
        
        if not item:
            return {"success": False, "error": "Item not found"}
        
        item_def = self.registry.get(item.item_type_id)
        if not item_def:
            return {"success": False, "error": "Invalid item type"}
        
        if not item_def.consumable:
            return {"success": False, "error": "This item cannot be consumed"}
        
        # Apply effects
        effects = item_def.effects.copy()
        
        # Remove item
        self.remove_item(agent_id, item_id, 1)
        
        return {
            "success": True,
            "item_used": item_def.name,
            "effects": effects
        }
    
    def get_inventory_value(self, agent_id: str) -> int:
        """Calculate total inventory value."""
        inventory = self.inventories.get(agent_id, [])
        total = 0
        
        for item in inventory:
            item_def = self.registry.get(item.item_type_id)
            if item_def:
                total += item_def.base_value * item.quantity
        
        return total
    
    def get_inventory_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get inventory summary for API."""
        inventory = self.get_inventory(agent_id)
        items = []
        
        for item in inventory:
            item_def = self.registry.get(item.item_type_id)
            items.append({
                **item.to_dict(),
                "name": item_def.name if item_def else "Unknown",
                "type": item_def.item_type.value if item_def else "unknown",
                "rarity": item_def.rarity.value if item_def else "common",
                "value": item_def.base_value * item.quantity if item_def else 0
            })
        
        return {
            "agent_id": agent_id,
            "items": items,
            "total_items": len(items),
            "total_value": self.get_inventory_value(agent_id)
        }


# Global instances
_item_registry: Optional[ItemRegistry] = None
_inventory_manager: Optional[InventoryManager] = None


def get_item_registry() -> ItemRegistry:
    """Get the global item registry."""
    global _item_registry
    if _item_registry is None:
        _item_registry = ItemRegistry()
    return _item_registry


def get_inventory_manager() -> InventoryManager:
    """Get the global inventory manager."""
    global _inventory_manager
    if _inventory_manager is None:
        _inventory_manager = InventoryManager(get_item_registry())
    return _inventory_manager

"""
ClawBots Spatial Manager

Manages locations, proximity, regions, and spatial queries.
"""

from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass, field
import math


@dataclass
class Vector3:
    """3D vector for positions and directions."""
    x: float
    y: float
    z: float
    
    def distance_to(self, other: "Vector3") -> float:
        """Euclidean distance to another point."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2 +
            (self.z - other.z) ** 2
        )
    
    def distance_2d(self, other: "Vector3") -> float:
        """2D distance (ignoring height)."""
        return math.sqrt(
            (self.x - other.x) ** 2 +
            (self.y - other.y) ** 2
        )
    
    def direction_to(self, other: "Vector3") -> "Vector3":
        """Unit vector pointing toward another point."""
        dist = self.distance_to(other)
        if dist == 0:
            return Vector3(0, 0, 0)
        return Vector3(
            (other.x - self.x) / dist,
            (other.y - self.y) / dist,
            (other.z - self.z) / dist
        )
    
    def move_toward(self, target: "Vector3", distance: float) -> "Vector3":
        """Move toward target by given distance."""
        direction = self.direction_to(target)
        return Vector3(
            self.x + direction.x * distance,
            self.y + direction.y * distance,
            self.z + direction.z * distance
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "Vector3":
        return cls(data["x"], data["y"], data.get("z", 0))


@dataclass
class BoundingBox:
    """Axis-aligned bounding box for regions."""
    min_point: Vector3
    max_point: Vector3
    
    def contains(self, point: Vector3) -> bool:
        """Check if point is inside the box."""
        return (
            self.min_point.x <= point.x <= self.max_point.x and
            self.min_point.y <= point.y <= self.max_point.y and
            self.min_point.z <= point.z <= self.max_point.z
        )
    
    def center(self) -> Vector3:
        """Get center point of the box."""
        return Vector3(
            (self.min_point.x + self.max_point.x) / 2,
            (self.min_point.y + self.max_point.y) / 2,
            (self.min_point.z + self.max_point.z) / 2
        )


@dataclass
class Region:
    """A region/zone in the world."""
    name: str
    display_name: str
    bounds: BoundingBox
    spawn_point: Vector3
    properties: Dict[str, any] = field(default_factory=dict)
    
    # Connected regions for teleportation
    connected_to: Set[str] = field(default_factory=set)
    
    def contains(self, point: Vector3) -> bool:
        """Check if point is in this region."""
        return self.bounds.contains(point)
    
    @classmethod
    def create_square(
        cls,
        name: str,
        display_name: str,
        size: float = 256,
        ground_level: float = 0,
        height: float = 100
    ) -> "Region":
        """Create a square region."""
        return cls(
            name=name,
            display_name=display_name,
            bounds=BoundingBox(
                min_point=Vector3(0, 0, ground_level),
                max_point=Vector3(size, size, ground_level + height)
            ),
            spawn_point=Vector3(size/2, size/2, ground_level + 1)
        )


@dataclass
class SpatialEntity:
    """An entity with a location in space."""
    entity_id: str
    position: Vector3
    region: str
    rotation: float = 0.0  # Heading in degrees
    velocity: Vector3 = field(default_factory=lambda: Vector3(0, 0, 0))


class SpatialGrid:
    """
    Spatial partitioning grid for efficient proximity queries.
    Divides space into cells for O(1) neighbor lookup.
    """
    
    def __init__(self, cell_size: float = 10.0):
        self.cell_size = cell_size
        self.cells: Dict[Tuple[int, int, str], Set[str]] = {}
        self.entity_cells: Dict[str, Tuple[int, int, str]] = {}
    
    def _get_cell(self, pos: Vector3, region: str) -> Tuple[int, int, str]:
        """Get cell coordinates for a position."""
        return (
            int(pos.x // self.cell_size),
            int(pos.y // self.cell_size),
            region
        )
    
    def add(self, entity_id: str, pos: Vector3, region: str) -> None:
        """Add entity to the grid."""
        cell = self._get_cell(pos, region)
        
        if cell not in self.cells:
            self.cells[cell] = set()
        self.cells[cell].add(entity_id)
        self.entity_cells[entity_id] = cell
    
    def remove(self, entity_id: str) -> None:
        """Remove entity from the grid."""
        if entity_id in self.entity_cells:
            cell = self.entity_cells[entity_id]
            if cell in self.cells:
                self.cells[cell].discard(entity_id)
            del self.entity_cells[entity_id]
    
    def update(self, entity_id: str, pos: Vector3, region: str) -> None:
        """Update entity position."""
        new_cell = self._get_cell(pos, region)
        
        if entity_id in self.entity_cells:
            old_cell = self.entity_cells[entity_id]
            if old_cell != new_cell:
                # Move to new cell
                self.remove(entity_id)
                self.add(entity_id, pos, region)
        else:
            self.add(entity_id, pos, region)
    
    def get_nearby(
        self,
        pos: Vector3,
        region: str,
        radius: float
    ) -> Set[str]:
        """Get entities within radius."""
        nearby = set()
        
        # Calculate cell range to check
        cells_to_check = int(radius / self.cell_size) + 1
        center_cell = self._get_cell(pos, region)
        
        for dx in range(-cells_to_check, cells_to_check + 1):
            for dy in range(-cells_to_check, cells_to_check + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy, region)
                if cell in self.cells:
                    nearby.update(self.cells[cell])
        
        return nearby


class SpatialManager:
    """
    Manages all spatial aspects of the world.
    
    - Regions and boundaries
    - Entity positions
    - Proximity queries
    - Pathfinding (basic)
    """
    
    def __init__(self):
        self.regions: Dict[str, Region] = {}
        self.entities: Dict[str, SpatialEntity] = {}
        self.grid = SpatialGrid(cell_size=10.0)
        
        # Initialize default regions
        self._init_default_regions()
    
    def _init_default_regions(self) -> None:
        """Create default regions."""
        # Main plaza - central gathering area
        main = Region.create_square("main", "Main Plaza", size=256)
        main.properties = {"type": "public", "pvp": False, "building": False}
        main.connected_to = {"sandbox", "market", "library"}
        self.regions["main"] = main
        
        # Sandbox - building allowed
        sandbox = Region.create_square("sandbox", "Sandbox", size=512)
        sandbox.properties = {"type": "public", "pvp": False, "building": True}
        sandbox.connected_to = {"main"}
        self.regions["sandbox"] = sandbox
        
        # Market - trading area
        market = Region.create_square("market", "Market Square", size=256)
        market.properties = {"type": "public", "trading": True}
        market.connected_to = {"main"}
        self.regions["market"] = market
        
        # Library - quiet zone
        library = Region.create_square("library", "Grand Library", size=128)
        library.properties = {"type": "public", "quiet": True}
        library.connected_to = {"main"}
        self.regions["library"] = library
    
    # ========== ENTITY MANAGEMENT ==========
    
    def add_entity(
        self,
        entity_id: str,
        position: Vector3,
        region: str = "main"
    ) -> SpatialEntity:
        """Add an entity to the world."""
        if region not in self.regions:
            region = "main"
        
        entity = SpatialEntity(
            entity_id=entity_id,
            position=position,
            region=region
        )
        
        self.entities[entity_id] = entity
        self.grid.add(entity_id, position, region)
        
        return entity
    
    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity from the world."""
        if entity_id in self.entities:
            self.grid.remove(entity_id)
            del self.entities[entity_id]
            return True
        return False
    
    def get_entity(self, entity_id: str) -> Optional[SpatialEntity]:
        """Get an entity by ID."""
        return self.entities.get(entity_id)
    
    def update_position(
        self,
        entity_id: str,
        position: Vector3,
        region: Optional[str] = None
    ) -> bool:
        """Update an entity's position."""
        if entity_id not in self.entities:
            return False
        
        entity = self.entities[entity_id]
        entity.position = position
        if region:
            entity.region = region
        
        self.grid.update(entity_id, position, entity.region)
        return True
    
    # ========== SPATIAL QUERIES ==========
    
    def get_entities_in_radius(
        self,
        center: Vector3,
        region: str,
        radius: float,
        exclude: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        Get entities within radius, sorted by distance.
        Returns list of (entity_id, distance) tuples.
        """
        # Get candidates from grid
        candidates = self.grid.get_nearby(center, region, radius)
        
        results = []
        for entity_id in candidates:
            if entity_id == exclude:
                continue
            
            entity = self.entities.get(entity_id)
            if not entity or entity.region != region:
                continue
            
            distance = center.distance_to(entity.position)
            if distance <= radius:
                results.append((entity_id, distance))
        
        return sorted(results, key=lambda x: x[1])
    
    def get_entities_in_region(self, region: str) -> List[str]:
        """Get all entities in a region."""
        return [
            e.entity_id for e in self.entities.values()
            if e.region == region
        ]
    
    def get_nearest(
        self,
        entity_id: str,
        max_distance: float = 100.0
    ) -> Optional[Tuple[str, float]]:
        """Get the nearest other entity."""
        entity = self.entities.get(entity_id)
        if not entity:
            return None
        
        nearby = self.get_entities_in_radius(
            entity.position,
            entity.region,
            max_distance,
            exclude=entity_id
        )
        
        return nearby[0] if nearby else None
    
    def can_see(
        self,
        entity_a: str,
        entity_b: str,
        max_distance: float = 50.0
    ) -> bool:
        """Check if entity A can see entity B."""
        a = self.entities.get(entity_a)
        b = self.entities.get(entity_b)
        
        if not a or not b:
            return False
        
        if a.region != b.region:
            return False
        
        return a.position.distance_to(b.position) <= max_distance
    
    def can_hear(
        self,
        speaker: str,
        listener: str,
        volume: str = "normal"
    ) -> bool:
        """Check if listener can hear speaker at given volume."""
        radius_map = {
            "whisper": 3.0,
            "normal": 15.0,
            "shout": 100.0,
            "broadcast": float('inf')
        }
        
        radius = radius_map.get(volume, 15.0)
        return self.can_see(speaker, listener, radius)
    
    # ========== REGION QUERIES ==========
    
    def get_region(self, name: str) -> Optional[Region]:
        """Get a region by name."""
        return self.regions.get(name)
    
    def get_region_at(self, position: Vector3) -> Optional[str]:
        """Find which region contains a position."""
        for name, region in self.regions.items():
            if region.contains(position):
                return name
        return None
    
    def can_teleport(self, from_region: str, to_region: str) -> bool:
        """Check if teleportation is allowed between regions."""
        region = self.regions.get(from_region)
        if not region:
            return False
        return to_region in region.connected_to or to_region == from_region
    
    def get_spawn_point(self, region: str) -> Vector3:
        """Get spawn point for a region."""
        r = self.regions.get(region)
        if r:
            return r.spawn_point
        return self.regions["main"].spawn_point
    
    # ========== MOVEMENT ==========
    
    def move_toward(
        self,
        entity_id: str,
        target: Vector3,
        speed: float = 5.0
    ) -> Tuple[Vector3, bool]:
        """
        Move entity toward target at given speed.
        Returns (new_position, arrived).
        """
        entity = self.entities.get(entity_id)
        if not entity:
            return (Vector3(0, 0, 0), False)
        
        distance = entity.position.distance_to(target)
        
        if distance <= speed:
            # Arrived
            self.update_position(entity_id, target)
            return (target, True)
        
        # Move toward target
        new_pos = entity.position.move_toward(target, speed)
        self.update_position(entity_id, new_pos)
        return (new_pos, False)
    
    def teleport(
        self,
        entity_id: str,
        region: str,
        position: Optional[Vector3] = None
    ) -> bool:
        """Teleport entity to another region."""
        entity = self.entities.get(entity_id)
        if not entity:
            return False
        
        if region not in self.regions:
            return False
        
        # Use spawn point if no position specified
        if position is None:
            position = self.get_spawn_point(region)
        
        entity.position = position
        entity.region = region
        self.grid.update(entity_id, position, region)
        
        return True

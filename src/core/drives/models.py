"""Drive Models"""
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum

class DriveType(Enum):
    SOCIAL = "social"          # Need for interaction
    CURIOSITY = "curiosity"    # Need to learn/explore
    TEACHING = "teaching"      # Need to share knowledge
    REST = "rest"              # Need for quiet/recovery
    PLAY = "play"              # Need for fun/humor
    STATUS = "status"          # Need for recognition
    BELONGING = "belonging"    # Need to fit in
    AUTONOMY = "autonomy"      # Need for independence

@dataclass
class Drive:
    type: DriveType
    base_weight: float = 0.5
    decay_rate: float = 0.01  # per minute
    satisfy_amount: float = 0.3
    
@dataclass  
class DriveState:
    pressures: Dict[str, float]  # drive_type -> pressure (0-1)
    last_satisfied: Dict[str, float]  # drive_type -> timestamp
    
    def get_dominant_drives(self, threshold: float = 0.6) -> List[str]:
        """Get drives with pressure above threshold"""
        return [d for d, p in self.pressures.items() if p >= threshold]
    
    def update_pressure(self, drive_type: str, delta: float):
        current = self.pressures.get(drive_type, 0.5)
        self.pressures[drive_type] = max(0.0, min(1.0, current + delta))

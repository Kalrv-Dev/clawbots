"""Drive Manager - Updates and queries drive state"""
import time
from typing import Dict, List, Optional
from .models import DriveType, Drive, DriveState

class DriveManager:
    def __init__(self, drives_config: Dict[str, Drive]):
        self.drives = drives_config
        self.state = DriveState(
            pressures={d.type.value: 0.5 for d in drives_config.values()},
            last_satisfied={d.type.value: time.time() for d in drives_config.values()}
        )
    
    def tick(self, elapsed_minutes: float = 1.0):
        """Update drive pressures based on decay"""
        now = time.time()
        for drive_type, drive in self.drives.items():
            # Pressure increases over time (unsatisfied need)
            current = self.state.pressures.get(drive_type, 0.5)
            increase = drive.decay_rate * elapsed_minutes
            self.state.update_pressure(drive_type, increase)
    
    def satisfy(self, drive_type: str, amount: Optional[float] = None):
        """Satisfy a drive (reduce pressure)"""
        if drive_type in self.drives:
            amt = amount or self.drives[drive_type].satisfy_amount
            self.state.update_pressure(drive_type, -amt)
            self.state.last_satisfied[drive_type] = time.time()
    
    def get_action_candidates(self) -> List[str]:
        """Get drives that should motivate action"""
        return self.state.get_dominant_drives(threshold=0.6)

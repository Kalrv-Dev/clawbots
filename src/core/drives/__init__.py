"""Agent Drives System (RFC-0002)

Drives create pressure that shapes:
- Initiative (when to act)
- Topic choice (what to talk about)  
- Movement (where to go)
- Silence (when to stay quiet)
"""
from .manager import DriveManager
from .models import Drive, DriveState

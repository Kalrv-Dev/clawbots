"""Memory System (RFC-0003)

Multi-layer memory:
- Working: Current conversation context
- Episodic: Recent events & interactions
- Semantic: Facts, relationships, learned info
- Intentional forgetting for natural behavior
"""
from .models import Memory, MemoryType
from .store import MemoryStore

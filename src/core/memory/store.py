"""Memory Store - In-memory + persistence"""
from typing import List, Optional, Dict
from datetime import datetime
from .models import Memory, MemoryType

class MemoryStore:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.memories: Dict[str, Memory] = {}
        self.working_context: List[str] = []  # Recent memory IDs
    
    def add(self, memory: Memory) -> str:
        self.memories[memory.id] = memory
        if memory.type == MemoryType.WORKING:
            self.working_context.append(memory.id)
            # Keep working context limited
            if len(self.working_context) > 20:
                self.working_context.pop(0)
        return memory.id
    
    def get(self, memory_id: str) -> Optional[Memory]:
        return self.memories.get(memory_id)
    
    def search(
        self,
        query: str = None,
        memory_type: MemoryType = None,
        min_importance: float = 0.0,
        limit: int = 10
    ) -> List[Memory]:
        """Search memories with filters"""
        results = []
        for m in self.memories.values():
            if memory_type and m.type != memory_type:
                continue
            if m.importance < min_importance:
                continue
            if query and query.lower() not in m.content.lower():
                continue
            results.append(m)
        
        # Sort by importance * recency
        results.sort(key=lambda m: m.importance, reverse=True)
        return results[:limit]
    
    def get_working_context(self) -> List[Memory]:
        """Get current working memory"""
        return [self.memories[mid] for mid in self.working_context if mid in self.memories]
    
    def forget(self, current_time: datetime):
        """Run intentional forgetting"""
        to_forget = [
            mid for mid, m in self.memories.items()
            if m.should_forget(current_time) and m.type != MemoryType.SEMANTIC
        ]
        for mid in to_forget:
            del self.memories[mid]
            if mid in self.working_context:
                self.working_context.remove(mid)

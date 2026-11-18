"""
SoulMem Provider — Behavioral Memory (guides how to act).

Local memory storage using SQLite FTS5. A persistent layer that is always enabled.
This stage only defines the interface; the facade (memory_store.py) remains unchanged.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .types import Memory


class BaseSoulMem(ABC):
    """SoulMem behavioral-memory interface — persistent layer."""

    @abstractmethod
    def add(
        self,
        user_id: str,
        persona_id: str,
        content: str,
        category: str = "conversation",
        importance: float = 0.5,
        source_turn: int = 0,
    ) -> int:
        """Add a memory entry. Returns the memory ID."""
        ...

    @abstractmethod
    def search(
        self,
        user_id: str,
        persona_id: str,
        query: str,
        limit: int = 5,
    ) -> list[Memory]:
        """Search memories using FTS5 full-text search."""
        ...

    @abstractmethod
    def build_memory_context(
        self,
        user_id: str,
        persona_id: str,
        current_query: str = "",
        max_items: int = 8,
    ) -> Optional[str]:
        """Build a memory context string for prompt injection."""
        ...

    @abstractmethod
    def close(self):
        """Close the memory store."""
        ...

"""
Memory shared types.

Defines types such as Memory, SessionContext, etc.
These types are used by both the soulmem and evermemos providers.
The original modules (memory_store.py, evermemos_client.py) keep their own
definitions unchanged; import from here when migrating later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Memory:
    """A single memory entry (SoulMem)."""
    memory_id: int = 0
    user_id: str = ""
    persona_id: str = ""
    content: str = ""
    category: str = "conversation"  # conversation | fact | event | preference
    importance: float = 0.5
    source_turn: int = 0
    created_at: float = 0.0


@dataclass
class SessionContext:
    """
    EverMemOS session context (declarative memory).

    Loaded once at session start, contains relationship priors,
    user profile, episode summaries, and foresight.
    """
    user_id: str = ""
    persona_id: str = ""
    user_profile: str = ""
    episode_summary: str = ""
    foresight_text: str = ""
    relationship_depth: float = 0.0
    emotional_valence: float = 0.0
    trust_level: float = 0.0
    pending_foresight: float = 0.0
    has_history: bool = False
    raw_data: Optional[dict] = None

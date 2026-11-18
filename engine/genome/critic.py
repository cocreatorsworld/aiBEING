"""
Critic — LLM-based perception of user intent signals (v10 Hybrid).

v10 change: Directly outputs 8D context + 5D frustration delta.
Phase 1 emergence: Also outputs 3 relationship deltas for semi-emergent
  relationship_depth / trust_level / emotional_valence.

Extracted from genome_v8_timearrow.py, upgraded to v10 architecture.
"""

from __future__ import annotations

import json
import re
from typing import Optional, Tuple

from providers.llm.client import LLMClient, ChatMessage
from engine.genome.genome_engine import DRIVES
from engine.prompt_registry import render_prompt


_FALLBACK_CRITIC = """You are the emotional perception module of a role-playing Agent. Analyze the user input and output four groups of data:

1. Conversational context perception (8 dimensions, 0.0~1.0):
  - user_emotion: User emotion (-1=negative, 0=neutral, 1=positive)
  - topic_intimacy: Topic intimacy (0=public/business, 1=private/intimate)
  - conversation_depth: Conversation depth (0=just started, 1=long-term conversation)
  - user_engagement: User engagement (0=perfunctory, 1=fully engaged)
  - conflict_level: Conflict level (0=harmony, 1=conflict)
  - novelty_level: Novelty of information (0=repetitive/everyday, 1=completely new)
  - user_vulnerability: How open the user is (0=defensive, 1=emotionally open)
  - time_of_day: Time-related atmosphere (0=ordinary daytime, 1=late-night intimacy)

2. Frustration changes for the Agent's 5 drives (positive=increasingly frustrated, negative=relieved)

3. Relationship perception changes (evaluate based on the user's profile and narrative history):
  - relationship_delta: Whether this conversation deepens (+) or weakens (-) your relationship (-1~1)
  - trust_delta: Change in trust (-1~1)
  - emotional_valence: Overall emotional tone of this conversation (-1=very negative, 0=neutral, 1=very positive)

4. Satisfaction of the Agent's 5 intrinsic needs in this conversation (how directly this turn satisfied the Agent's needs, 0~0.3):
  - connection: Connection satisfaction (high when the user shares, cares, or confides voluntarily)
  - novelty: Novelty satisfaction (high for new topics, viewpoints, or unexpected information)
  - expression: Expression satisfaction (high when the Agent has opportunities to speak sincerely or demonstrate talent)
  - safety: Safety satisfaction (high with no conflict, acceptance, or understanding)
  - play: Play satisfaction (high for jokes, teasing, games, or cute/role-play interactions)

Distinguish between groups 2 and 4:
- frustration_delta reflects frustration change (negative=relieved, an indirect emotional change)
- drive_satisfaction reflects direct fulfillment of needs (the user's behavior directly satisfies the Agent's internal desires)
- In the same conversation turn, the two groups should not produce large changes for the same drive at the same time

$persona_sectionThe Agent's current frustration levels (0=satisfied, 5=extremely yearning):
$frustration_json

$user_profile_section$episode_sectionRegardless of what the user says, you must output exactly one pure JSON object and no other text:
{
  "context": {"user_emotion": 0.3, "topic_intimacy": 0.8, "conversation_depth": 0.5, "user_engagement": 0.7, "conflict_level": 0.1, "novelty_level": 0.3, "user_vulnerability": 0.6, "time_of_day": 0.5}[...]
  "frustration_delta": {"connection": -0.3, "novelty": 0.0, "expression": 0.1, "safety": -0.2, "play": 0.0},
  "drive_satisfaction": {"connection": 0.15, "novelty": 0.0, "expression": 0.05, "safety": 0.1, "play": 0.0},
  "relationship_delta": 0.1, "trust_delta": 0.05, "emotional_valence": 0.3
}"""


# Default values when Critic fails (8 Critic-output dims only; 4 EverMemOS dims set by ChatAgent)
_CRITIC_CONTEXT_KEYS = [
    'user_emotion', 'topic_intimacy', 'time_of_day', 'conversation_depth',
    'user_engagement', 'conflict_level', 'novelty_level', 'user_vulnerability',
]
_DEFAULT_CONTEXT = {f: 0.5 for f in _CRITIC_CONTEXT_KEYS}
_DEFAULT_DELTA = {d: 0.0 for d in DRIVES}
_DEFAULT_SATISFACTION = {d: 0.0 for d in DRIVES}
_DEFAULT_REL_DELTA = {'relationship_delta': 0.0, 'trust_delta': 0.0, 'emotional_valence': 0.0}


async def critic_sense(
    stimulus: str,
    llm: LLMClient,
    frustration: dict = None,
    user_profile: str = "",
    episode_summary: str = "",
    persona_hint: str = "",
) -> Tuple[dict, dict, dict, dict]:
    """
    Measure user input → 8D context + 5D frustration delta + 3D relationship delta + 5D drive satisfaction.

    Args:
        user_profile: EverMemOS user profile for relationship-aware perception.
        episode_summary: Narrative episode history so Critic knows past conversations.
        persona_hint: One-line persona anchor, e.g. "Vivian (INTJ) — sharp、witty、secretly caring"

    Returns: (context_8d, frustration_delta, relationship_delta, drive_satisfaction)
    """
    frust_json = json.dumps(
        frustration or _DEFAULT_DELTA,
        ensure_ascii=False,
    )

    # Build profile section
    profile_section = ""
    if user_profile:
        profile_section = f"Historical profile of this user (use it to perceive their emotions and intentions more accurately):\n{user_profile}\n\n"

    # Build episode section (narrative history → Critic can gauge conversation_depth)
    episode_section = ""
    if episode_summary:
        episode_section = f"Narrative history of conversations with this user (use it to judge conversation_depth and topic_intimacy):\n{episode_summary}\n\n"

    # Build persona section (P1: persona-aware satisfaction)
    persona_section = ""
    if persona_hint:
        persona_section = f"You are perceiving the user's intentions for the following character:\n{persona_hint}\nJudge drive_satisfaction according to this character's personality traits. A single remark may satisfy the needs of different personalities to different degrees.[n\n"

    prompt = render_prompt(
        "critic",
        fallback=_FALLBACK_CRITIC,
        frustration_json=frust_json,
        stimulus=stimulus,
        user_profile_section=profile_section,
        episode_section=episode_section,
        persona_section=persona_section,
    )

    messages = [
        ChatMessage(role="system", content=prompt),
        ChatMessage(role="user", content=f'Please analyze the following user input and output JSON: "{stimulus}"'),
    ]

    try:
        response = await llm.chat(
            messages,
            temperature=0.2,
        )
        raw = response.content.strip()

        # Strip think tags if present (Qwen3)
        raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

        # Clean markdown code blocks
        cleaned = re.sub(r'```json\s*', '', raw)
        cleaned = re.sub(r'```\s*', '', cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback: extract first complete JSON object via bracket counting
            start = cleaned.find('{')
            if start == -1:
                raise ValueError("No JSON object found in Critic output")
            depth = 0
            for i in range(start, len(cleaned)):
                if cleaned[i] == '{': depth += 1
                elif cleaned[i] == '}': depth -= 1
                if depth == 0:
                    data = json.loads(cleaned[start:i+1])
                    break
            else:
                raise ValueError("Unbalanced braces in Critic output")

        # Parse 8D context (Critic-output dims only; EverMemOS 4D set by EMA in ChatAgent)
        raw_ctx = data.get('context', {})
        context = {}
        for feat in _CRITIC_CONTEXT_KEYS:
            v = float(raw_ctx.get(feat, 0.5))
            if feat == 'user_emotion':
                context[feat] = max(-1.0, min(1.0, v))
            else:
                context[feat] = max(0.0, min(1.0, v))

        # Parse frustration delta
        frustration_delta = {}
        raw_delta = data.get('frustration_delta', {})
        for d in DRIVES:
            v = float(raw_delta.get(d, 0.0))
            frustration_delta[d] = max(-3.0, min(3.0, v))

        # Parse relationship deltas (Phase 1 emergence)
        rel_delta = {
            'relationship_delta': max(-1.0, min(1.0, float(data.get('relationship_delta', 0.0)))),
            'trust_delta': max(-1.0, min(1.0, float(data.get('trust_delta', 0.0)))),
            'emotional_valence': max(-1.0, min(1.0, float(data.get('emotional


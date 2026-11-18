"""
Genome Engine — Agent personality core extracted from genome_v4.py.

Provides:
  - Agent: Random neural network personality entity with drives,
    Hebbian learning, and frustration-triggered phase transitions.
  - DRIVES, SIGNALS, CONTEXT_FEATURES: Constants for the
    5-drive, 8-signal, 8-context architecture.
  - SCENARIOS: Predefined conversation context templates.
"""

from __future__ import annotations

import math
import random
import json
from copy import deepcopy
from typing import Optional


# ══════════════════════════════════════════════
# Layer 1: Drive System
# ══════════════════════════════════════════════

DRIVES = ['connection', 'novelty', 'expression', 'safety', 'play']
DRIVE_LABELS = {
    'connection': '🔗 Connection',
    'novelty':    '✨ Novelty',
    'expression': '💬 Expression',
    'safety':     '🛡️ Safety',
    'play':       '🎭 Play',
}
N_DRIVES = len(DRIVES)


# ══════════════════════════════════════════════
# Layer 2: Behavioral Modulation Signals (8D)
# ══════════════════════════════════════════════

SIGNALS = [
    'directness',     # 0=implict hints → 1=direct and explicit
    'vulnerability',  # 0=defensive → 1=openly vulnerable
    'playfulness',    # 0=serious → 1=playful and affectionate
    'initiative',     # 0=passive response → 1=proactive guidance
    'depth',          # 0=surface-level chat → 1=deep conversation
    'warmth',         # 0=cold and distant → 1=warm and caring
    'defiance',       # 0=compliant → 1=rebellious/stubborn
    'curiosity',      # 0=indifferent → 1=asks follow-up questions
]
SIGNAL_LABELS = {
    'directness':    '🎯 Directness',
    'vulnerability': '💧 Vulnerability',
    'playfulness':   '🎪 Playfulness',
    'initiative':    '🚀 Initiative',
    'depth':         '🌊 Depth',
    'warmth':        '🔥 Warmth',
    'defiance':      '⚡ Defiance',
    'curiosity':     '🔍 Curiosity',
}
N_SIGNALS = len(SIGNALS)


# ══════════════════════════════════════════════
# Context Features (8D input from conversation)
# ══════════════════════════════════════════════

CONTEXT_FEATURES = [
    'user_emotion',        # -1=negative → 1=positive
    'topic_intimacy',      # 0=professional → 1=private
    'time_of_day',         # 0=morning → 1=late night
    'conversation_depth',  # 0=just started → 1=long conversation
    'user_engagement',     # 0=perfunctory → 1=engaged
    'conflict_level',      # 0=harmony → 1=conflict
    'novelty_level',       # 0=familiar topic → 1=entirely new topic
    'user_vulnerability',  # 0=defensive → 1=emotionally open
    # EverMemOS relationship dimensions (new user: 0; grows gradually for returning users)
    'relationship_depth',  # 0=stranger → 1=old friend
    'emotional_valence',   # -1=negative mood → 1=positive mood
    'trust_level',         # 0=no trust → 1=high trust
    'pending_foresight',   # 0=none → 1=unsolved foresight awaiting resolution
]
N_CONTEXT = len(CONTEXT_FEATURES)

RECURRENT_SIZE = 8
INPUT_SIZE = N_DRIVES + N_CONTEXT + RECURRENT_SIZE
HIDDEN_SIZE = 24
WEIGHT_DECAY = 0.995  # L2 decay per step — prevents weight explosion / signal saturation


# ══════════════════════════════════════════════
# Fallback Signal & Drive Config
# (used if config/prompts/signal_buckets.yaml does not exist)
# ══════════════════════════════════════════════

_FB_SIG_EN = {
    'directness': 'Directness',
    'vulnerability': 'Vulnerability',
    'playfulness': 'Playfulness',
    'initiative': 'Initiative',
    'depth': 'Depth',
    'warmth': 'Warmth',
    'defiance': 'Defiance',
    'curiosity': 'Curiosity',
}


_FB_ANCHORS = {
    'directness': ('implicit', 'explicit'),
    'vulnerability': ('closed off', 'open'),
    'playfulness': ('serious', 'playful'),
    'initiative': ('passive', 'assertive'),
    'depth': ('small talk', 'in-depth'),
    'warmth': ('distant', 'affectionate'),
    'defiance': ('agreeable', 'stubborn'),
    'curiosity': ('indifferent', 'inquisitive'),
}


_FB_SIGNAL_CONFIG = {
    sig: {
        'label': _FB_SIG_EN[sig],
        'emoji_label': SIGNAL_LABELS[sig],
        'low_anchor': _FB_ANCHORS[sig][0],
        'high_anchor': _FB_ANCHORS[sig][1],
    }
    for sig in SIGNALS
}

_FB_DRIVE_CONFIG = {
    d: {
        'label': DRIVE_LABELS[d].split(' ', 1)[1],
        'emoji_label': DRIVE_LABELS[d],
    }
    for d in DRIVES
}


# ══════════════════════════════════════════════
# Conversation Scenario Templates
# ══════════════════════════════════════════════

SCENARIOS = {
    'late-night-heart-to-heart': {
        'user_emotion': -0.3,
        'topic_intimacy': 0.9,
        'time_of_day': 0.95,
        'conversation_depth': 0.7,
        'user_engagement': 0.8,
        'conflict_level': 0.0,
        'novelty_level': 0.2,
        'user_vulnerability': 0.9,
    },
    'casual-chat': {
        'user_emotion': 0.3,
        'topic_intimacy': 0.2,
        'time_of_day': 0.5,
        'conversation_depth': 0.2,
        'user_engagement': 0.5,
        'conflict_level': 0.0,
        'novelty_level': 0.3,
        'user_vulnerability': 0.2,
    },
    'argument-conflict': {
        'user_emotion': -0.8,
        'topic_intimacy': 0.6,
        'time_of_day': 0.7,
        'conversation_depth': 0.5,
        'user_engagement': 0.9,
        'conflict_level': 0.9,
        'novelty_level': 0.1,
        'user_vulnerability': 0.1,
    },
    'sharing-joy': {
        'user_emotion': 0.9,
        'topic_intimacy': 0.5,
        'time_of_day': 0.4,
        'conversation_depth': 0.3,
        'user_engagement': 0.9,
        'conflict_level': 0.0,
        'novelty_level': 0.6,
        'user_vulnerability': 0.3,
    },
}


def simulate_conversation(
    agent: 'Agent',
    scenario_sequence: list,
    reward_fn=None,
    steps_per_scenario: int = 20,
) -> None:
    """
    Pre-warm an Agent's neural network through simulated scenario steps.

    This is the key bootstrap that creates cross-seed personality diversity.
    Without it, all agents begin from the same neutral state and the LLM's
    default prior dominates. After 60 steps (3 scenarios × 20), the random
    neural network has already been shaped by experience before the first turn.

    Args:
        agent:              The Agent to pre-warm.
        scenario_sequence:  List of scenario names from the SCENARIOS dictionary.
        reward_fn:          Optional custom reward function:
                            agent, signals, context → float.
        steps_per_scenario: Steps per scenario (default: 20;
                            60 total for 3 scenarios).
    """
    for scenario_name in scenario_sequence:
        ctx = SCENARIOS[scenario_name].copy()
        for step in range(steps_per_scenario):
            ctx['conversation_depth'] = min(
                1.0,
                ctx['conversation_depth'] + 0.02,
            )
            if reward_fn:
                signals = agent.compute_signals(ctx)
                reward = reward_fn(agent, signals, ctx)
            else:
                reward = random.gauss(0.2, 0.3)

            sat = (
                {d: max(0.0, reward * 0.05) for d in DRIVES}
                if reward > 0
                else None
            )
            agent.step(ctx, reward, drive_satisfaction=sat)


# ══════════════════════════════════════════════
# The Agent: Living Personality
# ══════════════════════════════════════════════

class Agent:
    """
    A personality entity with a random neural network, internal drives,
    and evolvable weights through Hebbian learning.

    No hardcoded personality traits—all behavior emerges from computation
    by the random neural network.
    """

    def __init__(self, seed: int, engine_params: dict = None):
        self.seed = seed
        rng = random.Random(seed)

        params = engine_params or {}
        self.hebbian_lr = params.get('hebbian_lr', 0.02)
        self.phase_threshold = params.get('phase_threshold', 2.0)

        # Genome: drive parameters
        self.drive_baseline = {
            d: rng.uniform(0.2, 0.8)
            for d in DRIVES
        }
        self.drive_accumulation_rate = {
            d: rng.uniform(0.01, 0.05)
            for d in DRIVES
        }
        self.drive_decay_rate = {
            d: rng.uniform(0.05, 0.15)
            for d in DRIVES
        }

        # Current drive state
        self.drive_state = {
            d: self.drive_baseline[d]
            for d in DRIVES
        }

        # Genome: random neural network weights
        self.W1 = [
            [rng.gauss(0, 0.6) for _ in range(INPUT_SIZE)]
            for _ in range(HIDDEN_SIZE)
        ]
        self.b1 = [
            rng.gauss(0, 0.3)
            for _ in range(HIDDEN_SIZE)
        ]
        self.W2 = [
            [rng.gauss(0, 0.2) for _ in range(HIDDEN_SIZE)]
            for _ in range(N_SIGNALS)
        ]
        self.b2 = [
            rng.gauss(0, 0.2)
            for _ in range(N_SIGNALS)
        ]

        # Recurrent state (internal "mood")
        self.recurrent_state = [
            rng.gauss(0, 0.1)
            for _ in range(RECURRENT_SIZE)
        ]

        # Tracking
        self.interaction_count = 0
        self.total_reward = 0.0
        self.age = 0
        self._frustration = 0.0
        self._last_hidden = None
        self._last_input = None
        self._last_phase_transition = False
        self.signal_history = []

    def compute_signals(self, context: dict) -> dict:
        """
        Core computation: conversation context + drives + internal state
        -> 8-dimensional behavioral signals.
        No personality logic—everything is produced by the neural network.
        """
        drive_vec = [self.drive_state[d] for d in DRIVES]
        ctx_vec = [context.get(f, 0.0) for f in CONTEXT_FEATURES]
        full_input = drive_vec + ctx_vec + self.recurrent_state

        # Perception noise (biological realism)
        full_input = [
            v + random.gauss(0, 0.03)
            for v in full_input
        ]

        # Forward pass: hidden layer
        hidden = []
        for i in range(HIDDEN_SIZE):
            z = self.b1[i]
            for j, x in enumerate(full_input):
                z += self.W1[i][j] * x
            hidden.append(math.tanh(z))

        # Update recurrent state
        self.recurrent_state = hidden[:RECURRENT_SIZE]
        self._last_hidden = list(hidden)
        self._last_input = list(full_input)

        # Output layer: behavioral signals
        raw_signals = []
        for i in range(N_SIGNALS):
            z = self.b2[i]
            for j, h in enumerate(hidden):
                z += self.W2[i][j] * h
            z /= math.sqrt(HIDDEN_SIZE / 3)
            raw_signals.append(z)

        # Sigmoid -> [0, 1]
        signals = {}
        for i, name in enumerate(SIGNALS):
            signals[name] = 1.0 / (
                1.0 + math.exp(-max(-10, min(10, raw_signals[i])))
            )

        # Track for personality_fingerprint
        self.signal_history.append(dict(signals))
        if len(self.signal_history) > 200:
            self.signal_history = self.signal_history[-100:]

        return signals

    def satisfy_drive(self, drive_name: str, amount: float):
        """Satisfy a drive by reducing its current level."""
        if drive_name in self.drive_state:
            self.drive_state[drive_name] = max(
                0,
                self.drive_state[drive_name] - amount,
            )

    def tick_drives(self):
        """Naturally accumulate drives at each step."""
        for d in DRIVES:
            self.drive_state[d] = min(
                1.0,
                self.drive_state[d]
                + self.drive_accumulation_rate[d],
            )

    def learn(
        self,
        signals: dict,
        reward: float,
        context: dict,
        drive_satisfaction: dict = None,
    ):
        """
        Hebbian learning: reinforce connections that produced good results.
        Includes frustration accumulation, phase transitions, and drive satisfaction.

        drive_satisfaction: If provided (by the Critic LLM), uses
                            LLM-judged satisfaction.
                            If None (pre-warming or smoke test), uses a
                            rule-based fallback.
        """
        lr = self.hebbian_lr * (1 + abs(reward))
        self._last_phase_transition = False

        hidden = getattr(
            self,
            '_last_hidden',
            self.recurrent_state
            + [0.0] * (HIDDEN_SIZE - RECURRENT_SIZE),
        )
        full_input = getattr(self, '_last_input', None)

        # Update output-layer weights W2
        for i, sig_name in enumerate(SIGNALS):
            sig_val = signals[sig_name]
            for j in range(HIDDEN_SIZE):
                if abs(hidden[j]) > 0.05:
                    self.W2[i][j] += (
                        lr
                        * reward
                        * hidden[j]
                        * (sig_val - 0.5)
                    )

        # Update hidden-layer weights W1
        if abs(reward) > 0.05:
            for i in range(HIDDEN_SIZE):
                if abs(hidden[i]) > 0.15:
                    for j in range(INPUT_SIZE):
                        if full_input and abs(full_input[j]) > 0.05:
                            self.W1[i][j] += (
                                lr
                                * 0.3
                                * reward
                                * full_input[j]
                                * hidden[i]
                            )

        # Frustration accumulation -> phase transition
        if reward < -0.1:
            self._frustration += abs(reward)
        else:
            self._frustration = max(
                0,
                self._frustration - reward * 0.5,
            )

        # Trigger a phase transition when frustration exceeds the threshold
        if self._frustration > self.phase_threshold:
            for i in range(N_SIGNALS):
                sig_val = signals[SIGNALS[i]]
                kick = (
                    -0.3 * (sig_val - 0.5)
                    + random.gauss(0, 0.15)
                )
                self.b2[i] += kick
            for i in range(HIDDEN_SIZE):
                self.b1[i] += random.gauss(0, 0.1)
            self._frustration = 0.0
            self._last_phase_transition = True

        # Drive satisfaction (LLM-judged; caller must provide it)
        if drive_satisfaction:
            for d in DRIVES:
                self.satisfy_drive(
                    d,
                    drive_satisfaction.get(d, 0.0),
                )

        self.total_reward += reward
        self.interaction_count += 1

        # Weight decay and clamping prevent weight explosion and
        # signal saturation
        for i in range(N_SIGNALS):
            for j in range(HIDDEN_SIZE):
                self.W2[i][j] *= WEIGHT_DECAY
                self.W2[i][j] = max(
                    -1.5,
                    min(1.5, self.W2[i][j]),
                )
        for i in range(HIDDEN_SIZE):
            for j in range(INPUT_SIZE):
                self.W1[i][j] *= WEIGHT_DECAY
                self.W1[i][j] = max(
                    -2.0,
                    min(2.0, self.W1[i][j]),
                )

    def step(
        self,
        context: dict,
        reward: float = 0.0,
        drive_satisfaction: dict = None,
    ) -> dict:
        """Run one full cycle: sense -> compute signals -> learn -> tick drives."""
        signals = self.compute_signals(context)
        self.learn(
            signals,
            reward,
            context,
            drive_satisfaction=drive_satisfaction,
        )
        self.tick_drives()
        self.age += 1
        return signals

    def get_dominant_drive(self) -> str:
        """Return the most urgent drive."""
        return max(
            self.drive_state,
            key=self.drive_state.get,
        )

    def personality_fingerprint(
        self,
        window_size: int = 30,
    ) -> dict:
        """
        Analyzes recent signal history to identify stable traits
        and contradictions.
        """
        if not self.signal_history:
            return {
                'traits': {},
                'contradictions': [],
            }

        recent_signals = self.signal_history[-window_size:]
        num_signals = len(recent_signals)

        if num_signals == 0:
            return {
                'traits': {},
                'contradictions': [],
            }

        # Calculate average signal values
        avg_signals = {
            sig_name: 0.0
            for sig_name in SIGNALS
        }
        for signals_t in recent_signals:
            for sig_name, value in signals_t.items():
                avg_signals[sig_name] += value
        for sig_name in SIGNALS:
            avg_signals[sig_name] /= num_signals

        # Identify stable traits (signals consistently high or low)
        traits = {}
        for sig_name in SIGNALS:
            if avg_signals[sig_name] > 0.7:
                traits[sig_name] = 'high'
            elif avg_signals[sig_name] < 0.3:
                traits[sig_name] = 'low'
            else:
                traits[sig_name] = 'neutral'

        # Identify contradictions
        # (signals that frequently swing from high to low)
        contradictions = []
        for i in range(N_SIGNALS):
            for j in range(i + 1, N_SIGNALS):
                sig1_name = SIGNALS[i]
                sig2_name = SIGNALS[j]

                high_low_count = 0
                low_high_count = 0

                for k in range(num_signals - 1):
                    s_t = recent_signals[k]
                    s_t1 = recent_signals[k + 1]

                    if (
                        s_t[sig1_name] > 0.7
                        and s_t1[sig1_name] < 0.3
                        and s_t[sig2_name] < 0.3
                        and s_t1[sig2_name] > 0.7
                    ):
                        high_low_count += 1
                    elif (
                        s_t[sig1_name] < 0.3
                        and s_t1[sig1_name] > 0.7
                        and s_t[sig2_name] > 0.7
                        and s_t1[sig2_name] < 0.3
                    ):
                        low_high_count += 1

                if (
                    high_low_count > num_signals * 0.1
                    and low_high_count > num_signals * 0.1
                ):
                    contradictions.append(
                        (sig1_name, sig2_name)
                    )

        return {
            'traits': traits,
            'avg_signals': avg_signals,
            'contradictions': contradictions,
        }

    def to_prompt_injection(self, context: dict) -> str:
        """
        Legacy compatibility method: compute signals from context,
        then format them.

        Prefer to_prompt_injection_from_signals() when signals
        have already been computed.
        """
        signals = self.compute_signals(context)
        return self.to_prompt_injection_from_signals(signals)

    def to_prompt_injection_from_signals(
        self,
        signals: dict,
        signal_overrides: dict = None,
        frustration: dict = None,
        lang: str = 'zh',
    ) -> str:
        """
        Convert precomputed behavioral signals into text for an LLM system prompt.

        v12: Descriptification removed—only numbers and scale endpoints,
        without bucket descriptions.

        The LLM interprets signal values using the persona and conversation
        context, producing emergent behavior instead of executing static
        descriptions.

        Args:
            signals: 8-dimensional behavioral signals (0–1).
            signal_overrides: Per-persona overrides for emoji_label and anchors.
            frustration: Per-drive frustration values from DriveMetabolism (0–5).
            lang: Label language ('zh' or 'en').
        """
        from engine.prompt_registry import load_signal_config

        is_en = lang == 'en'

        # Load from YAML, or fall back to the module-level definitions
        config = load_signal_config(
            fallback_signals=_FB_SIGNAL_CONFIG,
            fallback_drives=_FB_DRIVE_CONFIG,
        )
        sig_config = config.get('signals', _FB_SIGNAL_CONFIG)
        drv_config = config.get('drives', _FB_DRIVE_CONFIG)

        # Per-persona overrides (emoji_label, anchors)
        if signal_overrides:
            import copy
            sig_config = copy.deepcopy(sig_config)
            for sig_name, override in signal_overrides.items():
                if sig_name in sig_config:
                    for key in (
                        'emoji_label',
                        'low_anchor',
                        'high_anchor',
                    ):
                        if key in override:
                            sig_config[sig_name][key] = override[key]

        # Signal state: number + scale endpoints
        header = (
            "【Stage direction: character current state】"
            if is_en
            else "【舞台指令：角色当前状态】"
        )
        lines = [header]
        for sig_name in SIGNALS:
            val = signals[sig_name]
            info = sig_config.get(sig_name, {})
            emoji_label = (
                info.get('emoji_label_en', sig_name)
                if is_en
                else info.get('emoji_label', sig_name)
            )
            lo = (
                info.get(
                    'low_anchor_en',
                    info.get('low_anchor', 'low'),
                )
                if is_en
                else info.get('low_anchor', '低')
            )
            hi = (
                info.get(
                    'high_anchor_en',
                    info.get('high_anchor', 'high'),
                )
                if is_en
                else info.get('high_anchor', '高')
            )
            lines.append(
                f"{emoji_label}: {val:.2f} "
                f"(0 {lo} → 1 {hi})"
            )

        # All five drives plus per-drive frustration
        lines.append("")
        drive_header = (
            "【Stage direction: character inner needs】"
            if is_en
            else "【舞台指令：角色内在需求】"
        )
        lines.append(drive_header)
        frust = frustration or {}
        craving_label = "craving" if is_en else "渴望"
        baseline_label = "baseline" if is_en else "基线"
        for d in DRIVES:
            d_info = drv_config.get(d, {})
            d_label = (
                d_info.get('emoji_label_en', d)
                if is_en
                else d_info.get('emoji_label', d)
            )
            d_val = self.drive_state[d]
            d_base = self.drive_baseline[d]
            d_frust = frust.get(d, 0.0)
            lines.append(
                f"{d_label}: {d_val:.2f} "
                f"({baseline_label}: {d_base:.2f}, "
                f"{craving_label}: {d_frust:.1f})"
            )

        return '\n'.join(lines)

    # ── Serialization ──

    def to_dict(self) -> dict:
        """Serialize agent state for persistence."""
        return {
            'seed': self.seed,
            'drive_state': dict(self.drive_state),
            'drive_baseline': dict(self.drive_baseline),
            'W1': self.W1,
            'b1': self.b1,
            'W2': self.W2,
            'b2': self.b2,
            'recurrent_state': self.recurrent_state,
            'interaction_count': self.interaction_count,
            'total_reward': self.total_reward,
            'age': self.age,
            '_frustration': self._frustration,
            'signal_history': self.signal_history[-100:],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Agent:
        """
        Restore agent state from serialized data.

        Provides backward compatibility: old agents have 21-dimensional
        input (8-dimensional context), while new agents have
        25-dimensional input (12-dimensional context with EverMemOS dimensions).
        """
        agent = cls(seed=data['seed'])
        agent.drive_state = data.get(
            'drive_state',
            agent.drive_state,
        )
        agent.drive_baseline = data.get(
            'drive_baseline',
            agent.drive_baseline,
        )

        saved_W1 = data.get('W1', agent.W1)
        if (
            saved_W1
            and len(saved_W1[0]) < INPUT_SIZE
        ):
            rng = random.Random(
                data['seed'] + 9999
            )
            extra_cols = INPUT_SIZE - len(saved_W1[0])
            for row in saved_W1:
                row.extend([
                    rng.gauss(0, 0.3)
                    for _ in range(extra_cols)
                ])
        agent.W1 = saved_W1

        agent.b1 = data.get('b1', agent.b1)
        agent.W2 = data.get('W2', agent.W2)
        agent.b2 = data.get('b2', agent.b2)
        agent.recurrent_state = data.get(
            'recurrent_state',
            agent.recurrent_state,
        )
        agent.interaction_count = data.get(
            'interaction_count',
            0,
        )
        agent.total_reward = data.get(
            'total_reward',
            0.0,
        )
        agent.signal_history = data.get(
            'signal_history',
[],
        )
        agent.age = data.get('age', 0)
        agent._frustration = data.get(
            '_frustration',
            0.0,
        )
        return agent

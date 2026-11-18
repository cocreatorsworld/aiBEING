"""
PromptRegistry — Loads prompt templates and signal configurations from config/prompts/.

Uses string.Template ($variable) to avoid conflicts with JSON braces.
Falls back to hardcoded defaults if configuration files do not exist.
"""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Optional

import yaml

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_cache: dict[str, str] = {}
_signal_cache: Optional[dict] = None


def load_prompt(name: str, fallback: str = "") -> str:
    """Load a prompt template from config/prompts/{name}.md and cache it in memory."""
    if name in _cache:
        return _cache[name]
    path = _PROMPTS_DIR / f"{name}.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = fallback
    _cache[name] = text
    return text


def render_prompt(name: str, fallback: str = "", **kwargs) -> str:
    """Load a prompt template and substitute $variables.

    Uses safe_substitute: unknown $variables remain unchanged instead of raising KeyError.
    """
    tmpl = load_prompt(name, fallback)
    return Template(tmpl).safe_substitute(**kwargs)


def load_signal_config(fallback_signals: dict = None, fallback_drives: dict = None) -> dict:
    """Load signal_buckets.yaml → structured configuration containing labels, buckets, and drives.

    Returns:
        {
            'signals': {
                'directness': {
                    'label': 'Directness',
                    'emoji_label': '🎯 Directness',
                    'buckets': [(0.0, 0.33, 'Direct and blunt speech...'), ...],
                },
                ...
            },
            'drives': {
                'connection': {'label': 'Connection', 'emoji_label': '🔗 Connection'},
                ...
            },
        }
    """
    global _signal_cache
    if _signal_cache is not None:
        return _signal_cache

    path = _PROMPTS_DIR / "signal_buckets.yaml"
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        result = {'signals': {}, 'drives': {}}

        # Parse signals
        for sig_name, sig_data in raw.get('signals', {}).items():
            result['signals'][sig_name] = {
                'label': sig_data.get('label', sig_name),
                'emoji_label': sig_data.get('emoji_label', sig_name),
                'emoji_label_en': sig_data.get('emoji_label_en', sig_name),
                'low_anchor': sig_data.get('low_anchor', '低'),
                'high_anchor': sig_data.get('high_anchor', '高'),
                'low_anchor_en': sig_data.get('low_anchor_en', 'low'),
                'high_anchor_en': sig_data.get('high_anchor_en', 'high'),
                'buckets': [
                    (b['low'], b['high'], b['desc'])
                    for b in sig_data.get('buckets', [])
                ],
            }

        # Parse drives
        for drv_name, drv_data in raw.get('drives', {}).items():
            result['drives'][drv_name] = {
                'label': drv_data.get('label', drv_name),
                'emoji_label': drv_data.get('emoji_label', drv_name),
                'emoji_label_en': drv_data.get('emoji_label_en', drv_name),
            }

        _signal_cache = result
        return result

    # Fallback: build from hardcoded values
    result = {'signals': {}, 'drives': {}}
    if fallback_signals:
        result['signals'] = fallback_signals
    if fallback_drives:
        result['drives'] = fallback_drives
    _signal_cache = result
    return result


def reload():
    """Clear all caches — call this after editing prompt files at runtime."""
    global _signal_cache
    _cache.clear()
    _signal_cache = None

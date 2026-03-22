"""AI Provider Router - Routes to AI or falls back to Python heuristics.

Pattern: Try AI provider first (Claude, Gemini, etc.), fall back to
local Python-based analysis if AI is unavailable.
"""
from config import config


def _get_provider():
    """Get the configured AI provider, or None if unavailable."""
    provider = config.AI_PROVIDER.lower()
    if provider == "claude":
        try:
            from ai_providers.claude_provider import ClaudeProvider
            return ClaudeProvider()
        except Exception:
            return None
    return None


def route_analysis(text: str) -> dict:
    """Analyze text for AI patterns. AI-first, Python fallback."""
    provider = _get_provider()
    if provider:
        try:
            return provider.analyze(text)
        except Exception:
            pass
    # Fallback to Python heuristics
    from utils.detector import detect_ai_patterns
    return detect_ai_patterns(text)


def route_rewrite(text: str, voice_profile_id: int = None) -> dict:
    """Rewrite text to sound human. AI-first, Python fallback."""
    provider = _get_provider()
    if provider:
        try:
            return provider.rewrite(text, voice_profile_id)
        except Exception:
            pass
    # Fallback to Python heuristics
    from utils.rewriter import heuristic_rewrite
    return heuristic_rewrite(text, voice_profile_id)

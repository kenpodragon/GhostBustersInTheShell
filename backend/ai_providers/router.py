"""AI Provider Router - Routes to AI or falls back to Python heuristics.

Pattern: Try AI provider first (Claude, Gemini, etc.), fall back to
local Python-based analysis if AI is unavailable.

Runtime state: AI can be auto-disabled on token/rate errors and
re-enabled on next startup if the user's saved preference is 'on'.
"""
from config import config

# Runtime flag — set False on token/rate errors, checked on each request.
# Reset to True on startup if DB setting ai_enabled=True and health check passes.
_ai_runtime_available = True
_ai_runtime_error = None  # Last error message that caused runtime disable


def _get_settings():
    """Read AI settings from DB. Returns dict with ai_enabled, ai_provider."""
    try:
        from db import query_one
        row = query_one("SELECT ai_enabled, ai_provider FROM settings WHERE id = 1")
        if row:
            return dict(row)
    except Exception:
        pass
    return {"ai_enabled": True, "ai_provider": config.AI_PROVIDER}


def _get_provider(provider_name: str = None):
    """Get the configured AI provider, or None if unavailable."""
    if not provider_name:
        provider_name = config.AI_PROVIDER
    provider_name = provider_name.lower()
    if provider_name == "none":
        return None
    if provider_name == "claude":
        try:
            from ai_providers.claude_provider import ClaudeProvider
            p = ClaudeProvider()
            if not p.is_available():
                return None
            return p
        except Exception:
            return None
    return None


def _is_token_error(exc: Exception) -> bool:
    """Check if an exception indicates a token/rate/billing error."""
    msg = str(exc).lower()
    token_indicators = [
        "token", "rate limit", "rate_limit", "quota", "billing",
        "exceeded", "capacity", "overloaded", "too many requests",
    ]
    return any(ind in msg for ind in token_indicators)


def _disable_runtime(error_msg: str):
    """Disable AI at runtime (recoverable on restart)."""
    global _ai_runtime_available, _ai_runtime_error
    _ai_runtime_available = False
    _ai_runtime_error = error_msg
    print(f"[AI Router] Runtime disabled: {error_msg}")


def get_ai_status() -> dict:
    """Get current AI status for API/frontend consumption."""
    settings = _get_settings()
    provider = _get_provider(settings.get("ai_provider"))
    return {
        "ai_enabled": settings.get("ai_enabled", True),
        "ai_provider": settings.get("ai_provider", "claude"),
        "ai_runtime_available": _ai_runtime_available,
        "ai_runtime_error": _ai_runtime_error,
        "ai_cli_installed": provider is not None if provider else False,
    }


def should_use_ai(use_ai_param: bool = None) -> bool:
    """Determine whether to use AI for this request.

    Priority:
    1. Explicit use_ai parameter (per-request override)
    2. Runtime availability (auto-disabled on errors)
    3. DB setting (user's saved preference)
    """
    # Per-request override
    if use_ai_param is not None:
        if use_ai_param and not _ai_runtime_available:
            # User explicitly wants AI but it's runtime-disabled.
            # Re-check availability (maybe it recovered).
            startup_health_check()
        return use_ai_param and _ai_runtime_available

    # Check DB setting
    settings = _get_settings()
    if not settings.get("ai_enabled", True):
        return False

    return _ai_runtime_available


def route_analysis(text: str, use_ai: bool = None) -> dict:
    """Analyze text for AI patterns. AI-first, Python fallback."""
    if should_use_ai(use_ai):
        settings = _get_settings()
        provider = _get_provider(settings.get("ai_provider"))
        if provider:
            try:
                result = provider.analyze(text)
                result["_analysis_mode"] = "ai"
                return result
            except Exception as e:
                if _is_token_error(e):
                    _disable_runtime(str(e))
                # Fall through to heuristics

    # Fallback to Python heuristics
    from utils.detector import detect_ai_patterns
    result = detect_ai_patterns(text)
    result["_analysis_mode"] = "heuristic"
    return result


def route_rewrite(text: str, voice_profile_id: int = None, use_ai: bool = None) -> dict:
    """Rewrite text to sound human. AI-first, Python fallback."""
    if should_use_ai(use_ai):
        settings = _get_settings()
        provider = _get_provider(settings.get("ai_provider"))
        if provider:
            try:
                result = provider.rewrite(text, voice_profile_id)
                result["_analysis_mode"] = "ai"
                return result
            except Exception as e:
                if _is_token_error(e):
                    _disable_runtime(str(e))
                # Fall through to heuristics

    # Fallback to Python heuristics
    from utils.rewriter import heuristic_rewrite
    result = heuristic_rewrite(text, voice_profile_id)
    result["_analysis_mode"] = "heuristic"
    return result


def startup_health_check():
    """Run on app startup. Re-enable AI if user preference is on and CLI is healthy."""
    global _ai_runtime_available, _ai_runtime_error
    settings = _get_settings()
    if not settings.get("ai_enabled", True):
        _ai_runtime_available = False
        _ai_runtime_error = "Disabled by user setting"
        print("[AI Router] AI disabled by user setting")
        return

    provider = _get_provider(settings.get("ai_provider"))
    if provider:
        health = provider.health_check()
        if health.get("available"):
            _ai_runtime_available = True
            _ai_runtime_error = None
            print(f"[AI Router] AI available: {settings['ai_provider']} ({health.get('version', 'unknown')})")
        else:
            _ai_runtime_available = False
            _ai_runtime_error = health.get("error", "CLI not available")
            print(f"[AI Router] AI unavailable: {_ai_runtime_error}")
    else:
        _ai_runtime_available = False
        _ai_runtime_error = f"Provider '{settings.get('ai_provider')}' not found or CLI not installed"
        print(f"[AI Router] {_ai_runtime_error}")

"""MCP Server - Exposes GhostBusters tools via SSE transport."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ghostbusters")


@mcp.tool()
def analyze_text(text: str, use_ai: bool = None, use_lm_signals: bool = None) -> dict:
    """Analyze text for AI-generated content patterns.

    Returns sentence-level scores and an overall AI probability score.
    Set use_ai=true to force AI analysis, use_ai=false for heuristics only,
    or omit to use the saved setting.
    Set use_lm_signals=true to use language-model statistical signals,
    or omit to use the saved setting.
    """
    # Resolve use_lm_signals from DB settings if not provided
    if use_lm_signals is None:
        from db import query_one
        settings = query_one("SELECT lm_signals_enabled FROM settings WHERE id = 1")
        use_lm_signals = settings["lm_signals_enabled"] if settings else False
    from ai_providers.router import route_analysis
    return route_analysis(text, use_ai=use_ai, use_lm_signals=use_lm_signals)


@mcp.tool()
def rewrite_text(text: str, voice_profile_id: int = None, use_ai: bool = None) -> dict:
    """Rewrite AI-flagged text to sound more human.

    Uses the specified voice profile for style guidance.
    Set use_ai=true to force AI rewriting, use_ai=false for heuristics only,
    or omit to use the saved setting.
    """
    from ai_providers.router import route_rewrite
    return route_rewrite(text, voice_profile_id, use_ai=use_ai)


@mcp.tool()
def get_score(text: str, use_lm_signals: bool = None) -> dict:
    """Quick AI detection score for a block of text (heuristics only).

    Returns overall_score (0-100, higher = more likely AI),
    sentence_scores, and detected patterns. Always uses Python heuristics.
    Set use_lm_signals=true to use language-model statistical signals,
    or omit to use the saved setting.
    """
    # Resolve use_lm_signals from DB settings if not provided
    if use_lm_signals is None:
        from db import query_one
        settings = query_one("SELECT lm_signals_enabled FROM settings WHERE id = 1")
        use_lm_signals = settings["lm_signals_enabled"] if settings else False
    from utils.detector import detect_ai_patterns
    return detect_ai_patterns(text, use_lm_signals=use_lm_signals)


@mcp.tool()
def check_voice(text: str, voice_profile_id: int = None) -> dict:
    """Check text against a voice profile for anti-AI pattern compliance.

    Returns violations found and suggestions for improvement.
    """
    from utils.voice_checker import check_voice_compliance
    return check_voice_compliance(text, voice_profile_id)


@mcp.tool()
def get_ai_status() -> dict:
    """Get current AI provider status.

    Returns whether AI is enabled, which provider is configured,
    runtime availability, and any error messages.
    """
    from ai_providers.router import get_ai_status as _get_status
    return _get_status()


@mcp.tool()
def set_ai_enabled(enabled: bool) -> dict:
    """Toggle AI provider on or off.

    Saves the preference to the database. When disabled, all analysis
    and rewriting uses Python heuristics only.
    """
    from db import execute
    from ai_providers.router import startup_health_check, get_ai_status as _get_status
    execute("UPDATE settings SET ai_enabled = %s, updated_at = CURRENT_TIMESTAMP WHERE id = 1", (enabled,))
    startup_health_check()
    return _get_status()


@mcp.tool()
def get_style_guide() -> dict:
    """Get the resolved active voice profile (weights + English instructions + prompts).

    Returns the baseline profile, any overlays, the merged element list with
    numeric weights, human-readable English instructions derived from those
    weights, and all style prompts.
    """
    from db import get_conn
    from utils.voice_profile_service import VoiceProfileService
    from utils.weight_translator import translate_elements_to_english
    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        stack = svc.get_active_stack()
    elements = stack.get("resolved_elements", [])
    return {
        "baseline": stack.get("baseline"),
        "overlays": stack.get("overlays", []),
        "elements": elements,
        "english_instructions": translate_elements_to_english(elements),
        "prompts": stack.get("prompts", []),
    }


@mcp.tool()
def get_rules() -> dict:
    """Get the active rules configuration (detection config only).

    Returns all detection rule sections: heuristic weights, buzzwords,
    ai_phrases, word_lists, thresholds, classification, severity, and pipeline.
    """
    from utils.rules_config import rules_config
    return {
        "heuristic_weights": rules_config.weights,
        "buzzwords": rules_config.buzzwords,
        "ai_phrases": rules_config.ai_phrases,
        "word_lists": rules_config.word_lists,
        "thresholds": rules_config.thresholds,
        "classification": rules_config.classification,
        "severity": rules_config.severity,
        "pipeline": rules_config.pipeline,
        "ai_prompt": rules_config.ai_prompt,
    }


@mcp.tool()
def get_full_guide() -> dict:
    """Get both the active voice profile and the rules configuration combined.

    Useful for AI providers that need a single call to retrieve all style and
    detection guidance in one payload.
    """
    from db import get_conn
    from utils.voice_profile_service import VoiceProfileService
    from utils.weight_translator import translate_elements_to_english
    from utils.rules_config import rules_config
    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        stack = svc.get_active_stack()
    elements = stack.get("resolved_elements", [])
    return {
        "voice_profile": {
            "baseline": stack.get("baseline"),
            "overlays": stack.get("overlays", []),
            "elements": elements,
            "english_instructions": translate_elements_to_english(elements),
            "prompts": stack.get("prompts", []),
        },
        "rules": {
            "heuristic_weights": rules_config.weights,
            "buzzwords": rules_config.buzzwords,
            "ai_phrases": rules_config.ai_phrases,
            "word_lists": rules_config.word_lists,
            "thresholds": rules_config.thresholds,
            "classification": rules_config.classification,
            "severity": rules_config.severity,
            "pipeline": rules_config.pipeline,
            "ai_prompt": rules_config.ai_prompt,
        },
    }


@mcp.tool()
def list_voice_profiles() -> list:
    """List all available voice profiles.

    Returns summary info for every profile: id, name, description,
    profile_type (baseline or overlay), parse_count, and stack metadata.
    """
    from db import get_conn
    from utils.voice_profile_service import VoiceProfileService
    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        return svc.list_profiles()


@mcp.tool()
def set_active_profile(baseline_id: int, overlay_ids: list[int] = None) -> dict:
    """Set the active voice profile stack (baseline + overlays).

    baseline_id: ID of the profile to use as the baseline.
    overlay_ids: Optional list of profile IDs to layer on top, in order.

    Returns the resolved active stack after the update.
    """
    from db import get_conn
    from utils.voice_profile_service import VoiceProfileService
    from utils.weight_translator import translate_elements_to_english
    ids = overlay_ids or []
    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        svc.set_active_stack(baseline_id, ids)
        stack = svc.get_active_stack()
    elements = stack.get("resolved_elements", [])
    return {
        "baseline": stack.get("baseline"),
        "overlays": stack.get("overlays", []),
        "elements": elements,
        "english_instructions": translate_elements_to_english(elements),
        "prompts": stack.get("prompts", []),
    }

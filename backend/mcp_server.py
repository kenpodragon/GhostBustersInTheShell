"""MCP Server - Exposes GhostBusters tools via SSE transport."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ghostbusters")


@mcp.tool()
def analyze_text(text: str, use_ai: bool = None) -> dict:
    """Analyze text for AI-generated content patterns.

    Returns sentence-level scores and an overall AI probability score.
    Set use_ai=true to force AI analysis, use_ai=false for heuristics only,
    or omit to use the saved setting.
    """
    from ai_providers.router import route_analysis
    return route_analysis(text, use_ai=use_ai)


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
def get_score(text: str) -> dict:
    """Quick AI detection score for a block of text (heuristics only).

    Returns overall_score (0-100, higher = more likely AI),
    sentence_scores, and detected patterns. Always uses Python heuristics.
    """
    from utils.detector import detect_ai_patterns
    return detect_ai_patterns(text)


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

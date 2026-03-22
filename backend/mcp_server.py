"""MCP Server - Exposes GhostBusters tools via SSE transport."""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ghostbusters")


@mcp.tool()
def analyze_text(text: str) -> dict:
    """Analyze text for AI-generated content patterns.

    Returns sentence-level scores and an overall AI probability score.
    """
    from ai_providers.router import route_analysis
    return route_analysis(text)


@mcp.tool()
def rewrite_text(text: str, voice_profile_id: int = None) -> dict:
    """Rewrite AI-flagged text to sound more human.

    Uses the specified voice profile for style guidance.
    Falls back to default heuristic rewriting if no AI provider available.
    """
    from ai_providers.router import route_rewrite
    return route_rewrite(text, voice_profile_id)


@mcp.tool()
def get_score(text: str) -> dict:
    """Quick AI detection score for a block of text.

    Returns overall_score (0-100, higher = more likely AI),
    sentence_scores, and detected patterns.
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

"""AI Provider Router - Routes to AI or falls back to Python heuristics.

Pattern: Try AI provider first (Claude, Gemini, etc.), fall back to
local Python-based analysis if AI is unavailable.

Runtime state: AI can be auto-disabled on token/rate errors and
re-enabled on next startup if the user's saved preference is 'on'.
"""
from config import config
from utils.rules_config import rules_config

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


def route_analysis(text: str, use_ai: bool = None, use_lm_signals: bool = False) -> dict:
    """Analyze text for AI patterns.

    Architecture (Phase 3.11 A_v3):
    - Always run Python heuristics (fast, free, always-on)
    - If AI available, also run AI analysis in parallel pipeline
    - Combine: final = AI * 0.6 + Heuristic * 0.4
    - If AI unavailable or errors: heuristic-only
    """
    from utils.detector import detect_ai_patterns
    from utils.heuristics.classification import classify_category

    # Step 1: Always run heuristics
    heuristic_result = detect_ai_patterns(text, use_lm_signals=use_lm_signals)
    heuristic_score = heuristic_result.get("overall_score", 0)

    # Step 2: Try AI if available
    ai_result = None
    ai_score = None
    if should_use_ai(use_ai):
        settings = _get_settings()
        provider = _get_provider(settings.get("ai_provider"))
        if provider:
            try:
                ai_result = provider.analyze(text)
                ai_score = ai_result.get("overall_score")
            except Exception as e:
                if _is_token_error(e):
                    _disable_runtime(str(e))
                print(f"[AI Router] AI analysis failed: {e}")
                # Continue with heuristic-only

    # Step 3: Combine scores
    if ai_score is not None:
        combined_score = round(ai_score * rules_config.pipeline.get("ai_weight", 0.6) + heuristic_score * rules_config.pipeline.get("heuristic_weight", 0.4), 1)

        # Merge patterns from both sources
        ai_patterns = ai_result.get("detected_patterns", [])
        heuristic_patterns = heuristic_result.get("patterns", [])
        # Tag AI patterns with source
        for p in ai_patterns:
            p["source"] = "ai"
        for p in heuristic_patterns:
            p["source"] = "heuristic"
        all_patterns = heuristic_patterns + ai_patterns

        result = {
            "overall_score": combined_score,
            "patterns": all_patterns,
            "sentences": heuristic_result.get("sentences", []),
            "_analysis_mode": "combined",
            "_ai_score": round(ai_score, 1),
            "_heuristic_score": round(heuristic_score, 1),
            "_ai_reasoning": ai_result.get("reasoning", ""),
        }
        # Preserve tier breakdown from heuristics
        if "tiers" in heuristic_result:
            result["tiers"] = heuristic_result["tiers"]
        # Reclassify with combined score
        result["classification"] = classify_category(result)
        return result

    # Heuristic-only fallback
    heuristic_result["_analysis_mode"] = "heuristic"
    return heuristic_result


def _get_voice_elements_and_prompts(voice_profile_id: int = None, baseline_id: int = None, overlay_ids: list = None):
    """Resolve voice elements and prompts from the active stack or explicit IDs.

    Priority:
    1. Explicit baseline_id/overlay_ids (from request body)
    2. voice_profile_id (legacy — single profile, no stack)
    3. Active stack from settings (DB)

    Returns (voice_elements, voice_prompts) — both may be empty lists.
    """
    try:
        from utils.voice_profile_service import VoiceProfileService
        from db import get_conn
        with get_conn() as conn:
            svc = VoiceProfileService(conn)

            if baseline_id is not None:
                # Explicit stack provided — resolve it directly
                overlay_ids = overlay_ids or []
                from utils.voice_profile_service import VoiceProfileService as _VPS
                baseline_elements = svc._get_elements(baseline_id)
                overlay_element_lists = [svc._get_elements(oid) for oid in overlay_ids]
                resolved = svc._resolve_stack(baseline_elements, overlay_element_lists)
                prompts = svc._get_prompts(baseline_id)
                for oid in overlay_ids:
                    prompts.extend(svc._get_prompts(oid))
                return resolved, prompts

            elif voice_profile_id:
                # Legacy single profile — treat as baseline with no overlays
                elements = svc._get_elements(voice_profile_id)
                prompts = svc._get_prompts(voice_profile_id)
                return elements, prompts

            else:
                # Use active stack from settings
                stack = svc.get_active_stack()
                return stack.get("resolved_elements", []), stack.get("prompts", [])
    except Exception as e:
        print(f"[AI Router] Could not resolve voice stack: {e}")
        return [], []


def route_rewrite(text: str, voice_profile_id: int = None, use_ai: bool = None, threshold: int = 20, use_lm_signals: bool = False, comment: str = None, baseline_id: int = None, overlay_ids: list = None) -> dict:
    """Rewrite text using a two-pass pipeline.

    Pass 1 — Voice: Rewrite in the author's voice using voice elements.
        No detection analysis needed upfront. Pure voice fidelity.
    Pass 2 — Detection Fix (conditional): If pass 1 score > threshold,
        run detection and send targeted fix instructions. Minimal changes.
    """
    from utils.detector import detect_ai_patterns

    # Resolve voice stack
    voice_elements, voice_prompts = _get_voice_elements_and_prompts(
        voice_profile_id=voice_profile_id,
        baseline_id=baseline_id,
        overlay_ids=overlay_ids,
    )

    # If AI unavailable, fall back to heuristic rewrite
    if not should_use_ai(use_ai):
        from utils.rewriter import heuristic_rewrite
        result = heuristic_rewrite(text, voice_profile_id, voice_elements=voice_elements)
        result["_analysis_mode"] = "heuristic"
        return result

    settings = _get_settings()
    provider = _get_provider(settings.get("ai_provider"))
    if not provider:
        from utils.rewriter import heuristic_rewrite
        result = heuristic_rewrite(text, voice_profile_id, voice_elements=voice_elements)
        result["_analysis_mode"] = "heuristic"
        return result

    from utils.style_brief import generate_style_brief
    model_name = settings.get("ai_provider", "claude")

    try:
        # --- Pass 1: Voice rewrite ---
        brief_voice = generate_style_brief(
            detection_result=None,
            model=model_name,
            mode="voice",
            voice_elements=voice_elements or None,
            voice_prompts=voice_prompts or None,
        )

        rewritten = provider.rewrite(text, style_brief=brief_voice)
        rewritten_text = rewritten.get("rewritten_text", text)

        # Score pass 1 output
        recheck = detect_ai_patterns(rewritten_text, use_lm_signals=use_lm_signals)
        after_score = recheck.get("overall_score", 0)
        passes = 1
        brief_pass2 = None

        # --- Pass 2: Detection fix (conditional) ---
        if after_score > threshold:
            brief_pass2 = generate_style_brief(
                detection_result=recheck,
                model=model_name,
                mode="detection_fix",
                comment=comment,
            )
            try:
                rewritten2 = provider.rewrite(rewritten_text, style_brief=brief_pass2)
                rewritten_text2 = rewritten2.get("rewritten_text", rewritten_text)
                recheck2 = detect_ai_patterns(rewritten_text2, use_lm_signals=use_lm_signals)
                after_score2 = recheck2.get("overall_score", 0)

                # Regression guard: only use pass 2 if it improved
                if after_score2 < after_score:
                    rewritten_text = rewritten_text2
                    rewritten = rewritten2
                    recheck = recheck2
                    after_score = after_score2
                    passes = 2
            except Exception as e2:
                print(f"[AI Router] Pass 2 (detection fix) failed: {e2}")

        # Check voice compliance against resolved elements
        from utils.voice_checker import check_voice_compliance
        compliance = check_voice_compliance(
            rewritten_text,
            voice_profile_id=voice_profile_id if not voice_elements else None,
            voice_elements=voice_elements or None,
        )

        # Score original for the _before_score field
        original_detection = detect_ai_patterns(text, use_lm_signals=use_lm_signals)
        before_score = original_detection.get("overall_score", 0)

        remaining = [p.get("pattern", "") for p in recheck.get("patterns", [])]
        classification = recheck.get("classification", {})

        return {
            "rewritten_text": rewritten_text,
            "changes": rewritten.get("changes", []),
            "score": round(after_score, 1),
            "classification": classification,
            "patterns": recheck.get("patterns", []),
            "_analysis_mode": "ai_guided",
            "_before_score": round(before_score, 1),
            "_after_score": round(after_score, 1),
            "_passes": passes,
            "_remaining_signals": remaining,
            "_brief": brief_voice,
            "_brief_pass2": brief_pass2,
            "_voice_compliance": compliance,
        }

    except Exception as e:
        if _is_token_error(e):
            _disable_runtime(str(e))
        print(f"[AI Router] Rewrite failed: {e}")
        from utils.rewriter import heuristic_rewrite
        result = heuristic_rewrite(text, voice_profile_id, voice_elements=voice_elements)
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

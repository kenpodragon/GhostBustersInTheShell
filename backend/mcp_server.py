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


@mcp.tool()
def score_fidelity(generated_text: str, profile_id: int, mode: str = "quantitative") -> dict:
    """Score how closely generated text matches a voice profile.

    mode: 'quantitative' (element comparison), 'qualitative' (AI comparison),
          or 'both' (quantitative first, then qualitative with context).
    Returns aggregate similarity score and per-element breakdown.
    """
    from db import get_conn, query_all
    from utils.voice_profile_service import VoiceProfileService
    from utils.voice_fidelity_scorer import score_fidelity as do_score

    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        profile = svc.get_profile(profile_id)
    if not profile:
        return {"error": f"Profile {profile_id} not found"}
    profile_elements = profile.get("elements", [])
    sample_text = None
    if mode in ("qualitative", "both"):
        corpus_doc = query_all(
            """SELECT original_text FROM documents
               WHERE voice_profile_id = %s AND purpose = 'voice_corpus'
               ORDER BY length(original_text) DESC LIMIT 1""",
            (profile_id,),
        )
        if corpus_doc:
            sample_text = corpus_doc[0]["original_text"][:5000]
        elif mode == "qualitative":
            return {"error": "No corpus documents available for qualitative scoring."}
        else:
            mode = "quantitative"
    return do_score(generated_text=generated_text, profile_elements=profile_elements, sample_text=sample_text, mode=mode)


@mcp.tool()
def get_profile_samples(profile_id: int, limit: int = 5) -> list:
    """Get sample texts from a profile's voice corpus documents."""
    from db import query_all
    return query_all(
        """SELECT id AS document_id, filename, LEFT(original_text, 5000) AS text_excerpt,
                  length(original_text) AS word_count, created_at
           FROM documents WHERE voice_profile_id = %s AND purpose = 'voice_corpus'
           ORDER BY created_at DESC LIMIT %s""",
        (profile_id, limit),
    )


@mcp.tool()
def consolidate_voice_observations(profile_id: int) -> dict:
    """Consolidate AI observations for a voice profile.

    Merges per-document AI observations into clustered prompts with frequency
    counts, metric consensus descriptions, and discovered patterns.
    """
    from utils.ai_consolidator import consolidate_observations
    return consolidate_observations(profile_id)


@mcp.tool()
def reparse_voice_profile(profile_id: int, use_ai: bool = False) -> dict:
    """Re-parse all corpus documents into a new profile version.

    Creates a snapshot, clones the profile, re-parses all voice_corpus documents.
    Returns old vs new element comparison.
    """
    from db import get_conn, query_all, query_one, execute
    from utils.voice_profile_service import VoiceProfileService
    from utils.voice_generator import generate_voice_profile
    import datetime, json as _json

    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        profile = svc.get_profile_summary(profile_id)
        if not profile:
            return {"error": "Profile not found"}
        snapshot_name = f"Pre-reparse backup {datetime.date.today().isoformat()}"
        svc.save_snapshot(profile_id, snapshot_name)
        new_name = f"{profile['name']} (reparsed {datetime.date.today().isoformat()})"
        new_profile = svc.clone_profile(profile_id, new_name)
        new_id = new_profile["id"]

    corpus_docs = query_all(
        "SELECT id, original_text, filename FROM documents WHERE voice_profile_id = %s AND purpose = 'voice_corpus' ORDER BY created_at",
        (profile_id,),
    )
    parsed_count = 0
    for doc in corpus_docs:
        try:
            parse_result = generate_voice_profile(doc["original_text"])
            with get_conn() as conn:
                svc = VoiceProfileService(conn)
                svc.apply_parse_results(new_id, parse_result)
            parsed_count += 1
            if use_ai:
                from ai_providers.router import should_use_ai
                if should_use_ai(True):
                    from utils.ai_voice_extractor import extract_voice_with_ai
                    ai_result = extract_voice_with_ai(doc["original_text"], parse_result)
                    if ai_result["status"] == "success":
                        execute(
                            """INSERT INTO ai_parse_observations (profile_id, document_id, qualitative_prompts, metric_descriptions, discovered_patterns, raw_ai_response)
                               VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)""",
                            (new_id, doc["id"],
                             _json.dumps(ai_result["qualitative_prompts"]),
                             _json.dumps(ai_result["metric_descriptions"]),
                             _json.dumps(ai_result["discovered_patterns"]),
                             _json.dumps(ai_result["raw_ai_response"])),
                        )
        except Exception:
            pass

    obs_count = query_one("SELECT COUNT(*) AS cnt FROM ai_parse_observations WHERE profile_id = %s", (new_id,))
    if obs_count and obs_count["cnt"] > 0:
        from utils.ai_consolidator import consolidate_observations
        consolidate_observations(new_id)

    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        old_elements = svc.get_elements(profile_id)
        new_elements = svc.get_elements(new_id)

    return {
        "old_profile_id": profile_id, "new_profile_id": new_id,
        "parsed_count": parsed_count, "total_documents": len(corpus_docs),
        "old_elements": old_elements, "new_elements": new_elements,
    }


@mcp.tool()
def get_corpus_info(profile_id: int) -> dict:
    """Get corpus documents and stats for a voice profile."""
    from db import query_all, query_one
    docs = query_all(
        """SELECT d.id, d.filename, length(d.original_text) AS word_count, d.created_at,
                  EXISTS(SELECT 1 FROM ai_parse_observations a WHERE a.document_id = d.id) AS has_ai_observations
           FROM documents d
           WHERE d.voice_profile_id = %s AND d.purpose = 'voice_corpus'
           ORDER BY d.created_at DESC""",
        (profile_id,),
    )
    stats_row = query_one(
        """SELECT COUNT(*) AS total_documents,
                  COALESCE(SUM(length(original_text)), 0) AS total_words,
                  (SELECT COUNT(*) FROM ai_parse_observations WHERE profile_id = %s) AS ai_observations_count
           FROM documents WHERE voice_profile_id = %s AND purpose = 'voice_corpus'""",
        (profile_id, profile_id),
    )
    return {
        "documents": docs,
        "stats": {
            "total_documents": stats_row["total_documents"] if stats_row else 0,
            "total_words": stats_row["total_words"] if stats_row else 0,
            "ai_observations_count": stats_row["ai_observations_count"] if stats_row else 0,
        },
    }


@mcp.tool()
def remove_corpus_document(profile_id: int, document_id: int) -> dict:
    """Remove a document from a profile's voice corpus."""
    from db import query_one, execute
    doc = query_one(
        "SELECT id FROM documents WHERE id = %s AND voice_profile_id = %s AND purpose = 'voice_corpus'",
        (document_id, profile_id),
    )
    if not doc:
        return {"error": "Document not found in this profile's corpus"}
    execute("DELETE FROM ai_parse_observations WHERE document_id = %s", (document_id,))
    execute("DELETE FROM documents WHERE id = %s", (document_id,))
    return {"status": "deleted", "document_id": document_id,
            "warning": "Re-parse needed to recalculate profile without this document."}


@mcp.tool()
def purge_analysis_documents(older_than_days: int = 30) -> dict:
    """Purge analysis documents older than specified days. Never touches voice corpus."""
    from db import query_one, execute
    count_row = query_one(
        "SELECT COUNT(*) AS cnt FROM documents WHERE purpose = 'analysis' AND created_at < NOW() - make_interval(days => %s)",
        (older_than_days,),
    )
    execute(
        "DELETE FROM documents WHERE purpose = 'analysis' AND created_at < NOW() - make_interval(days => %s)",
        (older_than_days,),
    )
    return {"status": "purged", "deleted_count": count_row["cnt"] if count_row else 0}


@mcp.tool()
def parse_voice_text(profile_id: int, text: str, filename: str = "Untitled", use_ai: bool = False, force_near_duplicate: bool = False) -> dict:
    """Parse text into a voice profile with optional AI extraction.

    Creates a voice_corpus document, runs dedup check, parses with Python,
    optionally runs AI extraction and auto-consolidation.
    """
    import json as _json
    from db import get_conn, execute, query_one
    from utils.voice_profile_service import VoiceProfileService
    from utils.voice_generator import generate_voice_profile
    from utils.document_dedup import compute_content_hash, check_exact_duplicate, check_near_duplicate

    content_hash = compute_content_hash(text)
    exact = check_exact_duplicate(content_hash, profile_id)
    if exact:
        return {"error": f"Already parsed on {exact['created_at']} as '{exact['filename']}'.", "duplicate_type": "exact"}
    if not force_near_duplicate:
        near = check_near_duplicate(text, profile_id)
        if near:
            return {"error": f"Near duplicate of '{near['filename']}'. Set force_near_duplicate=true.", "duplicate_type": "near", "similarity": near.get("similarity")}

    doc_row = query_one(
        """INSERT INTO documents (filename, file_type, original_text, voice_profile_id, purpose, content_hash)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (filename, "text", text, profile_id, "voice_corpus", content_hash),
    )
    document_id = doc_row["id"]

    parse_result = generate_voice_profile(text)
    with get_conn() as conn:
        svc = VoiceProfileService(conn)
        svc.apply_parse_results(profile_id, parse_result)
        elements = svc.get_elements(profile_id)
        updated = svc.get_profile_summary(profile_id)

    ai_extraction = {"status": "skipped"}
    if use_ai:
        from ai_providers.router import should_use_ai
        if should_use_ai(True):
            from utils.ai_voice_extractor import extract_voice_with_ai
            ai_extraction = extract_voice_with_ai(text, parse_result)
            if ai_extraction["status"] == "success":
                execute(
                    """INSERT INTO ai_parse_observations (profile_id, document_id, qualitative_prompts, metric_descriptions, discovered_patterns, raw_ai_response)
                       VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)""",
                    (profile_id, document_id,
                     _json.dumps(ai_extraction["qualitative_prompts"]),
                     _json.dumps(ai_extraction["metric_descriptions"]),
                     _json.dumps(ai_extraction["discovered_patterns"]),
                     _json.dumps(ai_extraction["raw_ai_response"])),
                )
                from utils.ai_consolidator import consolidate_observations
                consolidate_observations(profile_id)

    return {
        "elements": elements, "findings": list(parse_result.keys()),
        "parse_count": updated.get("parse_count", 0), "document_id": document_id,
        "ai_extraction": {"status": ai_extraction["status"]},
    }


@mcp.tool()
def list_documents(purpose: str = "analysis", older_than_days: int = None) -> dict:
    """List documents for management. Filterable by purpose and age."""
    from db import query_all, query_one
    conditions = ["purpose = %s"]
    params: list = [purpose]
    if older_than_days is not None:
        conditions.append("created_at < NOW() - make_interval(days => %s)")
        params.append(older_than_days)
    where = " AND ".join(conditions)
    docs = query_all(
        f"SELECT id, filename, file_type, length(original_text) AS word_count, created_at, voice_profile_id FROM documents WHERE {where} ORDER BY created_at DESC",
        tuple(params),
    )
    stats = query_one(
        f"SELECT COUNT(*) AS total_count, COALESCE(SUM(length(original_text)), 0) AS total_size_words FROM documents WHERE {where}",
        tuple(params),
    )
    return {"documents": docs, "stats": {"total_count": stats["total_count"], "total_size_words": stats["total_size_words"]}}

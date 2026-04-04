"""AI observation consolidation engine.

Merges per-document AI observations into a consolidated analysis for a voice profile.

Two-stage consolidation for prompts:
  Stage 1 (Python): Group near-duplicate prompts by text similarity using SequenceMatcher.
  Stage 2 (AI): Send pre-clustered groups to Claude for semantic merge and quality rewriting.

Raw per-document observations are preserved in ai_parse_observations table.
"""
import json
from collections import defaultdict
from difflib import SequenceMatcher

# Similarity threshold for Stage 1 heuristic clustering (0.0 - 1.0)
# 0.3 tested: collapses 1167 prompts -> 347 clusters with meaningful grouping
SIMILARITY_THRESHOLD = 0.3

CONSOLIDATION_PROMPT = """You are analyzing voice style observations extracted from {doc_count} writing samples by the same author.

Below are pre-grouped voice characteristic clusters. Each cluster contains similar observations that were grouped by text similarity. Your job is to:
1. Write one clear, concise representative voice directive per cluster (2-3 sentences max)
2. Merge any clusters that describe the same underlying voice characteristic
3. Drop clusters that are vague, contradictory, or not useful as writing instructions
4. Return the final list sorted by frequency (most observed first)

## Pre-Clustered Observations:
{clusters_json}

Return ONLY valid JSON:
{{
  "consolidated_prompts": [
    {{
      "prompt": "clear, concise voice directive (2-3 sentences max)",
      "frequency": 15,
      "confidence": 0.85,
      "source_count": 3
    }}
  ]
}}"""


def _get_provider():
    """Get AI provider using the existing router pattern."""
    from ai_providers.router import _get_provider as router_get_provider, should_use_ai
    if not should_use_ai():
        return None
    return router_get_provider()


# ---------------------------------------------------------------------------
# Stage 1: Heuristic pre-clustering
# ---------------------------------------------------------------------------

def _normalize_prompt_text(text: str) -> str:
    """Normalize prompt text for comparison."""
    import re
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def _heuristic_cluster_prompts(all_prompts: list[dict], threshold: float = SIMILARITY_THRESHOLD) -> list[dict]:
    """Group similar prompts using SequenceMatcher on normalized text.

    Returns list of clusters: {representative, prompts[], frequency, avg_confidence}
    """
    clusters = []  # list of {normalized, prompts: [original dicts]}

    for p in all_prompts:
        text = p.get("prompt", "")
        if not text:
            continue
        normalized = _normalize_prompt_text(text)[:200]  # first 200 chars — prompts diverge in detail, not intent

        # Find best matching cluster
        best_match = None
        best_ratio = 0.0
        for cluster in clusters:
            ratio = SequenceMatcher(None, normalized, cluster["normalized"]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = cluster

        if best_match and best_ratio >= threshold:
            best_match["prompts"].append(p)
        else:
            clusters.append({"normalized": normalized, "prompts": [p]})

    # Build cluster summaries
    result = []
    for cluster in clusters:
        prompts = cluster["prompts"]
        confidences = [p.get("confidence", 0.5) for p in prompts]
        # Pick the longest prompt as representative (usually most detailed)
        representative = max(prompts, key=lambda p: len(p.get("prompt", "")))
        result.append({
            "representative": representative["prompt"],
            "frequency": len(prompts),
            "avg_confidence": round(sum(confidences) / len(confidences), 3),
            "sample_prompts": [p["prompt"] for p in prompts[:3]],  # keep 3 samples for AI context
        })

    # Sort by frequency descending
    result.sort(key=lambda c: -c["frequency"])
    return result


# ---------------------------------------------------------------------------
# Stage 2: AI semantic merge
# ---------------------------------------------------------------------------

# Minimum frequency for a cluster to be sent to AI for rewriting
MIN_FREQUENCY_FOR_AI = 5


def _ai_merge_clusters(clusters: list[dict], doc_count: int) -> list[dict] | None:
    """Send high-frequency pre-clustered groups to AI for semantic merge and rewriting.

    Only clusters with frequency >= MIN_FREQUENCY_FOR_AI are sent.
    """
    provider = _get_provider()
    if not provider:
        return None

    # Only send significant clusters
    significant = [c for c in clusters if c["frequency"] >= MIN_FREQUENCY_FOR_AI]
    if not significant:
        return None

    clusters_for_ai = []
    for c in significant:
        clusters_for_ai.append({
            "representative": c["representative"],
            "frequency": c["frequency"],
            "avg_confidence": c["avg_confidence"],
            "sample_prompts": c["sample_prompts"],
        })

    print(f"[Consolidator] Sending {len(clusters_for_ai)} clusters (freq >= {MIN_FREQUENCY_FOR_AI}) to AI")

    prompt = CONSOLIDATION_PROMPT.format(
        doc_count=doc_count,
        clusters_json=json.dumps(clusters_for_ai, indent=2),
    )

    try:
        response = provider._run_cli(prompt)
        return response.get("consolidated_prompts", [])
    except Exception as e:
        print(f"[Consolidator] AI merge failed: {e}")
        return None


def _fallback_from_clusters(clusters: list[dict]) -> list[dict]:
    """When AI is unavailable, use top heuristic clusters directly."""
    significant = [c for c in clusters if c["frequency"] >= MIN_FREQUENCY_FOR_AI]
    return [
        {
            "prompt": c["representative"],
            "frequency": c["frequency"],
            "confidence": c["avg_confidence"],
            "source_count": c["frequency"],
        }
        for c in significant
    ]


# ---------------------------------------------------------------------------
# Metric & Pattern Aggregation (unchanged)
# ---------------------------------------------------------------------------

def _aggregate_metric_descriptions(observations: list[dict]) -> list[dict]:
    """Aggregate metric descriptions across observations into consensus view."""
    element_data = defaultdict(lambda: {"descriptions": [], "assessments": []})

    for obs in observations:
        for md in obs.get("metric_descriptions", []):
            name = md.get("element", "")
            if not name:
                continue
            element_data[name]["descriptions"].append(md.get("description", ""))
            element_data[name]["assessments"].append(md.get("ai_assessment", "accurate"))

    result = []
    for element, data in sorted(element_data.items()):
        assessments = data["assessments"]
        accurate_count = sum(1 for a in assessments if a == "accurate")
        misleading_count = sum(1 for a in assessments if a == "misleading")
        insufficient_count = sum(1 for a in assessments if a == "insufficient_data")

        descriptions = [d for d in data["descriptions"] if d]
        consensus = max(descriptions, key=len) if descriptions else ""

        result.append({
            "element": element,
            "consensus_description": consensus,
            "agreement_count": accurate_count,
            "disagreement_count": misleading_count + insufficient_count,
            "flagged_misleading": misleading_count > 0,
        })

    return result


def _aggregate_discovered_patterns(observations: list[dict]) -> list[dict]:
    """Aggregate discovered patterns, deduplicating by suggested_element_name."""
    pattern_counts = defaultdict(lambda: {"pattern": "", "description": "", "occurrences": 0})

    for obs in observations:
        for dp in obs.get("discovered_patterns", []):
            name = dp.get("suggested_element_name", "")
            if not name:
                continue
            pattern_counts[name]["pattern"] = dp.get("pattern", "")
            pattern_counts[name]["description"] = dp.get("description", "")
            pattern_counts[name]["occurrences"] += 1

    return [
        {"suggested_element_name": name, **data}
        for name, data in sorted(pattern_counts.items(), key=lambda x: -x[1]["occurrences"])
    ]


# ---------------------------------------------------------------------------
# Main consolidation entry point
# ---------------------------------------------------------------------------

def consolidate_observations(profile_id: int) -> dict:
    """Consolidate all AI observations for a profile into a merged analysis.

    Stage 1: Python heuristic clustering (SequenceMatcher)
    Stage 2: AI semantic merge of pre-clustered groups
    Fallback: Use heuristic clusters directly if AI unavailable
    """
    from db import query_all, execute

    observations = query_all(
        """SELECT qualitative_prompts, metric_descriptions, discovered_patterns
           FROM ai_parse_observations
           WHERE profile_id = %s
           ORDER BY created_at""",
        (profile_id,),
    )

    if not observations:
        return {
            "consolidated_prompts": [],
            "metric_consensus": [],
            "discovered_patterns": [],
            "observation_count": 0,
            "document_count": 0,
        }

    # Collect all prompts
    all_prompts = []
    for obs in observations:
        for p in obs.get("qualitative_prompts", []):
            if p.get("prompt"):
                all_prompts.append(p)

    doc_count_row = query_all(
        """SELECT COUNT(DISTINCT document_id) as cnt
           FROM ai_parse_observations
           WHERE profile_id = %s""",
        (profile_id,),
    )
    doc_count = doc_count_row[0]["cnt"] if doc_count_row else 0

    # Stage 1: Heuristic pre-clustering
    clusters = _heuristic_cluster_prompts(all_prompts)
    significant = [c for c in clusters if c["frequency"] >= MIN_FREQUENCY_FOR_AI]
    print(f"[Consolidator] Stage 1: {len(all_prompts)} prompts -> {len(clusters)} clusters ({len(significant)} significant)")

    # Stage 2: AI semantic merge (only significant clusters)
    consolidated_prompts = _ai_merge_clusters(clusters, doc_count)
    if consolidated_prompts is None:
        print(f"[Consolidator] Stage 2: AI unavailable, using heuristic clusters")
        consolidated_prompts = _fallback_from_clusters(clusters)
    else:
        print(f"[Consolidator] Stage 2: AI merged to {len(consolidated_prompts)} prompts")

    metric_consensus = _aggregate_metric_descriptions(observations)
    discovered_patterns = _aggregate_discovered_patterns(observations)

    # Archive all clusters for reference, but only top ones go in consolidated_prompts
    archived_clusters = [
        {"representative": c["representative"], "frequency": c["frequency"], "avg_confidence": c["avg_confidence"]}
        for c in clusters
    ]

    import datetime
    result = {
        "consolidated_prompts": consolidated_prompts,
        "archived_clusters": archived_clusters,
        "heuristic_cluster_count": len(clusters),
        "significant_cluster_count": len(significant),
        "raw_prompt_count": len(all_prompts),
        "metric_consensus": metric_consensus,
        "discovered_patterns": discovered_patterns,
        "observation_count": len(observations),
        "document_count": doc_count,
        "last_consolidated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    execute(
        "UPDATE voice_profiles SET consolidated_ai_analysis = %s::jsonb WHERE id = %s",
        (json.dumps(result), profile_id),
    )

    # Write consolidated prompts into profile_prompts for generation + user editing
    _sync_prompts_to_profile(profile_id, consolidated_prompts)

    return result


def _sync_prompts_to_profile(profile_id: int, consolidated_prompts: list[dict]):
    """Replace profile_prompts with consolidated voice directives.

    These become the actual prompts used during rewrite generation
    and are editable by the user in the UI.
    """
    from db import execute

    execute("DELETE FROM profile_prompts WHERE voice_profile_id = %s", (profile_id,))
    for i, p in enumerate(consolidated_prompts):
        prompt_text = p.get("prompt", p.get("representative", ""))
        if not prompt_text:
            continue
        execute(
            """INSERT INTO profile_prompts (voice_profile_id, prompt_text, sort_order)
               VALUES (%s, %s, %s)""",
            (profile_id, prompt_text, i),
        )
    print(f"[Consolidator] Synced {len(consolidated_prompts)} prompts to profile_prompts")

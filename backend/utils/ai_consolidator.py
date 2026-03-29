"""AI observation consolidation engine.

Merges per-document AI observations into a consolidated analysis for a voice profile.
Uses AI for semantic clustering of qualitative prompts (with fallback to raw aggregation).
"""
import json
from collections import defaultdict

CONSOLIDATION_PROMPT = """You are analyzing voice style observations extracted from multiple writing samples by the same author.

Below are qualitative prompts extracted from {doc_count} documents. Many describe the same or similar voice characteristics in different words. Your job is to:
1. Group semantically similar prompts into clusters
2. Write one clear, concise representative prompt per cluster
3. Report the frequency (how many source prompts in the cluster) and average confidence

## Source Prompts:
{prompts_json}

Return ONLY valid JSON:
{{
  "consolidated_prompts": [
    {{
      "prompt": "clear, concise voice directive (2-3 sentences max)",
      "source_prompts": ["original prompt 1", "original prompt 2"],
      "frequency": 2,
      "confidence": 0.85
    }}
  ]
}}"""


def _get_provider():
    """Get AI provider using the existing router pattern."""
    from ai_providers.router import _get_provider as router_get_provider, should_use_ai
    if not should_use_ai():
        return None
    return router_get_provider()


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


def _cluster_prompts_with_ai(all_prompts: list[dict], doc_count: int) -> list[dict]:
    """Use AI to semantically cluster similar prompts."""
    provider = _get_provider()
    if not provider:
        return None

    prompt = CONSOLIDATION_PROMPT.format(
        doc_count=doc_count,
        prompts_json=json.dumps(all_prompts, indent=2),
    )

    try:
        response = provider._run_cli(prompt)
        return response.get("consolidated_prompts", [])
    except Exception as e:
        print(f"[Consolidator] AI clustering failed: {e}")
        return None


def _fallback_raw_prompts(all_prompts: list[dict]) -> list[dict]:
    """When AI is unavailable, return raw prompts with frequency=1."""
    return [
        {
            "prompt": p["prompt"],
            "source_prompts": [p["prompt"]],
            "frequency": 1,
            "confidence": p.get("confidence", 0.5),
        }
        for p in all_prompts
    ]


def consolidate_observations(profile_id: int) -> dict:
    """Consolidate all AI observations for a profile into a merged analysis."""
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

    consolidated_prompts = _cluster_prompts_with_ai(all_prompts, doc_count)
    if consolidated_prompts is None:
        consolidated_prompts = _fallback_raw_prompts(all_prompts)

    metric_consensus = _aggregate_metric_descriptions(observations)
    discovered_patterns = _aggregate_discovered_patterns(observations)

    import datetime
    result = {
        "consolidated_prompts": consolidated_prompts,
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

    return result

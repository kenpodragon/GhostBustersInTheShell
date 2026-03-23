"""Graduated severity system for AI detection signals.

Converts raw instance counts into tiered severity levels:
- caution (1 instance): minimal score impact, informational
- warning (2-3 instances): moderate score contribution
- strong (4+ instances): full score contribution

Severity compounds across analysis levels (sentence -> paragraph -> document).
"""

# Severity multipliers: how much of the raw score to apply
SEVERITY_MULTIPLIERS = {
    "caution": 0.25,
    "warning": 0.6,
    "strong": 1.0,
}

# Points assigned to each tier for cross-level compounding
SEVERITY_POINTS = {
    "caution": 1,
    "warning": 2,
    "strong": 3,
}


def classify_severity(instance_count: int) -> str | None:
    """Map instance count to severity tier."""
    if instance_count <= 0:
        return None
    if instance_count == 1:
        return "caution"
    if instance_count <= 3:
        return "warning"
    return "strong"


def apply_severity(raw_score: float, severity: str | None) -> float:
    """Scale a raw heuristic score by its severity tier."""
    if severity is None:
        return 0
    return raw_score * SEVERITY_MULTIPLIERS[severity]


def compound_across_levels(severities: list[str]) -> str | None:
    """Compound severity across analysis levels.

    Same signal appearing at multiple levels escalates:
    - caution + caution = warning
    - caution + caution + caution = strong
    - warning + caution = strong
    - any strong = strong
    """
    if not severities:
        return None

    total_points = sum(SEVERITY_POINTS.get(s, 0) for s in severities)

    if total_points >= 3:
        return "strong"
    if total_points >= 2:
        return "warning"
    if total_points >= 1:
        return "caution"
    return None

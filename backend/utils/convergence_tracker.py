"""
Convergence tracker — Welford's online algorithm + convergence detection.

Pure computation module: no database or IO dependencies.
Used by the research tool (Task 2) and product integration (Task 6).
"""
import math

# Convergence thresholds
ROLLING_DELTA_THRESHOLD = 0.02   # 2% change considered stable
CONSECUTIVE_REQUIRED = 3         # must be stable for 3 consecutive updates
NEAR_ZERO_MEAN = 0.01            # below this mean, use absolute delta
NEAR_ZERO_DELTA = 0.001          # absolute delta threshold for near-zero elements

# Completeness tiers: tier_name -> minimum pct (0-100)
COMPLETENESS_TIERS = {
    "bronze": 50,
    "silver": 75,
    "gold": 90,
}

# Starter tier: word-count-based milestones before Bronze
STARTER_MILESTONES = [2000, 5000, 10000, 20000]
STARTER_WORD_GATE = 20000  # Must have this many words AND 50% convergence for Bronze

STARTER_LABELS = {0: None, 1: "¼", 2: "½", 3: "¾", 4: "complete"}


def get_starter_milestone(total_words: int) -> dict:
    """Return current milestone progress based on word count.

    Returns dict with: milestone (0-4), milestone_label, words_current,
    words_next, milestone_pct.
    """
    # Find which milestone we've reached
    milestone = 0
    for i, threshold in enumerate(STARTER_MILESTONES):
        if total_words >= threshold:
            milestone = i + 1
        else:
            break

    # Clamp at 4 (full/complete)
    milestone = min(milestone, 4)
    label = STARTER_LABELS[milestone]

    # Calculate progress toward next milestone
    if milestone >= 4:
        # At or past word gate
        words_next = STARTER_WORD_GATE
        milestone_pct = 100
    else:
        words_next = STARTER_MILESTONES[milestone]
        prev_threshold = STARTER_MILESTONES[milestone - 1] if milestone > 0 else 0
        range_size = words_next - prev_threshold
        progress = total_words - prev_threshold
        milestone_pct = int(progress * 100 / range_size) if range_size > 0 else 0

    return {
        "milestone": milestone,
        "milestone_label": label,
        "words_current": total_words,
        "words_next": words_next,
        "milestone_pct": milestone_pct,
    }


# Mapping of all 65 elements to their category
ELEMENT_CATEGORIES = {
    # lexical (13)
    "avg_word_length": "lexical",
    "vocabulary_richness": "lexical",
    "hapax_legomena_ratio": "lexical",
    "long_word_frequency": "lexical",
    "lexical_density": "lexical",
    "function_word_rate": "lexical",
    "article_rate": "lexical",
    "preposition_rate": "lexical",
    "coordinating_conjunction_rate": "lexical",
    "subordinating_conjunction_rate": "lexical",
    "modal_verb_rate": "lexical",
    "contraction_rate": "lexical",
    "named_entity_density": "lexical",
    # syntactic (15)
    "avg_sentence_length": "syntactic",
    "sentence_length_stddev": "syntactic",
    "short_sentence_ratio": "syntactic",
    "long_sentence_ratio": "syntactic",
    "avg_clause_complexity": "syntactic",
    "sentence_opener_variety": "syntactic",
    "conjunction_opening_rate": "syntactic",
    "passive_voice_rate": "syntactic",
    "adjective_to_noun_ratio": "syntactic",
    "adverb_density": "syntactic",
    "verb_tense_past_ratio": "syntactic",
    "verb_tense_present_ratio": "syntactic",
    "clause_depth_avg": "syntactic",
    "paragraph_opening_pos_entropy": "syntactic",
    "narrative_vs_analytical_ratio": "syntactic",
    # structural (3)
    "paragraph_avg_length": "structural",
    "single_sentence_paragraph_ratio": "structural",
    "quotation_density": "structural",
    # idiosyncratic (13)
    "em_dash_usage": "idiosyncratic",
    "ellipsis_usage": "idiosyncratic",
    "exclamation_rate": "idiosyncratic",
    "semicolon_usage": "idiosyncratic",
    "colon_usage": "idiosyncratic",
    "comma_rate": "idiosyncratic",
    "parenthetical_usage": "idiosyncratic",
    "first_person_usage": "idiosyncratic",
    "second_person_usage": "idiosyncratic",
    "third_person_usage": "idiosyncratic",
    "rhetorical_question_rate": "idiosyncratic",
    "figurative_language_markers": "idiosyncratic",
    "archaic_vocabulary_rate": "idiosyncratic",
    # voice_tone (11)
    "hedging_language_rate": "voice_tone",
    "intensifier_rate": "voice_tone",
    "transition_word_rate": "voice_tone",
    "discourse_marker_rate": "voice_tone",
    "vocative_usage": "voice_tone",
    "sentiment_mean": "voice_tone",
    "sentiment_variance": "voice_tone",
    "sentiment_shift_rate": "voice_tone",
    "topic_drift_rate": "voice_tone",
    "topic_coherence_score": "voice_tone",
    "vocabulary_concentration": "voice_tone",
    # readability (10)
    "flesch_reading_ease": "readability",
    "flesch_kincaid_grade": "readability",
    "gunning_fog_index": "readability",
    "smog_index": "readability",
    "automated_readability_index": "readability",
    "coleman_liau_index": "readability",
}


class ElementTracker:
    """Tracks convergence of a single voice profile element using Welford's algorithm."""

    def __init__(self, name: str):
        self.name = name
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0          # sum of squared deviations (Welford)
        self.rolling_delta = 1.0
        self.consecutive_stable = 0
        self._converged = False
        self.converged_at_words = None
        self._category = ELEMENT_CATEGORIES.get(name, "unknown")

    @property
    def cv(self) -> float:
        """Coefficient of variation: std/mean. 0.0 if insufficient data or near-zero mean."""
        if self.count < 2:
            return 0.0
        if self.mean < NEAR_ZERO_MEAN:
            return 0.0
        variance = self.m2 / (self.count - 1)
        std = math.sqrt(variance)
        return std / self.mean

    @property
    def converged(self) -> bool:
        return self._converged

    def update(self, value: float, cumulative_words: int = 0) -> None:
        """Welford's incremental mean/variance update, then check convergence."""
        self.count += 1
        prev_mean = self.mean
        # Welford's online update
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2

        if self.count > 1:
            # Determine if this update is stable
            if prev_mean < NEAR_ZERO_MEAN:
                # Near-zero: use absolute delta
                self.rolling_delta = abs(self.mean - prev_mean)
                is_stable = self.rolling_delta < NEAR_ZERO_DELTA
            else:
                # Normal: use percentage delta
                self.rolling_delta = abs(self.mean - prev_mean) / abs(prev_mean)
                is_stable = self.rolling_delta < ROLLING_DELTA_THRESHOLD

            if is_stable:
                self.consecutive_stable += 1
            else:
                self.consecutive_stable = 0
                self._converged = False

            if self.consecutive_stable >= CONSECUTIVE_REQUIRED and not self._converged:
                self._converged = True
                self.converged_at_words = cumulative_words

    def to_dict(self) -> dict:
        """Serialize for DB storage."""
        return {
            "name": self.name,
            "count": self.count,
            "mean": self.mean,
            "m2": self.m2,
            "rolling_delta": self.rolling_delta,
            "consecutive_stable": self.consecutive_stable,
            "converged": self._converged,
            "converged_at_words": self.converged_at_words,
            "category": self._category,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ElementTracker":
        """Restore from DB row."""
        t = cls(data["name"])
        t.count = data["count"]
        t.mean = data["mean"]
        t.m2 = data["m2"]
        t.rolling_delta = data["rolling_delta"]
        t.consecutive_stable = data["consecutive_stable"]
        t._converged = data["converged"]
        t.converged_at_words = data.get("converged_at_words")
        if "category" in data:
            t._category = data["category"]
        return t


class ConvergenceComputer:
    """Computes aggregate completeness across multiple ElementTrackers."""

    def __init__(self):
        self._trackers: list[ElementTracker] = []

    def add_tracker(self, tracker: ElementTracker) -> None:
        self._trackers.append(tracker)

    def compute_completeness(self) -> dict:
        """Return completeness dict with tier, pct, and per-category breakdown."""
        total = len(self._trackers)
        if total == 0:
            return {
                "tier": None,
                "tier_label": None,
                "pct": 0,
                "next_tier": "bronze",
                "next_tier_label": "Bronze",
                "elements_converged": 0,
                "elements_total": 0,
                "categories": {},
            }

        converged_count = sum(1 for t in self._trackers if t._converged)
        pct = int(converged_count * 100 / total)

        # Determine tier (highest threshold met)
        tier = None
        tier_label = None
        next_tier = None
        next_tier_label = None
        # Tiers ordered by threshold ascending
        ordered_tiers = sorted(COMPLETENESS_TIERS.items(), key=lambda x: x[1])
        for t_name, t_threshold in ordered_tiers:
            if pct >= t_threshold:
                tier = t_name
                tier_label = t_name.capitalize()

        # Next tier
        for t_name, t_threshold in ordered_tiers:
            if pct < t_threshold:
                next_tier = t_name
                next_tier_label = t_name.capitalize()
                break

        # Per-category breakdown
        categories: dict[str, dict] = {}
        for tracker in self._trackers:
            cat = tracker._category
            if cat not in categories:
                categories[cat] = {"converged": 0, "total": 0, "status": "needs_more"}
            categories[cat]["total"] += 1
            if tracker._converged:
                categories[cat]["converged"] += 1

        for cat, data in categories.items():
            if data["total"] > 0:
                if data["converged"] == data["total"]:
                    data["status"] = "complete"
                elif data["converged"] / data["total"] >= 0.5:
                    data["status"] = "good"
                else:
                    data["status"] = "needs_more"

        return {
            "tier": tier,
            "tier_label": tier_label,
            "pct": pct,
            "next_tier": next_tier,
            "next_tier_label": next_tier_label,
            "elements_converged": converged_count,
            "elements_total": total,
            "categories": categories,
        }

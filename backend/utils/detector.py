"""Python-based AI text detection heuristics (no AI provider needed).

Implements multiple detection signals:
- Perplexity estimation (vocabulary predictability)
- Burstiness analysis (sentence length variance)
- Stylometric patterns (word choice, structure)
- Voice guide violations (banned words/constructions)
- Readability analysis (Flesch-Kincaid consistency)
- Contraction frequency (AI avoids contractions)
- First-person pronoun frequency
- Passive voice detection
- Adverb density
- Named entity density (specificity)
- Punctuation fingerprinting
- Opening word diversity
"""
import re
import math
from collections import Counter

try:
    import textstat
    HAS_TEXTSTAT = True
except ImportError:
    HAS_TEXTSTAT = False


def detect_ai_patterns(text: str) -> dict:
    """Run all heuristic detectors on text. Returns sentence-level scores."""
    sentences = _split_sentences(text)
    if not sentences:
        return {"overall_score": 0, "sentences": [], "detected_patterns": []}

    sentence_results = []
    all_patterns = []

    for i, sentence in enumerate(sentences):
        score, patterns = _score_sentence(sentence, sentences)
        sentence_results.append({
            "index": i,
            "text": sentence,
            "score": score,
            "patterns": patterns,
        })
        all_patterns.extend(patterns)

    # Aggregate overall score (weighted average favoring high-scoring sentences)
    scores = [s["score"] for s in sentence_results]
    sentence_overall = _weighted_overall(scores)

    # Document-level patterns and scores
    doc_patterns = _document_level_patterns(text, sentences)
    all_patterns.extend(doc_patterns)

    # Document-level score contributions
    doc_scores = []
    read_s, _ = _check_readability(text)
    if read_s > 0:
        doc_scores.append(read_s)
    contr_s, _ = _check_contractions(text)
    if contr_s > 0:
        doc_scores.append(contr_s)
    fp_s, _ = _check_first_person(text)
    if fp_s > 0:
        doc_scores.append(fp_s)
    pass_s, _ = _check_passive_voice(text)
    if pass_s > 0:
        doc_scores.append(pass_s)
    adv_s, _ = _check_adverb_density(text)
    if adv_s > 0:
        doc_scores.append(adv_s)
    ent_s, _ = _check_entity_density(text)
    if ent_s > 0:
        doc_scores.append(ent_s)
    punct_s, _ = _check_punctuation_fingerprint(text)
    if punct_s > 0:
        doc_scores.append(punct_s)
    open_s, _ = _check_opening_diversity(sentences)
    if open_s > 0:
        doc_scores.append(open_s)
    # Phase 2.2 document-level scores
    hedge_cl_s, _ = _check_hedge_clusters(sentences)
    if hedge_cl_s > 0:
        doc_scores.append(hedge_cl_s)
    trans_st_s, _ = _check_transition_stacks(sentences)
    if trans_st_s > 0:
        doc_scores.append(trans_st_s)
    syn_s, _ = _check_synonym_treadmill(text)
    if syn_s > 0:
        doc_scores.append(syn_s)
    emoji_s, _ = _check_emoji_density(text)
    if emoji_s > 0:
        doc_scores.append(emoji_s)
    sensory_s, _ = _check_sensory_checklist(text)
    if sensory_s > 0:
        doc_scores.append(sensory_s)
    self_s, _ = _check_self_contained_paragraphs(text)
    if self_s > 0:
        doc_scores.append(self_s)

    # Blend: 60% sentence-level, 40% document-level
    if doc_scores:
        doc_avg = sum(doc_scores) / len(doc_scores)
        overall = sentence_overall * 0.6 + doc_avg * 0.4
    else:
        overall = sentence_overall

    # Deduplicate pattern names
    unique_patterns = []
    seen = set()
    for p in all_patterns:
        if p["pattern"] not in seen:
            unique_patterns.append(p)
            seen.add(p["pattern"])

    return {
        "overall_score": round(overall, 1),
        "sentences": sentence_results,
        "detected_patterns": unique_patterns,
    }


def _split_sentences(text: str) -> list:
    """Split text into sentences."""
    # Simple sentence splitter - handles common cases
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def _score_sentence(sentence: str, all_sentences: list) -> tuple:
    """Score a single sentence for AI likelihood. Returns (score, patterns)."""
    scores = []
    patterns = []

    # 1. Vocabulary predictability (banned buzzwords)
    buzz_score, buzz_patterns = _check_buzzwords(sentence)
    scores.append(buzz_score)
    patterns.extend(buzz_patterns)

    # 2. Sentence length relative to document
    length_score = _check_length_uniformity(sentence, all_sentences)
    if length_score > 30:
        scores.append(length_score)
        patterns.append({"pattern": "uniform_length", "detail": "Sentence length is very uniform across document"})

    # 3. Hedge word density
    hedge_score, hedge_patterns = _check_hedge_words(sentence)
    scores.append(hedge_score)
    patterns.extend(hedge_patterns)

    # 4. Transition word overuse
    trans_score, trans_patterns = _check_transitions(sentence)
    scores.append(trans_score)
    patterns.extend(trans_patterns)

    # 5. Structural patterns
    struct_score, struct_patterns = _check_structural_patterns(sentence)
    scores.append(struct_score)
    patterns.extend(struct_patterns)

    # 6. Dual-adjective pairing (Voice Guide)
    dual_score, dual_patterns = _check_dual_adjectives(sentence)
    if dual_score > 0:
        scores.append(dual_score)
        patterns.extend(dual_patterns)

    # 7. Trailing participial phrases (Voice Guide Part 3)
    trail_score, trail_patterns = _check_trailing_participial(sentence)
    if trail_score > 0:
        scores.append(trail_score)
        patterns.extend(trail_patterns)

    # 8. Confident declarations (Voice Guide Part 2)
    conf_score, conf_patterns = _check_confident_declarations(sentence)
    if conf_score > 0:
        scores.append(conf_score)
        patterns.extend(conf_patterns)

    # 9. False dichotomy flips (Voice Guide Part 2)
    flip_score, flip_patterns = _check_false_dichotomy(sentence)
    if flip_score > 0:
        scores.append(flip_score)
        patterns.extend(flip_patterns)

    # 10. Emotional exposition (AI tells instead of shows)
    emo_score, emo_patterns = _check_emotional_exposition(sentence)
    if emo_score > 0:
        scores.append(emo_score)
        patterns.extend(emo_patterns)

    # Combine scores: only count non-zero signals to avoid dilution
    nonzero = [s for s in scores if s > 0]
    if nonzero:
        # More signals = higher confidence; avg of hits + bonus for signal count
        avg_hit = sum(nonzero) / len(nonzero)
        signal_bonus = min(30, len(nonzero) * 5)  # up to +30 for 6+ signals
        combined = min(100, avg_hit + signal_bonus)
    else:
        combined = 0
    return round(combined, 1), patterns


def _check_buzzwords(sentence: str) -> tuple:
    """Check for AI-typical buzzwords (expanded from Voice Guide)."""
    # Hard-ban verbs (Voice Guide Part 1)
    hard_ban_verbs = {
        "delve", "navigate", "foster", "leverage", "harness", "empower",
        "unlock", "catalyze", "galvanize", "utilize", "spearhead", "synergize",
        "operationalize", "revolutionize", "supercharge", "elevate", "amplify",
        "streamline", "champion", "evangelize", "pioneer", "facilitate",
        "optimize", "incentivize", "conceptualize", "contextualize",
        "problematize", "underscore", "showcase", "illuminate",
    }
    # Hard-ban adjectives (Voice Guide Part 1)
    hard_ban_adj = {
        "robust", "holistic", "paramount", "transformative", "cutting-edge",
        "seamless", "innovative", "groundbreaking", "comprehensive", "dynamic",
        "game-changing", "best-in-class", "world-class", "state-of-the-art",
        "mission-critical", "enterprise-grade", "multifaceted", "nuanced",
        "pivotal", "compelling", "invaluable", "indispensable", "unparalleled",
        "unprecedented", "myriad",
    }
    # Hard-ban filler / connector words (Voice Guide Part 1-2)
    hard_ban_filler = {
        "furthermore", "moreover", "additionally", "consequently", "nevertheless",
        "paradigm", "ecosystem", "synergy", "landscape", "realm", "tapestry",
        "underpinning", "bedrock", "cornerstone", "linchpin", "crucible",
        "zeitgeist", "ethos", "nexus", "interplay", "juxtaposition",
    }
    buzzwords = hard_ban_verbs | hard_ban_adj | hard_ban_filler

    words = set(re.findall(r'\b\w+\b', sentence.lower()))
    # Also check hyphenated forms
    hyphenated = set(re.findall(r'\b\w+-\w+(?:-\w+)?\b', sentence.lower()))
    all_tokens = words | hyphenated

    found = all_tokens & buzzwords
    # Hard-ban words score higher than before
    score = min(90, len(found) * 30)
    patterns = [{"pattern": "buzzword", "detail": f"AI-typical word: '{w}'"} for w in found]
    return score, patterns


def _check_hedge_words(sentence: str) -> tuple:
    """Check for AI hedging patterns."""
    hedges = [
        r'\bhowever\b', r'\bfurthermore\b', r'\bmoreover\b', r'\badditionally\b',
        r'\bconsequently\b', r'\bnevertheless\b', r'\bnotably\b', r'\bimportantly\b',
        r'\bsignificantly\b', r'\bundoubtedly\b', r'\bultimately\b',
    ]
    found = [h for h in hedges if re.search(h, sentence, re.IGNORECASE)]
    score = min(60, len(found) * 20)
    patterns = [{"pattern": "hedge_word", "detail": f"AI-typical hedge: {h}"} for h in found]
    return score, patterns


def _check_transitions(sentence: str) -> tuple:
    """Check for AI-typical transition patterns."""
    transitions = [
        r'^(In conclusion|To summarize|In summary|Overall|In essence)',
        r'^(It is worth noting|It should be noted|It is important to)',
        r'^(This (demonstrates|illustrates|highlights|underscores|showcases))',
        r'^(By (leveraging|utilizing|harnessing|implementing))',
    ]
    found = [t for t in transitions if re.search(t, sentence, re.IGNORECASE)]
    score = min(70, len(found) * 35)
    patterns = [{"pattern": "ai_transition", "detail": "AI-typical opening pattern"} for _ in found]
    return score, patterns


def _check_structural_patterns(sentence: str) -> tuple:
    """Check for structural AI tells."""
    patterns_found = []
    score = 0

    # "Not only X but also Y" pattern
    if re.search(r'not only .+ but also', sentence, re.IGNORECASE):
        patterns_found.append({"pattern": "not_only_but_also", "detail": "AI-typical parallel construction"})
        score += 25

    # "It is [adjective] to [verb]" pattern
    if re.search(r'it is \w+ to \w+', sentence, re.IGNORECASE):
        patterns_found.append({"pattern": "it_is_adj_to", "detail": "AI-typical impersonal construction"})
        score += 15

    # List of three with "and" (rule of three) — score higher if repeated in doc
    if re.search(r'\w+, \w+, and \w+', sentence):
        patterns_found.append({"pattern": "rule_of_three", "detail": "AI favors triadic lists"})
        score += 15

    # Hedging sandwich: bold claim → soften → bold claim (Voice Guide Part 3)
    if re.search(r'(certainly|clearly|undoubtedly|obviously).{10,}(however|but|although|though|yet).{10,}(still|nevertheless|ultimately|nonetheless)', sentence, re.IGNORECASE):
        patterns_found.append({"pattern": "hedging_sandwich", "detail": "Bold → soften → bold hedging sandwich"})
        score += 25

    # Front-loaded description dump: heavy adjective/adverb opening
    words = sentence.split()
    if len(words) > 12:
        first_half = ' '.join(words[:len(words)//2]).lower()
        adj_count = len(re.findall(r'\b(the|a|an)\s+\w+\s+\w+\s+(and\s+)?\w+', first_half))
        if adj_count >= 2:
            patterns_found.append({"pattern": "front_loaded_description", "detail": "Heavy descriptive front-loading before action"})
            score += 10

    return score, patterns_found


def _check_dual_adjectives(sentence: str) -> tuple:
    """Check for AI-typical dual-adjective pairing: 'rich and complex', 'bold and innovative'."""
    patterns = []
    # Pattern: adjective + "and" + adjective (Voice Guide: AI pairs adjectives compulsively)
    matches = re.findall(
        r'\b(\w+)\s+and\s+(\w+)\b',
        sentence.lower()
    )
    # Filter to likely adjective pairs (rough heuristic: common AI pairings)
    ai_adj_pairs = {
        "rich", "complex", "bold", "innovative", "nuanced", "layered",
        "diverse", "inclusive", "dynamic", "vibrant", "profound", "meaningful",
        "unique", "powerful", "compelling", "engaging", "thoughtful", "intentional",
        "strategic", "holistic", "robust", "seamless", "elegant", "sophisticated",
        "comprehensive", "transformative", "authentic", "genuine", "deep", "broad",
    }
    pair_count = 0
    for w1, w2 in matches:
        if w1 in ai_adj_pairs and w2 in ai_adj_pairs:
            pair_count += 1

    score = 0
    if pair_count >= 1:
        score = 25 * pair_count
        patterns.append({
            "pattern": "dual_adjective_pair",
            "detail": f"Found {pair_count} AI-typical adjective pair(s) — AI compulsively pairs adjectives"
        })
    return min(50, score), patterns


def _check_trailing_participial(sentence: str) -> tuple:
    """Check for trailing participial phrases: sentences ending with ', [verb]ing...'."""
    patterns = []
    score = 0
    # Voice Guide Part 3: "her voice barely above a whisper, trembling"
    if re.search(r',\s+\w+ing\b[^.]*[.!?]?$', sentence):
        score = 20
        patterns.append({
            "pattern": "trailing_participial",
            "detail": "Sentence ends with trailing participial phrase — AI structural tell"
        })
    return score, patterns


def _check_confident_declarations(sentence: str) -> tuple:
    """Check for AI confident declarations: 'Full stop.', 'Let that sink in.', 'And that's okay.'"""
    patterns = []
    score = 0
    declarations = [
        r'\bfull stop\b',
        r'\blet that sink in\b',
        r"\band that'?s? okay\b",
        r"\band that'?s? fine\b",
        r'\bread that again\b',
        r'\bperiod\.\s*$',
        r'\bthink about that\b',
        r'\blet me be clear\b',
        r'\bmake no mistake\b',
        r'\bhere\'?s? the (thing|truth|reality|kicker)\b',
        r'\bthe bottom line\b',
    ]
    found = [d for d in declarations if re.search(d, sentence, re.IGNORECASE)]
    if found:
        score = 35
        patterns.append({
            "pattern": "confident_declaration",
            "detail": "AI-typical confident declaration / mic-drop phrase"
        })
    return score, patterns


def _check_false_dichotomy(sentence: str) -> tuple:
    """Check for false dichotomy flips: 'It's not about X. It's about Y.'"""
    patterns = []
    score = 0
    # Voice Guide Part 2: "It's not about X. It's about Y."
    dichotomy_patterns = [
        r"it'?s?\s+not\s+(about|just|merely|simply)\b.*\bit'?s?\s+(about|really)",
        r"(this|that|it)\s+isn'?t\s+(about|just)\b",
        r"the (question|issue|point|problem)\s+isn'?t\b.*\bit'?s\b",
        r"don'?t\s+\w+\s*[.;]\s*(instead|rather)\b",
        r"stop\s+\w+ing\b.*\bstart\s+\w+ing\b",
    ]
    found = [p for p in dichotomy_patterns if re.search(p, sentence, re.IGNORECASE)]
    if found:
        score = 30
        patterns.append({
            "pattern": "false_dichotomy",
            "detail": "AI-typical 'not about X, about Y' false dichotomy flip"
        })
    return score, patterns


def _check_emotional_exposition(sentence: str) -> tuple:
    """Check for AI emotional exposition: 'She felt a pang of...', 'A wave of sadness...'"""
    patterns = []
    score = 0
    emotional_patterns = [
        r'\bfelt\s+a\s+(pang|wave|rush|surge|flutter|stab|twinge|jolt)\s+of\b',
        r'\ba\s+(wave|surge|rush|flood|pang)\s+of\s+(sadness|joy|emotion|grief|relief|anger|anxiety|guilt|shame|pride|nostalgia)\b',
        r'\b(heart|stomach|chest)\s+(sank|clenched|tightened|fluttered|ached|swelled)\b',
        r'\btears\s+(pricked|stung|welled|burned)\b',
        r'\bbreath\s+(caught|hitched)\b',
        r'\bsomething\s+(shifted|stirred|broke|snapped)\s+(in|inside|within)\b',
    ]
    found = [p for p in emotional_patterns if re.search(p, sentence, re.IGNORECASE)]
    if found:
        score = 30
        patterns.append({
            "pattern": "emotional_exposition",
            "detail": "AI tells emotions instead of showing — 'felt a pang of' / 'a wave of sadness'"
        })
    return score, patterns


def _check_length_uniformity(sentence: str, all_sentences: list) -> float:
    """Score based on how uniform sentence lengths are (improved burstiness)."""
    if len(all_sentences) < 3:
        return 0
    lengths = [len(s.split()) for s in all_sentences]
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return 0
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance) if variance > 0 else 0

    # Coefficient of variation: low = uniform = AI-like
    cv = std_dev / mean_len
    # Also check if most sentences cluster in AI-typical 15-20 word range
    in_ai_range = sum(1 for l in lengths if 12 <= l <= 22) / len(lengths)

    score = 0
    if cv < 0.15:
        score = 60  # Very uniform
    elif cv < 0.25:
        score = 35  # Somewhat uniform
    elif cv < 0.35:
        score = 15  # Mildly uniform

    # Bonus if sentences cluster in the AI sweet spot
    if in_ai_range > 0.7:
        score = min(80, score + 20)

    return score


def _count_syllables(word: str) -> int:
    """Estimate syllable count for a word."""
    word = word.lower().rstrip('e')
    if not word:
        return 1
    count = len(re.findall(r'[aeiouy]+', word))
    return max(1, count)


def _flesch_kincaid_grade(text: str) -> float:
    """Calculate Flesch-Kincaid grade level."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r'\b\w+\b', text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)  # avg sentence length
    asw = syllables / len(words)  # avg syllables per word
    return 0.39 * asl + 11.8 * asw - 15.59


def _flesch_reading_ease(text: str) -> float:
    """Calculate Flesch reading ease score."""
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    words = re.findall(r'\b\w+\b', text)
    if not sentences or not words:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    asl = len(words) / len(sentences)
    asw = syllables / len(words)
    return 206.835 - 1.015 * asl - 84.6 * asw


def _check_readability(text: str) -> tuple:
    """Check readability consistency — AI produces mid-range Flesch-Kincaid scores."""
    score = 0
    patterns = []

    if len(text.split()) < 30:
        return 0, []

    if HAS_TEXTSTAT:
        fk_grade = textstat.flesch_kincaid_grade(text)
        flesch_ease = textstat.flesch_reading_ease(text)
    else:
        fk_grade = _flesch_kincaid_grade(text)
        flesch_ease = _flesch_reading_ease(text)

    # AI tends to produce text in the 8-12 grade range (professional but accessible)
    if 8.0 <= fk_grade <= 12.0:
        score += 25
        patterns.append({
            "pattern": "mid_range_readability",
            "detail": f"Flesch-Kincaid grade {fk_grade:.1f} is in AI-typical range (8-12)"
        })

    # AI tends to produce reading ease 40-60 (fairly difficult to standard)
    if 40 <= flesch_ease <= 65:
        score += 15
        patterns.append({
            "pattern": "uniform_reading_ease",
            "detail": f"Flesch reading ease {flesch_ease:.0f} is in AI-typical range (40-65)"
        })

    return score, patterns


def _check_contractions(text: str) -> tuple:
    """Check contraction frequency — AI avoids contractions."""
    patterns = []

    # Common contractions
    contraction_re = re.compile(
        r"\b(i'm|i've|i'll|i'd|we're|we've|we'll|we'd|"
        r"you're|you've|you'll|you'd|they're|they've|they'll|they'd|"
        r"he's|she's|it's|that's|there's|here's|what's|who's|"
        r"isn't|aren't|wasn't|weren't|hasn't|haven't|hadn't|"
        r"doesn't|don't|didn't|won't|wouldn't|can't|couldn't|"
        r"shouldn't|mustn't|let's|ain't)\b", re.IGNORECASE
    )
    # Expanded forms that could be contracted
    expandable_re = re.compile(
        r"\b(I am|I have|I will|I would|we are|we have|we will|we would|"
        r"you are|you have|you will|you would|they are|they have|they will|they would|"
        r"he is|she is|it is|that is|there is|here is|what is|who is|"
        r"is not|are not|was not|were not|has not|have not|had not|"
        r"does not|do not|did not|will not|would not|can not|cannot|could not|"
        r"should not|must not|let us)\b", re.IGNORECASE
    )

    contractions = len(contraction_re.findall(text))
    expandable = len(expandable_re.findall(text))
    total = contractions + expandable

    if total < 3:
        return 0, []

    contraction_ratio = contractions / total
    score = 0

    # Very low contraction usage = AI signal
    if contraction_ratio < 0.15:
        score = 50
        patterns.append({
            "pattern": "no_contractions",
            "detail": f"Only {contraction_ratio:.0%} contractions used ({contractions}/{total}) — AI avoids contractions"
        })
    elif contraction_ratio < 0.3:
        score = 25
        patterns.append({
            "pattern": "low_contractions",
            "detail": f"Low contraction usage ({contraction_ratio:.0%}) — AI tends to use expanded forms"
        })

    return score, patterns


def _check_first_person(text: str) -> tuple:
    """Check first-person pronoun frequency — AI underuses 'I', 'me', 'my' in personal writing."""
    patterns = []
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < 30:
        return 0, []

    first_person = {"i", "me", "my", "mine", "myself", "we", "us", "our", "ours", "ourselves"}
    fp_count = sum(1 for w in words if w in first_person)
    fp_ratio = fp_count / len(words)

    # Very low first-person usage can signal AI (especially in personal/narrative text)
    # But this is context-dependent, so we keep the signal mild
    score = 0
    if fp_ratio < 0.005:
        score = 20
        patterns.append({
            "pattern": "no_first_person",
            "detail": "No first-person pronouns — AI defaults to impersonal voice"
        })
    elif fp_ratio < 0.015:
        score = 10
        patterns.append({
            "pattern": "low_first_person",
            "detail": f"Low first-person pronoun usage ({fp_ratio:.1%}) — AI underuses personal voice"
        })

    return score, patterns


def _check_passive_voice(text: str) -> tuple:
    """Check passive voice frequency — AI overuses passive constructions."""
    patterns = []

    # Match common passive patterns: "is/was/were/been/being + past participle"
    passive_re = re.compile(
        r'\b(is|are|was|were|been|being|be)\s+'
        r'(\w+ly\s+)?'  # optional adverb
        r'(\w+ed|built|made|seen|done|taken|given|found|known|shown|written|'
        r'driven|spoken|broken|chosen|forgotten|hidden|proven|stolen|worn)\b',
        re.IGNORECASE
    )

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    if len(sentences) < 3:
        return 0, []

    passive_count = sum(1 for s in sentences if passive_re.search(s))
    passive_ratio = passive_count / len(sentences)

    score = 0
    if passive_ratio > 0.5:
        score = 40
        patterns.append({
            "pattern": "high_passive_voice",
            "detail": f"{passive_ratio:.0%} of sentences use passive voice — AI defaults to passive"
        })
    elif passive_ratio > 0.35:
        score = 20
        patterns.append({
            "pattern": "elevated_passive_voice",
            "detail": f"{passive_ratio:.0%} passive voice sentences — above natural frequency"
        })

    return score, patterns


def _check_adverb_density(text: str) -> tuple:
    """Check adverb density — AI over-relies on -ly adverbs for emphasis."""
    patterns = []
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < 30:
        return 0, []

    # Common -ly adverbs AI overuses (exclude common non-adverbs ending in -ly)
    not_adverbs = {"family", "only", "early", "likely", "friendly", "lonely",
                   "ugly", "holy", "daily", "weekly", "monthly", "yearly",
                   "rally", "belly", "jelly", "bully", "ally", "supply", "apply",
                   "reply", "fly", "july", "italy"}
    ly_adverbs = [w for w in words if w.endswith("ly") and len(w) > 3 and w not in not_adverbs]

    # Also check for intensifier adverbs AI loves
    intensifiers = {"significantly", "dramatically", "fundamentally", "incredibly",
                    "remarkably", "exceptionally", "profoundly", "thoroughly",
                    "effectively", "efficiently", "seamlessly", "effortlessly",
                    "meticulously", "strategically", "inherently", "ultimately"}
    intensifier_count = sum(1 for w in ly_adverbs if w in intensifiers)

    adverb_ratio = len(ly_adverbs) / len(words)
    score = 0

    if adverb_ratio > 0.06:
        score = 40
        patterns.append({
            "pattern": "high_adverb_density",
            "detail": f"Adverb density {adverb_ratio:.1%} — AI over-relies on -ly adverbs"
        })
    elif adverb_ratio > 0.04:
        score = 20
        patterns.append({
            "pattern": "elevated_adverb_density",
            "detail": f"Adverb density {adverb_ratio:.1%} — above typical human writing"
        })

    if intensifier_count >= 2:
        score = min(60, score + 20)
        patterns.append({
            "pattern": "ai_intensifiers",
            "detail": f"Found {intensifier_count} AI-typical intensifier adverbs"
        })

    return score, patterns


def _check_entity_density(text: str) -> tuple:
    """Check named entity density — AI is vague, humans use specifics."""
    patterns = []
    words = re.findall(r'\b\w+\b', text)
    if len(words) < 30:
        return 0, []

    # Heuristic entity detection (no NER model needed):
    # Proper nouns (capitalized words not at sentence start)
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    proper_nouns = 0
    for sent in sentences:
        sent_words = sent.split()
        # Skip first word (sentence start is always capitalized)
        for w in sent_words[1:]:
            if w[0:1].isupper() and w.isalpha() and len(w) > 1:
                proper_nouns += 1

    # Numbers and dates
    numbers = len(re.findall(r'\b\d+[\d,.]*\b', text))

    # Specific markers (dollar amounts, percentages, years, times)
    specifics = len(re.findall(r'(\$[\d,.]+|\d+%|\b(19|20)\d{2}\b|\d{1,2}:\d{2})', text))

    entity_count = proper_nouns + numbers + specifics
    entity_ratio = entity_count / len(words)

    score = 0
    if entity_ratio < 0.01 and len(words) > 50:
        score = 35
        patterns.append({
            "pattern": "no_specifics",
            "detail": "Almost no specific names, numbers, or dates — AI defaults to vague abstractions"
        })
    elif entity_ratio < 0.025 and len(words) > 50:
        score = 15
        patterns.append({
            "pattern": "low_specifics",
            "detail": f"Low entity density ({entity_ratio:.1%}) — few concrete details"
        })

    return score, patterns


def _check_punctuation_fingerprint(text: str) -> tuple:
    """Check punctuation patterns — AI overuses em dashes, avoids irregular punctuation."""
    patterns = []
    words = re.findall(r'\b\w+\b', text)
    if len(words) < 30:
        return 0, []

    word_count = len(words)
    score = 0

    # Em dash overuse (AI loves em dashes)
    em_dashes = len(re.findall(r'[—–]', text))
    em_ratio = em_dashes / word_count
    if em_ratio > 0.015:
        score += 25
        patterns.append({
            "pattern": "em_dash_overuse",
            "detail": f"Em dash density {em_ratio:.1%} — AI overuses em dashes"
        })

    # Comma density (AI tends toward high, regular comma usage)
    commas = text.count(',')
    comma_ratio = commas / word_count
    if comma_ratio > 0.08:
        score += 15
        patterns.append({
            "pattern": "high_comma_density",
            "detail": f"Comma density {comma_ratio:.1%} — AI produces highly punctuated prose"
        })

    # Semicolon usage (AI uses semicolons more than typical humans)
    semicolons = text.count(';')
    if semicolons >= 2 and semicolons / word_count > 0.005:
        score += 10
        patterns.append({
            "pattern": "semicolon_overuse",
            "detail": f"Found {semicolons} semicolons — above typical human frequency"
        })

    # Lack of irregular punctuation (humans use !, ..., ?, parentheticals more freely)
    exclamations = text.count('!')
    ellipses = len(re.findall(r'\.{3}|…', text))
    parens = text.count('(')
    irregular = exclamations + ellipses + parens
    if irregular == 0 and word_count > 80:
        score += 15
        patterns.append({
            "pattern": "no_irregular_punctuation",
            "detail": "No exclamations, ellipses, or parentheticals — AI writes sanitized prose"
        })

    return min(50, score), patterns


def _check_opening_diversity(sentences: list) -> tuple:
    """Check sentence/paragraph opening word diversity — AI repeats openers."""
    patterns = []
    if len(sentences) < 5:
        return 0, []

    openers = []
    for s in sentences:
        words = s.strip().split()
        if words:
            openers.append(words[0].lower().rstrip(','))

    # Check how many unique openers vs total
    opener_counts = Counter(openers)
    unique_ratio = len(opener_counts) / len(openers)

    score = 0

    # AI-typical openers
    ai_openers = {"the", "this", "these", "those", "it", "in", "by", "with", "from", "as"}
    ai_opener_count = sum(c for w, c in opener_counts.items() if w in ai_openers)
    ai_opener_ratio = ai_opener_count / len(openers)

    if unique_ratio < 0.4:
        score = 40
        most_common = opener_counts.most_common(3)
        top_words = ", ".join(f"'{w}' ({c}x)" for w, c in most_common)
        patterns.append({
            "pattern": "repetitive_openers",
            "detail": f"Only {unique_ratio:.0%} unique sentence openers — top: {top_words}"
        })
    elif unique_ratio < 0.55:
        score = 20
        patterns.append({
            "pattern": "low_opener_diversity",
            "detail": f"Low sentence opener diversity ({unique_ratio:.0%} unique)"
        })

    if ai_opener_ratio > 0.6:
        score = min(50, score + 15)
        patterns.append({
            "pattern": "ai_typical_openers",
            "detail": f"{ai_opener_ratio:.0%} of sentences start with AI-typical words (The, This, It, In...)"
        })

    return score, patterns


def _check_hedge_clusters(sentences: list) -> tuple:
    """Check for hedge word clustering — AI stacks hedges in adjacent sentences."""
    patterns = []
    hedge_words = {
        "however", "furthermore", "moreover", "additionally", "consequently",
        "nevertheless", "notably", "importantly", "significantly", "ultimately",
        "it's worth noting", "it should be noted", "it is important to note",
        "interestingly", "remarkably", "arguably", "admittedly",
    }
    # Count hedges per sentence
    hedge_per_sent = []
    for s in sentences:
        s_lower = s.lower()
        count = sum(1 for h in hedge_words if h in s_lower)
        hedge_per_sent.append(count)

    # Look for clusters: 3+ consecutive sentences with hedges
    score = 0
    max_run = 0
    current_run = 0
    for count in hedge_per_sent:
        if count > 0:
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0

    if max_run >= 4:
        score = 45
        patterns.append({
            "pattern": "hedge_cluster",
            "detail": f"{max_run} consecutive sentences contain hedge words — AI stacks hedges"
        })
    elif max_run >= 3:
        score = 25
        patterns.append({
            "pattern": "hedge_cluster",
            "detail": f"{max_run} consecutive hedged sentences — above natural frequency"
        })

    return score, patterns


def _check_transition_stacks(sentences: list) -> tuple:
    """Check for adverbial transition stacks — paragraphs starting with Moreover/Furthermore/etc."""
    patterns = []
    stack_starters = {
        "moreover", "furthermore", "additionally", "consequently", "subsequently",
        "similarly", "likewise", "conversely", "nevertheless", "nonetheless",
        "in addition", "as a result", "on the other hand", "in contrast",
    }

    stack_count = 0
    for s in sentences:
        s_lower = s.strip().lower()
        if any(s_lower.startswith(t) for t in stack_starters):
            stack_count += 1

    score = 0
    if len(sentences) >= 3:
        ratio = stack_count / len(sentences)
        if ratio > 0.4:
            score = 45
            patterns.append({
                "pattern": "transition_stacks",
                "detail": f"{ratio:.0%} of sentences open with adverbial transitions — AI connector overuse"
            })
        elif ratio > 0.25:
            score = 25
            patterns.append({
                "pattern": "transition_stacks",
                "detail": f"{ratio:.0%} adverbial transition openers — above natural writing"
            })

    return score, patterns


def _check_synonym_treadmill(text: str) -> tuple:
    """Check for elegant variation / synonym treadmill — using different words for same concept."""
    patterns = []
    # Common AI synonym clusters (using different fancy words for the same thing)
    synonym_groups = [
        {"important", "crucial", "vital", "essential", "critical", "paramount", "pivotal", "key", "fundamental"},
        {"help", "assist", "aid", "support", "facilitate", "enable", "empower"},
        {"show", "demonstrate", "illustrate", "highlight", "showcase", "underscore", "exemplify"},
        {"use", "utilize", "leverage", "harness", "employ", "deploy", "implement"},
        {"make", "create", "craft", "forge", "build", "develop", "construct", "establish"},
        {"change", "transform", "revolutionize", "reshape", "redefine", "reimagine", "reinvent"},
        {"big", "significant", "substantial", "considerable", "noteworthy", "remarkable", "profound"},
        {"improve", "enhance", "elevate", "optimize", "refine", "strengthen", "bolster", "augment"},
    ]

    words = re.findall(r'\b\w+\b', text.lower())
    word_set = set(words)
    score = 0
    treadmill_count = 0

    for group in synonym_groups:
        used = word_set & group
        if len(used) >= 3:
            treadmill_count += 1

    if treadmill_count >= 3:
        score = 40
        patterns.append({
            "pattern": "synonym_treadmill",
            "detail": f"{treadmill_count} synonym clusters detected — AI rotates fancy words for same concept"
        })
    elif treadmill_count >= 2:
        score = 20
        patterns.append({
            "pattern": "synonym_treadmill",
            "detail": f"{treadmill_count} synonym clusters — possible elegant variation"
        })

    return score, patterns


def _check_emoji_density(text: str) -> tuple:
    """Check for excessive/performative emoji use in casual text."""
    patterns = []
    # Match common emoji Unicode ranges
    emoji_re = re.compile(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000FE00-\U0000FE0F\U0000200D]'
    )
    emojis = emoji_re.findall(text)
    words = re.findall(r'\b\w+\b', text)
    if not words:
        return 0, []

    emoji_ratio = len(emojis) / len(words)
    score = 0
    if emoji_ratio > 0.1:
        score = 30
        patterns.append({
            "pattern": "emoji_overuse",
            "detail": f"Emoji density {emoji_ratio:.0%} — performative emoji use common in AI text"
        })
    elif emoji_ratio > 0.05 and len(emojis) >= 3:
        score = 15
        patterns.append({
            "pattern": "elevated_emoji",
            "detail": f"Found {len(emojis)} emojis — above typical density"
        })

    return score, patterns


def _check_sensory_checklist(text: str) -> tuple:
    """Check for systematic sensory rotation — AI cycles through sight/sound/smell/touch/taste."""
    patterns = []
    senses = {
        "sight": re.compile(r'\b(saw|gazed|watched|looked|glanced|stared|peered|observed|glimpsed|noticed|eye|vision|bright|dark|glow|shimmer|gleam)\b', re.I),
        "sound": re.compile(r'\b(heard|listened|whispered|murmured|echoed|hummed|rang|crackled|rustled|silence|voice|sound|noise|quiet)\b', re.I),
        "smell": re.compile(r'\b(smelled|scent|aroma|fragrance|stench|whiff|pungent|musty|fresh|perfume|odor)\b', re.I),
        "touch": re.compile(r'\b(felt|touched|rough|smooth|soft|hard|warm|cold|cool|texture|fingers|skin|grip|grasp|caress)\b', re.I),
        "taste": re.compile(r'\b(tasted|flavor|sweet|bitter|sour|salty|savory|tongue|mouth|palate|delicious)\b', re.I),
    }

    senses_found = sum(1 for s_re in senses.values() if s_re.search(text))
    score = 0

    if senses_found >= 4:
        score = 35
        patterns.append({
            "pattern": "sensory_checklist",
            "detail": f"{senses_found}/5 senses covered — AI systematically rotates through sensory details"
        })
    elif senses_found >= 3:
        score = 15
        patterns.append({
            "pattern": "sensory_rotation",
            "detail": f"{senses_found}/5 senses represented — possible systematic sensory coverage"
        })

    return score, patterns


def _check_self_contained_paragraphs(text: str) -> tuple:
    """Check if paragraphs are self-contained with no threads across them."""
    patterns = []
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) < 3:
        return 0, []

    # Check for cross-paragraph references (pronouns, demonstratives that connect)
    connectors = re.compile(
        r'^(This|These|That|Those|Such|Here|The above|As mentioned|'
        r'Building on|Continuing|Following|Returning to)\b', re.IGNORECASE
    )
    # Check how many paragraphs start with a connecting reference
    connected = sum(1 for p in paragraphs[1:] if connectors.match(p.strip()))
    connection_ratio = connected / (len(paragraphs) - 1)

    score = 0
    # Very low connection between paragraphs = AI self-containment
    if connection_ratio < 0.1 and len(paragraphs) >= 4:
        score = 30
        patterns.append({
            "pattern": "self_contained_paragraphs",
            "detail": "Paragraphs are self-contained with no connecting threads — AI structural tell"
        })

    return score, patterns


def _document_level_patterns(text: str, sentences: list) -> list:
    """Check for document-level AI patterns."""
    patterns = []

    # Check paragraph length uniformity
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 2:
        para_lengths = [len(p.split()) for p in paragraphs]
        mean_len = sum(para_lengths) / len(para_lengths)
        if mean_len > 0:
            variance = sum((l - mean_len) ** 2 for l in para_lengths) / len(para_lengths)
            cv = math.sqrt(variance) / mean_len
            if cv < 0.2:
                patterns.append({
                    "pattern": "uniform_paragraphs",
                    "detail": f"Paragraph length CV={cv:.2f} — suspiciously uniform (AI-typical)"
                })
            elif cv < 0.3:
                patterns.append({
                    "pattern": "low_paragraph_variance",
                    "detail": f"Paragraph length CV={cv:.2f} — below natural variation"
                })

            # Check if paragraphs cluster in AI-typical 3-5 sentence range
            para_sent_counts = [len(re.split(r'(?<=[.!?])\s+', p.strip())) for p in paragraphs]
            in_ai_range = sum(1 for c in para_sent_counts if 3 <= c <= 5) / len(para_sent_counts)
            if in_ai_range > 0.7 and len(paragraphs) > 2:
                patterns.append({
                    "pattern": "uniform_para_sentences",
                    "detail": f"{in_ai_range:.0%} of paragraphs have 3-5 sentences — AI-typical uniformity"
                })

    # Check vocabulary richness (type-token ratio)
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) > 50:
        ttr = len(set(words)) / len(words)
        if ttr < 0.4:
            patterns.append({
                "pattern": "low_vocabulary_richness",
                "detail": f"Type-token ratio {ttr:.2f} suggests repetitive vocabulary"
            })

    # Readability analysis (document-level)
    read_score, read_patterns = _check_readability(text)
    patterns.extend(read_patterns)

    # Contraction analysis (document-level)
    contr_score, contr_patterns = _check_contractions(text)
    patterns.extend(contr_patterns)

    # First-person pronoun analysis (document-level)
    fp_score, fp_patterns = _check_first_person(text)
    patterns.extend(fp_patterns)

    # Passive voice analysis (document-level)
    passive_score, passive_patterns = _check_passive_voice(text)
    patterns.extend(passive_patterns)

    # Adverb density (document-level)
    adverb_score, adverb_patterns = _check_adverb_density(text)
    patterns.extend(adverb_patterns)

    # Entity density (document-level)
    entity_score, entity_patterns = _check_entity_density(text)
    patterns.extend(entity_patterns)

    # Punctuation fingerprint (document-level)
    punct_score, punct_patterns = _check_punctuation_fingerprint(text)
    patterns.extend(punct_patterns)

    # Opening word diversity (document-level)
    opener_score, opener_patterns = _check_opening_diversity(sentences)
    patterns.extend(opener_patterns)

    # --- Phase 2.2 document-level patterns ---

    # Hedge word clustering
    hedge_cl_score, hedge_cl_patterns = _check_hedge_clusters(sentences)
    patterns.extend(hedge_cl_patterns)

    # Adverbial transition stacks
    trans_st_score, trans_st_patterns = _check_transition_stacks(sentences)
    patterns.extend(trans_st_patterns)

    # Synonym treadmill / elegant variation
    syn_score, syn_patterns = _check_synonym_treadmill(text)
    patterns.extend(syn_patterns)

    # Emoji density
    emoji_score, emoji_patterns = _check_emoji_density(text)
    patterns.extend(emoji_patterns)

    # Sensory checklist
    sensory_score, sensory_patterns = _check_sensory_checklist(text)
    patterns.extend(sensory_patterns)

    # Self-contained paragraphs
    self_score, self_patterns = _check_self_contained_paragraphs(text)
    patterns.extend(self_patterns)

    return patterns


def _weighted_overall(scores: list) -> float:
    """Calculate weighted overall score, favoring high-scoring sentences."""
    if not scores:
        return 0
    # Weight high scores more heavily
    weighted = sum(s * (1 + s / 100) for s in scores)
    total_weight = sum(1 + s / 100 for s in scores)
    return weighted / total_weight if total_weight > 0 else 0

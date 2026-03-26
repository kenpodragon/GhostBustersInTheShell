"""
ETL script: Parse VOICE_GUIDE.md and seed voice_profiles, profile_elements,
profile_prompts, and detection_rules tables.

Usage:
    # From inside the ghostbusters-app container:
    docker exec ghostbusters-app python tools/load_voice_guide.py /data/VOICE_GUIDE.md

    # Or mount and run locally (needs psycopg2 + env vars):
    python code/tools/load_voice_guide.py path/to/VOICE_GUIDE.md
"""

import sys
import os
import re
import json

# When running inside the container, backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import psycopg2
import psycopg2.extras


# ---------------------------------------------------------------------------
# Database connection (standalone, doesn't use Flask app pool)
# ---------------------------------------------------------------------------

def get_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5566')),
        dbname=os.getenv('DB_NAME', 'ghostbusters'),
        user=os.getenv('DB_USER', 'ghostbusters'),
        password=os.getenv('DB_PASSWORD', 'ghostbusters_dev'),
    )


# ---------------------------------------------------------------------------
# Parser: VOICE_GUIDE.md -> structured parts
# ---------------------------------------------------------------------------

PART_RE = re.compile(r'^## PART (\d+[A-Z]?):?\s*(.*)', re.IGNORECASE)
H3_RE = re.compile(r'^### (.*)')

def parse_voice_guide(filepath):
    """Parse the voice guide into a list of parts, each with sections."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    parts = []
    current_part = None
    current_section = None

    for line in lines:
        line_stripped = line.rstrip('\n')

        # Check for part header (## PART N: Title)
        m = PART_RE.match(line_stripped)
        if m:
            if current_section and current_part:
                current_part['sections'].append(current_section)
            if current_part:
                parts.append(current_part)
            current_part = {
                'part_num': m.group(1),
                'title': m.group(2).strip(),
                'sections': [],
            }
            current_section = None
            continue

        # Check for section header (### Title)
        m = H3_RE.match(line_stripped)
        if m:
            if current_section and current_part:
                current_part['sections'].append(current_section)
            current_section = {
                'title': m.group(1).strip(),
                'lines': [],
            }
            continue

        # Also capture ## Quick Reference as its own section under current part
        if line_stripped.startswith('## ') and not PART_RE.match(line_stripped):
            if current_section and current_part:
                current_part['sections'].append(current_section)
            current_section = {
                'title': line_stripped.lstrip('#').strip(),
                'lines': [],
            }
            continue

        # Accumulate content lines
        if current_section is not None:
            current_section['lines'].append(line_stripped)
        elif current_part is not None:
            # Lines before first section in a part — store as intro
            if 'intro_lines' not in current_part:
                current_part['intro_lines'] = []
            current_part['intro_lines'].append(line_stripped)

    # Flush last section/part
    if current_section and current_part:
        current_part['sections'].append(current_section)
    if current_part:
        parts.append(current_part)

    return parts


# ---------------------------------------------------------------------------
# Extract banned words from Part 1
# ---------------------------------------------------------------------------

def extract_banned_words(parts):
    """Extract banned word lists from Part 1 for detection_rules seeding."""
    rules = []
    part1 = next((p for p in parts if p['part_num'] == '1'), None)
    if not part1:
        return rules

    for section in part1['sections']:
        body = '\n'.join(section['lines'])

        # Find bold-labeled word lists like **Buzzword Verbs:**
        pattern = re.compile(r'\*\*([^*]+):\*\*\s*\n?(.*?)(?=\n\*\*|\n###|\n---|\Z)', re.DOTALL)
        for m in pattern.finditer(body):
            subcategory = m.group(1).strip()
            words_text = m.group(2).strip()
            # Parse comma-separated words, strip parenthetical notes
            words = []
            for w in re.split(r',\s*', words_text):
                w = re.sub(r'\s*\(.*?\)\s*', '', w).strip().strip('"').strip('\u201c').strip('\u201d')
                if w and len(w) < 80:
                    words.append(w)
            for word in words:
                rules.append({
                    'category': 'buzzword',
                    'subcategory': subcategory.lower().replace(' ', '_'),
                    'rule_text': word.lower(),
                    'weight': 1.0 if 'never' in section['title'].lower() or 'hard ban' in section['title'].lower() else 0.5,
                    'explanation': f"From Part 1 > {section['title']} > {subcategory}",
                })

    return rules


# ---------------------------------------------------------------------------
# Extract banned constructions from Part 2
# ---------------------------------------------------------------------------

def extract_constructions(parts):
    """Extract banned constructions from Part 2."""
    rules = []
    part2 = next((p for p in parts if p['part_num'] == '2'), None)
    if not part2:
        return rules

    for section in part2['sections']:
        body = '\n'.join(section['lines'])
        # Find lines starting with - " (quoted banned phrases)
        for m in re.finditer(r'^-\s*"([^"]+)"', body, re.MULTILINE):
            phrase = m.group(1).strip().rstrip('.')
            rules.append({
                'category': 'construction',
                'subcategory': section['title'].lower().replace(' ', '_'),
                'rule_text': phrase.lower(),
                'weight': 1.0,
                'explanation': f"From Part 2 > {section['title']}",
            })

    return rules


# ---------------------------------------------------------------------------
# Extract AI patterns from Parts 5, 6B
# ---------------------------------------------------------------------------

def extract_ai_patterns(parts):
    """Extract AI-specific pattern rules."""
    rules = []
    for part in parts:
        if part['part_num'] not in ('5', '6B'):
            continue
        for section in part['sections']:
            if 'anti-ai' not in section['title'].lower() and 'pattern' not in section['title'].lower() and 'bait' not in section['title'].lower() and 'banned' not in section['title'].lower():
                continue
            body = '\n'.join(section['lines'])
            for m in re.finditer(r'^-\s*"([^"]+)"', body, re.MULTILINE):
                phrase = m.group(1).strip().rstrip('.')
                rules.append({
                    'category': 'ai_pattern',
                    'subcategory': section['title'].lower().replace(' ', '_'),
                    'rule_text': phrase.lower(),
                    'weight': 1.0,
                    'explanation': f"From Part {part['part_num']} > {section['title']}",
                })

    return rules


# ---------------------------------------------------------------------------
# Build profile_elements from voice guide style guidance
# ---------------------------------------------------------------------------

# Static baseline elements derived from the voice guide's style philosophy.
# These map the guide's directional guidance to measurable style dimensions.
BASELINE_ELEMENTS = [
    # --- syntactic ---
    {
        'name': 'contraction_rate',
        'category': 'syntactic',
        'element_type': 'directional',
        'direction': 'more',
        'weight': 0.8,
        'target_value': None,
        'tags': ['tone', 'conversational'],
    },
    {
        'name': 'passive_voice_rate',
        'category': 'syntactic',
        'element_type': 'directional',
        'direction': 'less',
        'weight': 0.8,
        'target_value': None,
        'tags': ['clarity', 'active_voice'],
    },
    {
        'name': 'sentence_length_stddev',
        'category': 'syntactic',
        'element_type': 'directional',
        'direction': 'more',
        'weight': 0.7,
        'target_value': None,
        'tags': ['rhythm', 'variety'],
    },
    # --- lexical ---
    {
        'name': 'first_person_usage',
        'category': 'lexical',
        'element_type': 'directional',
        'direction': 'more',
        'weight': 0.6,
        'target_value': None,
        'tags': ['tone', 'personal_voice'],
    },
    {
        'name': 'vocabulary_richness',
        'category': 'lexical',
        'element_type': 'directional',
        'direction': 'more',
        'weight': 0.6,
        'target_value': None,
        'tags': ['variety', 'authenticity'],
    },
    # --- character ---
    {
        'name': 'em_dash_usage',
        'category': 'character',
        'element_type': 'directional',
        'direction': 'more',
        'weight': 0.5,
        'target_value': None,
        'tags': ['punctuation', 'natural'],
    },
    # --- structural ---
    {
        'name': 'flesch_kincaid_grade',
        'category': 'structural',
        'element_type': 'metric',
        'direction': None,
        'weight': 0.7,
        'target_value': 8.0,
        'tags': ['readability', 'accessibility'],
    },
    {
        'name': 'avg_sentence_length',
        'category': 'syntactic',
        'element_type': 'metric',
        'direction': None,
        'weight': 0.6,
        'target_value': 18.0,
        'tags': ['rhythm', 'readability'],
    },
    # --- content ---
    {
        'name': 'hedge_word_rate',
        'category': 'content',
        'element_type': 'directional',
        'direction': 'less',
        'weight': 0.5,
        'target_value': None,
        'tags': ['confidence', 'directness'],
    },
]

# Default prompts inserted alongside the baseline profile
BASELINE_PROMPTS = [
    "Write naturally, as if explaining to a colleague over coffee.",
    "Vary sentence length and structure — mix short punchy sentences with longer flowing ones.",
    "Use contractions, first person, and conversational tone.",
]


# ---------------------------------------------------------------------------
# Database insertion
# ---------------------------------------------------------------------------

def seed_database(conn, parts, voice_guide_text):
    """Insert voice profile, profile_elements, profile_prompts, and detection_rules."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    profile_name = "Baseline"

    # Idempotent: delete existing profile (CASCADE removes elements + prompts)
    cur.execute("SELECT id FROM voice_profiles WHERE name = %s", (profile_name,))
    existing = cur.fetchone()
    if existing:
        print(f"[INFO] Deleting existing profile id={existing['id']} for re-seed...")
        cur.execute("DELETE FROM voice_profiles WHERE id = %s", (existing['id'],))

    # 1. Insert voice profile
    cur.execute("""
        INSERT INTO voice_profiles
            (name, description, profile_type, is_active, sample_content)
        VALUES (%s, %s, 'baseline', true, %s)
        RETURNING id
    """, (
        profile_name,
        "Baseline anti-AI voice guide with style elements covering contractions, "
        "passive voice, sentence variety, first person, vocabulary richness, "
        "em-dash usage, and readability target.",
        voice_guide_text[:5000],  # First 5K chars as sample
    ))
    profile_id = cur.fetchone()['id']
    print(f"[OK] Created voice_profile id={profile_id} (baseline, is_active=true)")

    # 2. Insert profile_elements
    for i, el in enumerate(BASELINE_ELEMENTS):
        cur.execute("""
            INSERT INTO profile_elements
                (voice_profile_id, name, category, element_type,
                 direction, weight, target_value, tags, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'manual')
            ON CONFLICT (voice_profile_id, name) DO UPDATE SET
                category     = EXCLUDED.category,
                element_type = EXCLUDED.element_type,
                direction    = EXCLUDED.direction,
                weight       = EXCLUDED.weight,
                target_value = EXCLUDED.target_value,
                tags         = EXCLUDED.tags,
                updated_at   = NOW()
        """, (
            profile_id,
            el['name'],
            el['category'],
            el['element_type'],
            el['direction'],
            el['weight'],
            el['target_value'],
            json.dumps(el['tags']),
        ))
    print(f"[OK] Inserted {len(BASELINE_ELEMENTS)} profile_elements for profile {profile_id}")

    # 3. Insert profile_prompts
    for i, prompt_text in enumerate(BASELINE_PROMPTS):
        cur.execute("""
            INSERT INTO profile_prompts (voice_profile_id, prompt_text, sort_order)
            VALUES (%s, %s, %s)
        """, (profile_id, prompt_text, i))
    print(f"[OK] Inserted {len(BASELINE_PROMPTS)} profile_prompts for profile {profile_id}")

    # 4. Update settings to point active_baseline_id at this profile
    cur.execute("SELECT id FROM settings LIMIT 1")
    settings_row = cur.fetchone()
    if settings_row:
        cur.execute(
            "UPDATE settings SET active_baseline_id = %s WHERE id = %s",
            (profile_id, settings_row['id'])
        )
        print(f"[OK] Updated settings.active_baseline_id = {profile_id}")
    else:
        print("[WARN] No settings row found — skipping active_baseline_id update")

    # 5. Seed detection_rules (unchanged — feeds Rules Configurator)
    cur.execute("SELECT COUNT(*) as cnt FROM detection_rules")
    existing_count = cur.fetchone()['cnt']
    if existing_count > 0:
        print(f"[SKIP] detection_rules already has {existing_count} rows. Skipping seed.")
    else:
        detection_rules = []
        detection_rules.extend(extract_banned_words(parts))
        detection_rules.extend(extract_constructions(parts))
        detection_rules.extend(extract_ai_patterns(parts))

        for rule in detection_rules:
            cur.execute("""
                INSERT INTO detection_rules (category, subcategory, rule_text, weight, explanation)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                rule['category'],
                rule['subcategory'],
                rule['rule_text'],
                rule['weight'],
                rule['explanation'],
            ))

        print(f"[OK] Inserted {len(detection_rules)} detection_rules")

    conn.commit()
    cur.close()
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python load_voice_guide.py <path-to-VOICE_GUIDE.md>")
        print("  Env vars: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD")
        sys.exit(1)

    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"[ERROR] File not found: {filepath}")
        sys.exit(1)

    print(f"[INFO] Parsing {filepath}...")
    parts = parse_voice_guide(filepath)
    print(f"[INFO] Found {len(parts)} parts:")
    for p in parts:
        print(f"  Part {p['part_num']}: {p['title']} ({len(p['sections'])} sections)")

    with open(filepath, 'r', encoding='utf-8') as f:
        voice_guide_text = f.read()

    print(f"\n[INFO] Connecting to database...")
    conn = get_connection()
    try:
        seed_database(conn, parts, voice_guide_text)
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        conn.close()

    print("\n[DONE] Voice guide import complete.")


if __name__ == '__main__':
    main()

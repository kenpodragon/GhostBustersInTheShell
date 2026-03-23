"""
ETL script: Parse VOICE_GUIDE.md and seed voice_profiles, voice_rules,
and detection_rules tables.

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
                w = re.sub(r'\s*\(.*?\)\s*', '', w).strip().strip('"').strip('"').strip('"')
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
# Build rules_json for voice profile
# ---------------------------------------------------------------------------

def build_rules_json(parts):
    """Build a summary rules_json for the voice_profiles.rules_json column."""
    rules = {
        'banned_words': [],
        'banned_constructions': [],
        'structural_tells': [],
        'ai_patterns': [],
        'voice_markers': [],
    }

    for part in parts:
        for section in part['sections']:
            body = '\n'.join(section['lines'])
            if part['part_num'] == '1':
                for m in re.finditer(r'\*\*([^*]+):\*\*\s*\n?(.*?)(?=\n\*\*|\n###|\n---|\Z)', body, re.DOTALL):
                    words_text = m.group(2).strip()
                    for w in re.split(r',\s*', words_text):
                        w = re.sub(r'\s*\(.*?\)\s*', '', w).strip().strip('"').strip('"').strip('"')
                        if w and len(w) < 80:
                            rules['banned_words'].append(w.lower())
            elif part['part_num'] == '2':
                for m in re.finditer(r'^-\s*"([^"]+)"', body, re.MULTILINE):
                    rules['banned_constructions'].append(m.group(1).strip().lower())
            elif part['part_num'] == '3':
                rules['structural_tells'].append(section['title'])
            elif part['part_num'] in ('5', '6B'):
                for m in re.finditer(r'^-\s*"([^"]+)"', body, re.MULTILINE):
                    rules['ai_patterns'].append(m.group(1).strip().lower())
            elif part['part_num'] == '7':
                rules['voice_markers'].append(section['title'])

    return rules


# ---------------------------------------------------------------------------
# Database insertion
# ---------------------------------------------------------------------------

def seed_database(conn, parts, voice_guide_text):
    """Insert voice profile, voice rules, and detection rules."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Check if already seeded
    cur.execute("SELECT id FROM voice_profiles WHERE name = %s", ("Default - Anti-AI Voice Guide",))
    existing = cur.fetchone()
    if existing:
        print(f"[SKIP] Voice profile already exists (id={existing['id']}). Delete it first to re-seed.")
        print("       DELETE FROM voice_profiles WHERE name = 'Default - Anti-AI Voice Guide';")
        return False

    # 1. Insert voice profile
    rules_json = build_rules_json(parts)
    cur.execute("""
        INSERT INTO voice_profiles (name, description, rules_json, sample_content)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (
        "Default - Anti-AI Voice Guide",
        "Comprehensive anti-AI voice guide with 8 parts covering banned vocabulary, "
        "constructions, structural tells, resume rules, cover letter rules, final checks, "
        "LinkedIn patterns, Stephen-isms, and context-specific patterns.",
        json.dumps(rules_json),
        voice_guide_text[:5000],  # First 5K chars as sample
    ))
    profile_id = cur.fetchone()['id']
    print(f"[OK] Created voice_profile id={profile_id}")

    # 2. Insert voice_rules (one row per section per part)
    rule_count = 0
    sort_order = 0
    for part in parts:
        part_num_int = int(re.sub(r'[^0-9]', '', part['part_num']) or '0')
        for section in part['sections']:
            body = '\n'.join(section['lines']).strip()
            if not body:
                continue

            # Extract bad/good examples
            bad_examples = []
            good_examples = []
            for m in re.finditer(r'(?:Bad|Never|❌|Don\'t):\s*(.+)', body, re.IGNORECASE):
                bad_examples.append(m.group(1).strip().strip('"'))
            for m in re.finditer(r'(?:Good|Instead|✅|Do):\s*(.+)', body, re.IGNORECASE):
                good_examples.append(m.group(1).strip().strip('"'))

            # Determine category
            category = 'general'
            title_lower = section['title'].lower()
            if part['part_num'] == '1':
                category = 'banned_vocabulary'
            elif part['part_num'] == '2':
                category = 'banned_construction'
            elif part['part_num'] == '3':
                category = 'structural_tell'
            elif part['part_num'] == '4':
                category = 'resume_rule'
            elif part['part_num'] == '5':
                category = 'cover_letter_rule'
            elif part['part_num'] == '6':
                category = 'quality_gate'
            elif part['part_num'] == '6B':
                category = 'linkedin_pattern'
            elif part['part_num'] == '7':
                category = 'voice_marker'
            elif part['part_num'] == '8':
                category = 'context_pattern'

            sort_order += 1
            cur.execute("""
                INSERT INTO voice_rules
                    (voice_profile_id, part, part_title, category, subcategory,
                     rule_text, explanation, examples_bad, examples_good, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                profile_id,
                part_num_int,
                part['title'],
                category,
                title_lower[:100],
                body[:2000],  # Main rule content
                f"Part {part['part_num']}: {part['title']}",
                '\n'.join(bad_examples)[:1000] or None,
                '\n'.join(good_examples)[:1000] or None,
                sort_order,
            ))
            rule_count += 1

    print(f"[OK] Inserted {rule_count} voice_rules for profile {profile_id}")

    # 3. Seed detection_rules
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

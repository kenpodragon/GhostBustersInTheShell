# code/tools/run_determinism.py
"""Determinism validation: parse each corpus text 3x, verify identical results,
then cross-compare all pairs via profile_similarity."""
import sys, os, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.dirname(__file__))
from voice_test_harness import parse_file, profile_similarity, save_report

DIVERSE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'local_data', 'corpus', 'diverse')


def main():
    results = {'texts': [], 'cross_comparisons': [], 'determinism': 'PASS'}
    profiles = {}

    print('=== Determinism Validation ===\n')

    # Parse each text 3x, check determinism
    for fname in sorted(os.listdir(DIVERSE_DIR)):
        if not fname.endswith('.txt'):
            continue
        fpath = os.path.join(DIVERSE_DIR, fname)
        parses = []
        for i in range(3):
            p = parse_file(fpath, max_words=10000)
            parses.append(p['profile'])

        # Check determinism
        ok = True
        for key in parses[0]:
            for i in range(1, 3):
                if parses[0][key]['weight'] != parses[i][key]['weight']:
                    results['determinism'] = f'FAIL: {fname}/{key}'
                    ok = False
                tv0 = parses[0][key].get('target_value')
                tvi = parses[i][key].get('target_value')
                if tv0 is not None and tv0 != tvi:
                    results['determinism'] = f'FAIL: {fname}/{key} target_value'
                    ok = False

        profiles[fname] = parses[0]
        results['texts'].append({
            'file': fname,
            'word_count': p['word_count'],
            'elements': len(parses[0]),
            'deterministic': ok,
        })
        status = 'OK' if ok else 'FAIL'
        print(f'  {fname}: {p["word_count"]} words, {len(parses[0])} elements - {status}')

    # Cross-compare every pair
    fnames = list(profiles.keys())
    for i in range(len(fnames)):
        for j in range(i + 1, len(fnames)):
            sim = profile_similarity(profiles[fnames[i]], profiles[fnames[j]])
            results['cross_comparisons'].append({
                'text_a': fnames[i],
                'text_b': fnames[j],
                'similarity': sim['overall_similarity'],
                'label': sim['label'],
            })

    # Print cross-comparison summary
    print(f'\nCross-comparisons ({len(results["cross_comparisons"])} pairs):')
    for c in results['cross_comparisons']:
        print(f'  {c["text_a"]:35s} vs {c["text_b"]:35s}: {c["similarity"]:.3f} ({c["label"]})')

    save_report('determinism_report', results)
    print(f'\nDeterminism: {results["determinism"]}')
    print(f'Texts processed: {len(results["texts"])}')


if __name__ == '__main__':
    main()

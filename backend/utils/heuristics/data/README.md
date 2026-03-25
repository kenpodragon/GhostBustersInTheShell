# Heuristic Data Files

Pre-computed n-gram frequency tables and genre baselines used by AI detection signals.

## Files

| File | Description |
|------|-------------|
| `combined_trigrams.json.gz` | Merged trigram log-probabilities from all corpora |
| `brown_trigrams.json.gz` | Brown corpus trigrams (general American English) |
| `gutenberg_trigrams.json.gz` | Project Gutenberg trigrams (classic literature) |
| `reuters_trigrams.json.gz` | Reuters corpus trigrams (news/business) |
| `webtext_trigrams.json.gz` | Web text corpus trigrams (informal/casual) |
| `genre_baselines.json` | Per-genre MATTR and TTR statistics |

## Trigram File Format

```json
{
  "trigrams": {"word1 word2 word3": -5.123, ...},
  "floor_logprob": -15.7,
  "stats": {"total_trigrams": 1000000, "unique_before_prune": 800000, "unique_after_prune": 200000, "min_count": 2}
}
```

- Values are Laplace-smoothed log-probabilities
- `floor_logprob` is the log-probability assigned to unseen trigrams

## Rebuilding

From the project root:

```bash
cd code/tools
python build_ngram_tables.py
```

Options:
- `--min-count N` — minimum trigram occurrence count to retain (default: 2)
- `--output-dir PATH` — output directory (default: `../backend/utils/heuristics/data`)

Requires: `nltk`, `numpy`

## Adding Custom Corpora

1. Add a loader function in `build_ngram_tables.py` under `get_corpus_words()`
2. Add the corpus name to `corpus_names` in `main()`
3. Map it to a genre in `genre_mapping` if applicable
4. Re-run the build script

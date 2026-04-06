# GhostBusters In The Shell

A local AI text detection and humanization tool. Analyzes text for AI-generated patterns, highlights suspicious sections at sentence level, scores content, and helps rewrite it to sound naturally human.

[Learn more at does-god-exist.org/gbits](https://does-god-exist.org/gbits/)

## What It Does

- **Detect**: Paste text or upload documents (PDF, DOCX, TXT). Get a sentence-level AI probability score with pattern breakdown.
- **Analyze**: Identifies specific AI tells... buzzword density, structural uniformity, hedge word patterns, vocabulary predictability.
- **Rewrite**: Suggests and generates human-sounding replacements for flagged sections. Uses voice profiles to match your writing style.
- **Voice Profiles**: Onboard your own writing samples (2000+ words) to generate a personalized voice profile. The rewriter uses your voice, not generic paraphrasing.
- **Documents**: For longer documents, paginated section-by-section workflow. Analyze, rewrite, iterate, and export.
- **Chrome Extension**: Manifest V3 browser extension for scanning pages, generating content in your voice, and viewing reports.
- **MCP Integration**: 20+ tools via SSE server for agent integration.
- **Neural Sidecars**: Optional embeddings (MiniLM) and RoBERTa for neural AI detection.
- **Evasion Metrics**: Divergence scoring and n-gram overlap to verify rewrites actually changed.

## Architecture

```
Docker Compose (3 services):
  ghostbusters-db   -> PostgreSQL 17 on port 5566
  ghostbusters-app  -> Flask API (8066) + MCP SSE Server (8067)
  ghostbusters-ui   -> React + Vite (5176)
```

## Detection Engine

68+ heuristic patterns across three tiers:

- **Sentence**: Buzzword detection, hedge words, transition patterns, cross-model phrase fingerprinting (Claude/GPT/Gemini dictionaries). Each pattern has a display name and description.
- **Paragraph**: Uniformity scoring (sentence length variance within paragraphs), fragment list detection, staccato rhythm analysis.
- **Document**: Burstiness (sentence length variance across the full text), type-token ratio, semantic embedding monotony, chunked score consistency.

Weighted composite scoring: sentence 45%, paragraph 30%, document 25%. The score math panel in the UI shows exactly which patterns contributed and how much weight each carried. Every flagged sentence links back to the specific heuristic that triggered it.

## Neural Sidecars (Optional)

Two Docker sidecars extend detection beyond heuristics:

- **Embeddings** (default): `all-MiniLM-L6-v2` (384-dim). Powers semantic monotony detection and rewrite divergence scoring.
- **RoBERTa** (opt-in): Pangram EditLens RoBERTa-Large. Neural AI classifier. Requires HuggingFace account for gated model access.

Triple blend when all three are active: heuristic x 0.35 + AI x 0.35 + RoBERTa x 0.30. Degrades gracefully — if a sidecar is unavailable, weights redistribute across remaining sources.

See [docker/SIDECAR_SETUP.md](docker/SIDECAR_SETUP.md) for configuration.

## Quick Start

```bash
# Clone
git clone https://github.com/kenpodragon/GhostBustersInTheShell.git code
cd code

# Start
docker compose up -d

# Verify
curl http://localhost:8066/api/health
```

Open http://localhost:5176 in your browser.

## Evasion Metrics

After rewriting, two metrics verify the output actually diverged from the original:

- **Divergence**: `1 - cosine_similarity` on embeddings. Values below 0.15 trigger a Pass 2 automatic rewrite.
- **N-gram Overlap**: `rapidfuzz` fuzzy matching on 3-6 grams. Catches synonym-only rewrites that preserve sentence structure.

## API

All endpoints at `http://localhost:8066/api/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/analyze | Analyze text or file for AI patterns |
| POST | /api/score | Quick heuristic score (no AI provider needed) |
| POST | /api/rewrite | Rewrite flagged text to sound human |
| POST | /api/rewrite/iterate | Iterate on a specific section |
| GET | /api/documents | List analyzed documents |
| GET | /api/documents/:id | Get document with sections |
| GET | /api/documents/:id/export | Export rewritten document |
| GET | /api/voice-profiles | List voice profiles |
| POST | /api/voice-profiles | Create voice profile |
| POST | /api/voice-profiles/onboard | Auto-generate profile from samples |
| PUT | /api/voice-profiles/:id | Update voice profile |
| GET | /api/voice-style-prompt | Get voice style prompt for active profile |
| GET | /api/analyses | List analysis history |
| GET | /api/analyses/:id | Get analysis with display data |
| GET | /api/health | Health check |

Analysis responses include display data: temperature gauge score, paragraph accordion breakdown, and score math panel showing per-pattern contributions.

## Chrome Extension

Manifest V3. Load unpacked from `chrome-extension/`.

- **Scan**: Paste text or scan current page (selection-first, then smart extraction).
- **Generate**: Write content using a voice profile.
- **Rewrite**: Rewrite flagged text in your voice.
- **Reports**: Save to history, open full report in web UI.

## MCP Server

SSE transport on port 8067. 20+ tools grouped by function:

**Detection**: `analyze_text`, `get_score`, `check_voice`

**Rewriting**: `rewrite_text`, `get_voice_style_prompt`

**Voice Profiles**: `list_voice_profiles`, `set_active_profile`, `score_fidelity`, `get_profile_samples`, `consolidate_voice_observations`, `reparse_voice_profile`

**Corpus**: `parse_voice_text`, `get_corpus_info`, `remove_corpus_document`, `list_documents`, `purge_analysis_documents`

**Settings**: `get_ai_status`, `set_ai_enabled`, `get_rules`, `get_style_guide`, `get_full_guide`

### Connecting from Claude Code

Add to your `.mcp.json`:
```json
{
  "mcpServers": {
    "ghostbusters": {
      "type": "sse",
      "url": "http://localhost:8067/sse"
    }
  }
}
```

### Connecting Other AI Agents

Any MCP-compatible agent can connect via SSE. Set the transport URL to `http://localhost:8067/sse` in your agent's MCP configuration.

## AI Provider Setup

The system works without any AI provider (Python heuristic fallback). For better analysis and rewriting, configure an AI provider:

### Claude (Default)
Set `ANTHROPIC_API_KEY` in `backend/.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### Other Providers
The AI router pattern supports adding custom providers. See `backend/ai_providers/router.py` for the interface.

## Tech Stack

- **Backend**: Python 3.13, Flask, psycopg2
- **Frontend**: React 19, TypeScript, Vite
- **Database**: PostgreSQL 17
- **NLP**: NLTK, textstat, scikit-learn, rapidfuzz
- **AI**: Anthropic SDK (optional)
- **Neural**: MiniLM (sentence-transformers), RoBERTa (optional)
- **MCP**: FastMCP with SSE transport

## Development

```bash
# Backend only (outside Docker)
cd backend
pip install -r requirements.txt
python app.py

# Frontend only
cd frontend
npm install
npm run dev

# Database
# Direct access: psql -h localhost -p 5566 -U ghostbusters -d ghostbusters
```

## License

MIT License. See LICENSE file.

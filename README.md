# GhostBusters In The Shell

A local AI text detection and humanization tool. Analyzes text for AI-generated patterns, highlights suspicious sections at sentence level, scores content, and helps rewrite it to sound naturally human.

## What It Does

- **Detect**: Paste text or upload documents (PDF, DOCX, TXT). Get a sentence-level AI probability score with pattern breakdown.
- **Analyze**: Identifies specific AI tells... buzzword density, structural uniformity, hedge word patterns, vocabulary predictability.
- **Rewrite**: Suggests and generates human-sounding replacements for flagged sections. Uses voice profiles to match your writing style.
- **Voice Profiles**: Onboard your own writing samples (2000+ words) to generate a personalized voice profile. The rewriter uses your voice, not generic paraphrasing.
- **Documents**: For longer documents, paginated section-by-section workflow. Analyze, rewrite, iterate, and export.

## Architecture

```
Docker Compose (3 services):
  ghostbusters-db   -> PostgreSQL 17 on port 5566
  ghostbusters-app  -> Flask API (8066) + MCP SSE Server (8067)
  ghostbusters-ui   -> React + Vite (5176)
```

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
| GET | /api/health | Health check |

## MCP Server

SSE transport at `http://localhost:8067/sse`. Tools exposed:

- `analyze_text` - Full AI detection analysis
- `rewrite_text` - Humanize text with optional voice profile
- `get_score` - Quick heuristic score
- `check_voice` - Check against voice profile rules

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
- **NLP**: NLTK, textstat, scikit-learn
- **AI**: Anthropic SDK (optional)
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

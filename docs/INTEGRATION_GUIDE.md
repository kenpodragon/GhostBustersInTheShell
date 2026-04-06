# GBIS Integration Guide

How to integrate GhostBusters In The Shell (GBIS) into any project for AI text detection, voice-matched rewriting, and fidelity scoring via MCP tools or REST API.

---

## 1. MCP Server Config

Add to your project's `.mcp.json`:

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

Restart Claude Code after adding the config.

---

## 2. CLAUDE.md Snippet

Paste this block into your project's `CLAUDE.md`. Replace all `<CUSTOMIZE>` placeholders.

````markdown
## GBIS — AI Detection & Voice Writing

This project uses [GhostBusters In The Shell](https://github.com/kenpodragon/GhostBustersInTheShell) for AI text detection and voice-matched writing. The GBIS MCP server exposes tools for detection, rewriting, and voice profile management.

### Voice Style Prompt (use when writing content)
Before generating any public-facing prose, fetch the voice style prompt and inject it into your system context:

```
get_voice_style_prompt(baseline_id=<CUSTOMIZE: your profile ID, e.g. 1295>)
```

This returns an 11.4KB prompt containing voice rules, sentence patterns, vocabulary preferences, and stylistic constraints. Use it as a system prompt or prepend it when writing content.

### Anti-AI Analysis (use after generating content)
After generating content, check it for detectable AI patterns:

```
analyze_text(text=<generated content>, use_ai=false)
```

**Target**: `overall_score < 30` (lower = more human-sounding). If the score is above 30, revise the flagged sentences and re-check.

### Voice Fidelity Check
Verify the generated content matches the voice profile:

```
score_fidelity(generated_text=<generated content>, profile_id=<CUSTOMIZE: your profile ID, e.g. 1295>)
```

**Target**: `similarity > 0.5` (higher = closer voice match).

### What to Analyze
<!-- CUSTOMIZE: adjust this list for your project -->
**Analyze** (run detection + fidelity on these):
- Blog posts, articles, marketing copy
- Cover letters, professional bios
- Any public-facing prose

**Skip** (do not run detection on these):
- Code comments, commit messages
- Internal notes, technical documentation
- Configuration files, READMEs
````

---

## 3. Docker Startup

GBIS runs as a Docker Compose stack (4 containers: app, ui, db, and MCP server bundled in app).

```bash
cd /path/to/GhostBustersInTheShell/code
docker compose up -d
```

Verify all containers are healthy:

```bash
docker compose ps
# Expected: ghostbusters-db, ghostbusters-app, ghostbusters-ui — all "Up"
```

**Ports**:
| Service | Port | Purpose |
|---------|------|---------|
| Flask API | 8066 | REST endpoints |
| MCP SSE | 8067 | MCP tool server |
| Frontend | 5176 | Web UI |
| PostgreSQL | 5566 | Database |

If MCP tools return connection errors, ensure the stack is running first.

---

## 4. Voice Prompt REST Endpoint

For tools that don't support MCP (external AI tools, scripts, CI pipelines), use the REST endpoint:

```
GET http://localhost:8066/api/voice-style-prompt?baseline_id=<ID>
```

Returns the voice style prompt as a plain text string (~11.4KB). This is the same prompt returned by the `get_voice_style_prompt` MCP tool.

**Why this endpoint exists**: A full voice profile is ~1.8MB of JSON (corpus data, analysis metadata, samples). The style prompt endpoint extracts just the reusable writing instructions — the only part you need for content generation.

Example with curl:

```bash
curl "http://localhost:8066/api/voice-style-prompt?baseline_id=1295"
```

Example in Python:

```python
import requests
prompt = requests.get("http://localhost:8066/api/voice-style-prompt", params={"baseline_id": 1295}).text
```

---

## 5. Available MCP Tools

### Detection
| Tool | Description |
|------|-------------|
| `analyze_text` | Full AI detection analysis with sentence-level scoring |
| `get_score` | Quick overall AI probability score |
| `check_voice` | Check text against active voice profile rules |

### Rewriting
| Tool | Description |
|------|-------------|
| `rewrite_text` | Rewrite text to reduce AI patterns using voice profile |
| `get_voice_style_prompt` | Get the voice style prompt for injection into any AI tool |

### Voice Profiles
| Tool | Description |
|------|-------------|
| `list_voice_profiles` | List all available voice profiles |
| `set_active_profile` | Set the active profile for detection/rewriting |
| `score_fidelity` | Score how closely text matches a voice profile |
| `get_profile_samples` | Get sample texts from a voice profile's corpus |
| `consolidate_voice_observations` | Merge and deduplicate voice observations |
| `reparse_voice_profile` | Re-analyze corpus to rebuild voice rules |

### Corpus Management
| Tool | Description |
|------|-------------|
| `parse_voice_text` | Add a text sample to a voice profile's corpus |
| `get_corpus_info` | Get corpus statistics for a profile |
| `remove_corpus_document` | Remove a document from the corpus |
| `list_documents` | List all documents in a profile's corpus |
| `purge_analysis_documents` | Remove all analysis-generated documents |

### Settings
| Tool | Description |
|------|-------------|
| `get_ai_status` | Check if AI provider (Claude) is enabled |
| `set_ai_enabled` | Enable/disable AI provider for detection |
| `get_rules` | Get current detection rules |
| `get_style_guide` | Get the style guide for a voice profile |
| `get_full_guide` | Get the complete voice guide (rules + style + examples) |

---

## 6. Example Workflow

End-to-end integration for a new project:

### Setup (one-time)

```bash
# 1. Start GBIS
cd /path/to/GhostBustersInTheShell/code
docker compose up -d

# 2. Verify
docker compose ps
```

Add `.mcp.json` to your project root (see Section 1).

Add the CLAUDE.md snippet to your project (see Section 2), replacing:
- Profile ID placeholder with your actual profile ID (e.g., `1295`)
- "What to analyze" list with your project's content types

### Writing Workflow (every time)

```
Step 1: Fetch voice prompt
  → get_voice_style_prompt(baseline_id=1295)

Step 2: Write content with the voice prompt injected as context

Step 3: Run AI detection
  → analyze_text(text=<content>, use_ai=false)
  → Target: overall_score < 30

Step 4: Run voice fidelity check
  → score_fidelity(generated_text=<content>, profile_id=1295)
  → Target: similarity > 0.5

Step 5: If either check fails:
  → Review flagged sentences from analyze_text
  → Revise patterns that scored high
  → Re-run Steps 3-4 until both pass
```

### Quick Verification

To test that everything is working:

```
1. get_voice_style_prompt(baseline_id=1295)
   → Should return ~11KB prompt text

2. analyze_text(text="The quick brown fox jumps over the lazy dog.", use_ai=false)
   → Should return analysis with overall_score

3. score_fidelity(generated_text="Test sentence.", profile_id=1295)
   → Should return similarity score
```

If any tool returns a connection error, check that the Docker stack is running and port 8067 is accessible.

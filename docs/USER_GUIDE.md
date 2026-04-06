# GhostBusters In The Shell — User Guide

So you want to catch ghost-written text. Good. This guide walks you through everything from installation to running your first scan, building a voice profile, and integrating with your dev tools. No fluff, just the steps.

## Prerequisites

- **Docker Desktop** — [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)
- **Git**
- **Optional: Anthropic API key** — for AI-assisted analysis and rewriting (Claude). Without it, heuristic-only mode works fully.
- **Optional: HuggingFace account** — for the RoBERTa neural sidecar (gated model, needs access approval)

That's it. The entire stack runs in Docker, so you don't need Python, Node, or PostgreSQL installed locally.

## Installation

Clone the repo and get into the code directory:

```bash
git clone https://github.com/kenpodragon/GhostBustersInTheShell.git
cd GhostBustersInTheShell/code
```

If you have an Anthropic API key, create `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

This enables AI-powered analysis and rewriting. Skip this if you only want heuristic detection (which is honestly quite capable on its own).

Fire it up:

```bash
docker compose up -d
```

Verify everything is running:

```bash
docker compose ps
```

You should see four containers: `ghostbusters-db`, `ghostbusters-app`, `ghostbusters-ui`, and `ghostbusters-embeddings`. All should show "healthy" or "running" status.

Open your browser to [http://localhost:5176](http://localhost:5176) and you're in.

One thing to know: the first startup builds Docker images from scratch, which takes a few minutes depending on your connection. Subsequent starts are fast since the images are cached.

## First Scan

Open localhost:5176 and you'll see the main interface. Paste some text into the input area and click **Analyze**.

The temperature gauge at the top gives you the quick read. Clean (0-25) means the text looks human. Ghost Touched (25-50) means there are some AI-typical patterns present. Ghost Written (50-100) means the text is lighting up like a Christmas tree with AI signals.

Here's where it gets interesting. Expand any paragraph to see sentence-level scores and pattern chips. Each chip represents a specific detection signal, things like formulaic transitions, hedge stacking, or suspiciously uniform sentence length. Hover over any chip for a description of what was flagged and why it matters.

Want to understand the math? Click the score breakdown expander. You'll see the weighting tiers: sentence-level signals contribute 45%, paragraph patterns 30%, and document-wide metrics 25%. This layered approach catches patterns that single-pass detectors miss entirely.

I recommend pasting something obviously AI-generated for your first test. Ask ChatGPT to write a cover letter or a product description, drop it in, and watch the system light up. It's the fastest way to calibrate your expectations for what the scores actually mean.

## Building a Voice Profile

Voice profiles are what make rewriting actually work. Without one, you're just paraphrasing. With one, you're translating into a specific person's writing style.

**What to submit:** You need a minimum of 500 words, but I recommend 2000+ words for good coverage. The system extracts 65+ style elements from your samples, including vocabulary richness, sentence structure patterns, punctuation habits, tone markers, and construction tendencies. More text means more reliable extraction.

**What makes good samples:** This is where people trip up. You want natural, unedited writing. Emails you've sent, Slack messages, first drafts, journal entries... that sort of thing. Published blog posts or heavily edited articles are less useful because editors (including your own inner editor) smooth out the quirks that make your voice distinctive. The raw stuff is what the system needs.

Submit your samples through the Voice Profile section of the UI. After processing, check your profile's element breakdown. You'll see exactly what was captured: your average sentence length, your comma frequency, whether you tend toward active or passive voice, your vocabulary tier distribution, all of it.

Use `score_fidelity` to measure how well any generated text matches your profile. It returns a similarity score with per-element breakdowns so you can see exactly where the match is strong and where it drifts.

The more diverse your samples, the better. If you only submit formal writing, the profile won't know how you handle casual tone. Give it range.

## Rewriting with Voice

Got text that scored high on the AI detector? Here's how to make it sound like you wrote it.

Select your baseline voice profile from the dropdown. Paste the flagged text and click **Rewrite**. The system restructures the content to match your voice profile while preserving the meaning.

After rewriting, check the evasion metrics. The divergence score tells you how structurally different the rewrite is from the input (higher is better, means more transformation happened). The n-gram overlap shows how much original phrasing was reused (lower is better for detection evasion).

If divergence is low (below 0.15), a second pass fires automatically with more aggressive structural changes. This handles cases where the first rewrite was too conservative, maybe the input was already close to your style and needed bigger moves to actually shift the detection score.

You can also add optional instructions in the comment field. Things like "make this more casual" or "keep the technical terms but loosen the structure." The rewriter uses these alongside your voice profile to guide the output.

## Content Generation

Switch to **Generate** mode in the UI. Write a prompt describing what you want ("Write a cover letter for a senior developer position at a fintech startup") and select your voice profile from the dropdown.

Click **Generate** and the system produces content that's written in your voice from the start, not AI-generic text that needs rewriting after the fact. The output is automatically scored against the detection engine, so you can see the analysis display right away for any flagged patterns.

This is genuinely useful for drafting content where you need your voice but don't want to stare at a blank page.

## Chrome Extension

Load the extension from the `chrome-extension/` directory. Go to `chrome://extensions`, enable Developer mode, click "Load unpacked," and point it at the directory.

Click the extension icon and open Options to configure the connection. The default points to localhost:8066, which is correct if you're running the Docker stack locally. Hit **Test Connection** to verify.

The extension gives you a few ways to scan. You can paste text directly into the popup, select text on any webpage and click "Scan This Page," or let the smart-extraction pull the main content from whatever page you're viewing. It handles article detection, comment stripping, that kind of thing.

Generation works from the popup too. Pick your voice profile, write a prompt, and get voice-matched content without leaving the page you're on.

**View Full Report** saves the analysis to your history and opens the complete breakdown in the web UI at localhost:5176. Useful when you want the full sentence-level detail that doesn't fit in a popup.

## MCP Integration

Add this to your project's `.mcp.json`:

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

This gives you 20+ tools for detection, rewriting, voice profiles, corpus management, and settings. Everything the web UI can do, MCP can do programmatically.

The voice style prompt endpoint is particularly useful: `GET /api/voice-style-prompt?baseline_id=1295` returns the exact prompt other tools need to write in your voice. It's a compact 11.4KB payload instead of the full 1.8MB profile, optimized for LLM consumption.

Where does this shine? Claude Code projects where you want AI-generated docs or code comments to match your style. Custom AI agents that need to write as you. Any tool that speaks MCP and needs voice-aware text generation.

## Advanced: Neural Sidecars

### Embeddings Sidecar (Default)

The embeddings sidecar starts automatically with `docker compose up -d`. It runs MiniLM-L6-v2 for semantic analysis and powers several detection features: semantic embedding monotony detection (catches text that's suspiciously uniform in meaning-space), rewrite divergence scoring, and cross-model phrase fingerprinting.

You don't need to configure anything. It just works.

### RoBERTa Sidecar (Opt-In)

This adds a neural AI classification signal to the detection pipeline. It requires a HuggingFace account with approved access to `pangram/editlens_roberta-large` (it's a gated model, so you need to request access first).

Start it with the research profile:

```bash
docker compose --profile research up -d
```

Once running, RoBERTa's signal gets blended into the triple-blend scoring alongside heuristics and embeddings. See `docker/SIDECAR_SETUP.md` for full setup instructions and model access details.

## Troubleshooting

**Container won't start:** Run `docker compose logs <service>` to see what's happening. Most common cause is port conflicts. The stack uses ports 5566 (PostgreSQL), 8066 (Flask API), 8067 (MCP SSE), and 5176 (frontend). Make sure nothing else is sitting on those.

**MCP connection refused:** Verify the backend is actually running with `docker compose ps`. If the container is up but MCP won't connect, check that port 8067 isn't blocked by a firewall or VPN.

**Voice profile quality seems low:** Submit more writing samples. Aim for 2000+ words across varied topics and formats. A profile built from one 500-word blog post won't capture your full range.

**High AI scores on your own human text:** This happens more than you'd think, especially with polished, modern writing (temporal bias is real). Check which specific patterns triggered the score. You might find that your natural style happens to overlap with some AI-typical patterns, and that's OK. Consider adjusting pattern weights if specific signals are consistently false-positive for your writing.

**Embeddings sidecar unhealthy:** The model download takes time on the first build. Check logs with `docker compose logs embeddings` and give it a minute. Subsequent starts are instant since the model is cached in the Docker volume.

**RoBERTa sidecar won't build:** Double-check your HuggingFace token and that your account has approved access to the gated model. The build will fail silently if authentication doesn't go through.

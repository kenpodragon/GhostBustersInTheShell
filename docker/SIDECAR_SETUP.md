# Sidecar Setup — Embeddings & RoBERTa

GhostBusters uses two optional neural sidecars that run as separate Docker containers alongside the main application. They communicate over the internal Docker network — no external API calls, everything stays local.

## Overview

| Sidecar | Model | Size | Starts By Default | Purpose |
|---------|-------|------|-------------------|---------|
| Embeddings | all-MiniLM-L6-v2 | ~80MB | Yes | Semantic monotony detection, rewrite divergence scoring |
| RoBERTa | Pangram EditLens RoBERTa-Large | ~1.5GB | No (opt-in) | Neural AI text classification (4-bucket: human → heavy-ai) |

When both sidecars are running, detection uses **triple blend scoring**: heuristic (35%) + AI provider (35%) + RoBERTa (30%). If a sidecar is unavailable, weights redistribute automatically.

---

## Embeddings Sidecar (MiniLM)

No special setup needed — it starts automatically with the main stack.

```bash
docker compose up -d
```

The embeddings model (~80MB) downloads during the first build. After that, it's baked into the image.

**Health check**: The backend waits for the embeddings container to be healthy before starting. If the backend starts but embeddings isn't ready, the system falls back to TF-IDF for similarity calculations.

**Endpoints** (internal Docker network only):
- `GET /health` — returns `{"status": "ok", "model": "all-MiniLM-L6-v2"}`
- `POST /embed` — `{"texts": ["s1", "s2"]}` → `{"embeddings": [[...], [...]]}`
- `POST /similarity` — `{"text_a": "...", "text_b": "..."}` → `{"cosine_similarity": 0.87}`

---

## RoBERTa Sidecar (Pangram EditLens)

This sidecar uses a **gated model** on HuggingFace. You need a free HuggingFace account and must accept the model license before building.

### Step 1: Create a HuggingFace Account

Go to [huggingface.co/join](https://huggingface.co/join) and sign up (or sign in if you have one).

### Step 2: Accept the Model License

1. Go to [pangram/editlens_roberta-large](https://huggingface.co/pangram/editlens_roberta-large)
2. Click **"Agree and access repository"** (or similar button)
3. Wait for approval — some gated repos grant access instantly, others require manual review by the model owner

### Step 3: Create an Access Token

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
2. Click **"New token"**
3. Name it something like `ghostbusters-roberta`
4. Select **"Read"** permission (that's all you need)
5. Click **"Generate"**
6. Copy the token — it starts with `hf_...`

### Step 4: Build the Container

Pass your token as a build argument. The build downloads ~1.5GB of model weights and bakes them into the image:

```bash
docker compose --profile research build --build-arg HF_TOKEN=hf_your_token_here roberta
```

This takes several minutes on first build depending on your connection speed. The model is cached in the Docker image after that.

### Step 5: Start the Sidecar

```bash
docker compose --profile research up -d roberta
```

The RoBERTa sidecar is **opt-in only** — it does NOT start with regular `docker compose up -d`. You must use `--profile research` every time you start it.

**First request**: Takes ~15-20 seconds while the model loads into memory. Subsequent requests are fast.

**Endpoints** (internal Docker network only):
- `GET /health` — returns `{"status": "ok", "model": "editlens_roberta-large"}`
- `POST /classify` — `{"text": "..."}` → `{"ai_probability": 0.92, "label": "ai-generated", "bucket_label": "heavy-ai", "bucket_probs": {...}}`

### Classification Buckets

The EditLens model classifies text into 4 buckets, not binary:

| Bucket | Probability Range | Meaning |
|--------|------------------|---------|
| human | < 0.4 | Likely human-written |
| light-ai | 0.4 - 0.6 | Minor AI editing |
| moderate-ai | 0.6 - 0.7 | Significant AI involvement |
| heavy-ai | > 0.7 | Likely AI-generated |

The model works best on text with 75+ words. Shorter text may produce unreliable results.

### License

The Pangram EditLens RoBERTa-Large model is licensed under **CC BY-NC-SA 4.0** (non-commercial use only). Do not use in commercial deployments.

---

## Verifying Sidecars

After starting, verify from the backend container:

```bash
# Check embeddings
docker exec ghostbusters-app python -c "
from utils.embedding_client import get_embedding_client
c = get_embedding_client()
print('Embeddings available:', c.is_available())
"

# Check RoBERTa (only if running with --profile research)
docker exec ghostbusters-app python -c "
from utils.roberta_client import get_roberta_client
c = get_roberta_client()
print('RoBERTa available:', c.is_available())
"
```

Both should print `True`. If they print `False`, check the container logs.

---

## Claude Integration Volume Mount

The docker-compose mounts your local Claude configuration into the backend container:

```yaml
volumes:
  - ${USERPROFILE:-.}/.claude:/root/.claude
```

This allows the MCP server inside the container to access Claude Code configuration. On Windows, `USERPROFILE` resolves to your user directory (e.g., `C:\Users\YourName`). On Linux/Mac, set `USERPROFILE` or the mount falls back to the current directory.

If you don't use Claude Code integration, this mount is harmless — it just won't find anything.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `401 Unauthorized` during RoBERTa build | Token missing or wrong. Verify `--build-arg HF_TOKEN=hf_...` is correct |
| `GatedRepoError` | You haven't accepted the model license. Visit the [model page](https://huggingface.co/pangram/editlens_roberta-large) and click "Agree" |
| `403 Forbidden` during RoBERTa build | Model access not yet approved. Check your HuggingFace notifications |
| Backend crashes with `ModuleNotFoundError: rapidfuzz` | Rebuild backend: `docker compose build backend` |
| Embeddings health check failing | Model may still be loading. Wait 30s, then check: `docker compose logs embeddings` |
| RoBERTa slow on first request | Normal — model loading takes ~15-20s. Subsequent requests are fast |
| Backend starts before embeddings is ready | The backend gracefully falls back to TF-IDF. Restart once embeddings is healthy: `docker compose restart backend` |
| `../local_data/db_data` mount error | Create the directory: `mkdir -p ../local_data/db_data` |

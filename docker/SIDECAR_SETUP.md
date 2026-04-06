# Sidecar Setup — Embeddings & RoBERTa

## Embeddings Sidecar (MiniLM)

No special setup needed. Build and run:

```bash
docker compose build embeddings
docker compose up -d embeddings
```

Starts automatically with `docker compose up -d`. Uses `all-MiniLM-L6-v2` (~80MB, downloaded at build time).

**Endpoints** (internal Docker network only):
- `GET /health` — returns `{"status": "ok", "model": "all-MiniLM-L6-v2"}`
- `POST /embed` — `{"texts": ["s1", "s2"]}` → `{"embeddings": [[...], [...]]}`
- `POST /similarity` — `{"text_a": "...", "text_b": "..."}` → `{"cosine_similarity": 0.87}`

---

## RoBERTa Sidecar (Pangram EditLens)

This sidecar uses a **gated model** on HuggingFace. You must complete these steps before building.

### Step 1: Create a HuggingFace Account

Go to https://huggingface.co/join and sign up (or sign in if you have one).

### Step 2: Accept the Model License

1. Go to https://huggingface.co/pangram/editlens_roberta-large
2. Click **"Agree and access repository"** (or similar button)
3. Wait for approval — some gated repos are instant, others require manual review

### Step 3: Create an Access Token

1. Go to https://huggingface.co/settings/tokens
2. Click **"New token"**
3. Name it something like `ghostbusters-roberta`
4. Select **"Read"** permission (that's all you need)
5. Click **"Generate"**
6. **Copy the token** — it starts with `hf_...`

### Step 4: Build the Container

```bash
docker compose --profile research build --build-arg HF_TOKEN=hf_your_token_here roberta
```

Replace `hf_your_token_here` with your actual token. The build downloads ~1.5GB (model weights).

### Step 5: Run

```bash
docker compose --profile research up -d roberta
```

The RoBERTa sidecar is **opt-in only** — it does NOT start with regular `docker compose up -d`. You must explicitly use `--profile research`.

**Endpoints** (internal Docker network only):
- `GET /health` — returns `{"status": "ok", "model": "editlens_roberta-large"}`
- `POST /classify` — `{"text": "..."}` → `{"ai_probability": 0.92, "label": "ai-generated", "chunks": [...]}`

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

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 401 Unauthorized during RoBERTa build | Token missing or wrong. Check `--build-arg HF_TOKEN=...` |
| GatedRepoError | You haven't accepted the license at the HuggingFace model page |
| Backend crashes with `ModuleNotFoundError: rapidfuzz` | Rebuild backend: `docker compose build backend` |
| Embeddings health check failing | Model may still be loading. Wait 30s, check `docker compose logs embeddings` |
| RoBERTa slow to start | Normal — model loading takes ~15-20s on first request |

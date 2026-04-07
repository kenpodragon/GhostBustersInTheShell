import re

from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = Flask(__name__)
tokenizer = AutoTokenizer.from_pretrained('pangram/editlens_roberta-large')
model = AutoModelForSequenceClassification.from_pretrained('pangram/editlens_roberta-large')
model.eval()

MAX_TOKENS = 512
CHUNK_WORDS = 300

# EditLens 4-bucket model (pangram/editlens_roberta-large):
# Trained on cosine_score (editing degree) with lo=0.03, hi=0.15.
#   LABEL_0: cosine_score <= 0.03 — human-written (minimal AI editing)
#   LABEL_1: 0.03 < score < 0.09 — lightly AI-edited
#   LABEL_2: 0.09 <= score < 0.15 — significantly AI-edited
#   LABEL_3: cosine_score >= 0.15 — heavily AI-generated/rewritten
# Weights convert bucket probabilities to a single 0-1 AI probability.
BUCKET_AI_WEIGHTS = [0.0, 0.33, 0.67, 1.0]
BUCKET_LABELS = ["human", "light-ai", "significant-ai", "heavy-ai"]

BOILERPLATE_STARTS = ["Sure", "Here", "Abstract", "Title", "I'm happy to help", "Certainly"]


def _preprocess(text: str) -> str:
    """Match EditLens training preprocessing: lowercase, strip boilerplate, normalize whitespace."""
    paragraphs = [p for p in text.split("\n") if p.strip()]
    if paragraphs:
        first = re.sub(r"^[^a-zA-Z0-9]*", "", paragraphs[0])
        if any(first.startswith(phrase) for phrase in BOILERPLATE_STARTS):
            if len(paragraphs) > 1:
                text = "\n".join(paragraphs[1:])
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _chunk_text(text: str) -> list[str]:
    """Split text into ~300-word chunks at sentence boundaries."""
    words = text.split()
    if len(words) <= CHUNK_WORDS:
        return [text]
    chunks = []
    current = []
    for word in words:
        current.append(word)
        if len(current) >= CHUNK_WORDS and word.endswith(('.', '!', '?')):
            chunks.append(' '.join(current))
            current = []
    if current:
        chunks.append(' '.join(current))
    return chunks


def _classify_chunk(text: str) -> dict:
    """Classify a single chunk, returning AI probability and per-bucket detail."""
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=MAX_TOKENS)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=-1)[0]
    bucket_probs = [float(probs[i]) for i in range(len(probs))]
    ai_prob = sum(p * w for p, w in zip(bucket_probs, BUCKET_AI_WEIGHTS))
    top_bucket = int(torch.argmax(probs))
    return {
        "ai_probability": ai_prob,
        "bucket_label": BUCKET_LABELS[top_bucket],
        "bucket_probs": {BUCKET_LABELS[i]: round(bucket_probs[i], 4) for i in range(len(bucket_probs))},
    }


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "model": "editlens_roberta-large"})


@app.route('/classify', methods=['POST'])
def classify():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "text required"}), 400

    preprocessed = _preprocess(text)
    chunks = _chunk_text(preprocessed)
    chunk_results = []
    for chunk in chunks:
        result = _classify_chunk(chunk)
        result["text"] = chunk[:100] + "..." if len(chunk) > 100 else chunk
        chunk_results.append(result)

    mean_prob = sum(c["ai_probability"] for c in chunk_results) / len(chunk_results)
    if mean_prob >= 0.7:
        label = "ai-generated"
    elif mean_prob >= 0.4:
        label = "ai-edited"
    else:
        label = "human-written"

    return jsonify({
        "ai_probability": round(mean_prob, 4),
        "label": label,
        "chunks": chunk_results
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

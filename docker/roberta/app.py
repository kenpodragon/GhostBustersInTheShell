from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = Flask(__name__)
tokenizer = AutoTokenizer.from_pretrained('pangram/editlens_roberta-large')
model = AutoModelForSequenceClassification.from_pretrained('pangram/editlens_roberta-large')
model.eval()

MAX_TOKENS = 512
CHUNK_WORDS = 300


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


def _classify_chunk(text: str) -> float:
    """Return AI probability for a single chunk."""
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=MAX_TOKENS)
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.softmax(outputs.logits, dim=-1)
    # Assume label 1 = AI-generated (verify against model card)
    ai_prob = float(probs[0][1]) if probs.shape[1] > 1 else float(probs[0][0])
    return ai_prob


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "model": "editlens_roberta-large"})


@app.route('/classify', methods=['POST'])
def classify():
    data = request.get_json()
    text = data.get('text', '')
    if not text:
        return jsonify({"error": "text required"}), 400

    chunks = _chunk_text(text)
    chunk_results = []
    for chunk in chunks:
        prob = _classify_chunk(chunk)
        chunk_results.append({"text": chunk[:100] + "..." if len(chunk) > 100 else chunk, "ai_probability": prob})

    mean_prob = sum(c["ai_probability"] for c in chunk_results) / len(chunk_results)
    label = "ai-generated" if mean_prob >= 0.5 else "human-written"

    return jsonify({
        "ai_probability": round(mean_prob, 4),
        "label": label,
        "chunks": chunk_results
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

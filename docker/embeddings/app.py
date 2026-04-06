from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import numpy as np

app = Flask(__name__)
model = SentenceTransformer('all-MiniLM-L6-v2')


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "model": "all-MiniLM-L6-v2"})


@app.route('/embed', methods=['POST'])
def embed():
    data = request.get_json()
    texts = data.get('texts', [])
    if not texts:
        return jsonify({"error": "texts array required"}), 400
    embeddings = model.encode(texts, normalize_embeddings=True)
    return jsonify({"embeddings": embeddings.tolist()})


@app.route('/similarity', methods=['POST'])
def similarity():
    data = request.get_json()
    text_a = data.get('text_a', '')
    text_b = data.get('text_b', '')
    if not text_a or not text_b:
        return jsonify({"error": "text_a and text_b required"}), 400
    embeddings = model.encode([text_a, text_b], normalize_embeddings=True)
    cosine_sim = float(np.dot(embeddings[0], embeddings[1]))
    return jsonify({"cosine_similarity": cosine_sim})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

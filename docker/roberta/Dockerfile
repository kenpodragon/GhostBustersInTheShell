FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Download gated model at build time (requires HuggingFace token)
ARG HF_TOKEN
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; AutoTokenizer.from_pretrained('pangram/editlens_roberta-large', token='${HF_TOKEN}'); AutoModelForSequenceClassification.from_pretrained('pangram/editlens_roberta-large', token='${HF_TOKEN}')"

COPY app.py .

EXPOSE 5000

# License: CC BY-NC-SA 4.0 (non-commercial only)
LABEL license="CC BY-NC-SA 4.0" \
      model="pangram/editlens_roberta-large" \
      usage="non-commercial research only"

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "2", "--timeout", "60", "app:app"]

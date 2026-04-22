FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for Claude CLI)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude CLI (optional — used for AI-enhanced analysis)
RUN npm install -g @anthropic-ai/claude-code || echo "Claude CLI install skipped"

COPY requirements.txt .
RUN pip install --no-cache-dir setuptools && pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm
RUN python -c "import nltk; nltk.download('vader_lexicon', download_dir='/usr/local/nltk_data')"

COPY . .

# Isolated cwd + empty plugin-dir for Claude CLI calls: stops CLAUDE.md,
# user settings, and marketplace plugins from auto-loading on each call.
RUN mkdir -p /tmp/cli_cwd /tmp/empty_plugins

EXPOSE 8066 8067

CMD ["python", "app.py"]

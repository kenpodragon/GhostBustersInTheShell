"""Claude CLI adapter using `claude -p` for non-interactive prompts."""
import subprocess
import json
import re

from .base import AIProvider


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from Claude output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = re.sub(r'^```\w*\n?', '', text)
        # Remove closing fence
        text = re.sub(r'\n?```$', '', text)
    return text.strip()


ANALYZE_PROMPT = """You are an AI text detection expert. Analyze this text for AI-generated content patterns.
For each sentence, provide an AI probability score (0-100).
Also identify specific patterns that suggest AI generation (buzzwords, hedge words, passive voice, uniform sentence length, etc.).

Return ONLY valid JSON matching this exact schema:
{{
  "overall_score": 0-100,
  "sentences": [
    {{"text": "the sentence", "score": 0-100, "patterns": [{{"pattern": "name", "detail": "description"}}]}}
  ],
  "detected_patterns": [
    {{"pattern": "name", "detail": "description"}}
  ]
}}

Text to analyze:
---
{text}
---

Return ONLY the JSON object, no explanation."""

REWRITE_PROMPT = """You are a text humanizer. Rewrite this text to sound naturally human-written, not AI-generated.
Preserve the meaning but change: sentence structure, vocabulary, rhythm, and flow.
Make it sound like a real person wrote it — varied sentence lengths, natural contractions, specific details over vague generalities.
{voice_context}

Return ONLY valid JSON matching this exact schema:
{{
  "rewritten_text": "the full rewritten text",
  "changes": [
    {{"original": "original phrase", "rewritten": "new phrase", "reason": "why changed"}}
  ]
}}

Text to rewrite:
---
{text}
---

Return ONLY the JSON object, no explanation."""


class ClaudeProvider(AIProvider):
    """Adapter for the Claude CLI (claude -p)."""
    name = "claude"
    cli_command = "claude"

    def _run_cli(self, prompt: str) -> dict:
        """Run claude -p <prompt> --output-format json and parse the result."""
        try:
            cmd = [self.cli_command, "-p", prompt, "--output-format", "json"]
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI error: {result.stderr.strip()}")
            output = result.stdout.strip()
            # Claude --output-format json wraps in {"type":"result","result":"..."}
            try:
                parsed = json.loads(output)
                if isinstance(parsed, dict) and "result" in parsed:
                    inner = parsed["result"]
                    if isinstance(inner, str):
                        inner = _strip_code_fences(inner)
                        return json.loads(inner)
                    return inner
                return parsed
            except json.JSONDecodeError:
                # Try extracting JSON block from plain text
                match = re.search(r'\{.*\}', output, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise RuntimeError(f"Claude returned invalid JSON: {output[:200]}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude CLI timed out after 120s")

    def analyze(self, text: str) -> dict:
        """Use Claude to analyze text for AI patterns."""
        prompt = ANALYZE_PROMPT.format(text=text)
        result = self._run_cli(prompt)
        for key in ("overall_score", "sentences", "detected_patterns"):
            if key not in result:
                raise RuntimeError(f"Claude analyze missing key: {key}")
        return result

    def rewrite(self, text: str, voice_profile_id: int = None) -> dict:
        """Use Claude to rewrite text to sound more human."""
        voice_context = ""
        if voice_profile_id:
            from db import query_one
            profile = query_one(
                "SELECT name, rules_json FROM voice_profiles WHERE id = %s",
                (voice_profile_id,)
            )
            if profile:
                voice_context = f"\nVoice profile '{profile['name']}' rules:\n{profile['rules_json']}"

        prompt = REWRITE_PROMPT.format(text=text, voice_context=voice_context)
        result = self._run_cli(prompt)
        if "rewritten_text" not in result:
            raise RuntimeError("Claude rewrite missing key: rewritten_text")
        return result

    def health_check(self) -> dict:
        """Check if Claude CLI is available and return version info."""
        if not self.is_available():
            return {"available": False, "version": None, "model": None}
        try:
            result = subprocess.run(
                [self.cli_command, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            version = result.stdout.strip() or result.stderr.strip()
            return {"available": True, "version": version, "model": "claude-cli"}
        except Exception as e:
            return {"available": False, "version": None, "model": None, "error": str(e)}

"""Claude CLI adapter using `claude -p` for non-interactive prompts."""
import subprocess
import json
import re

from .base import AIProvider
from utils.rules_config import rules_config


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from Claude output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        text = re.sub(r'^```\w*\n?', '', text)
        # Remove closing fence
        text = re.sub(r'\n?```$', '', text)
    return text.strip()


ANALYZE_PROMPT = """Determine if this text is AI-generated or human-written. Score 0-100 (0=human, 100=AI).

Be calibrated: most AI text scores 60-90. Most human text scores 0-25. Don't cluster around 50.
Judge the STYLE, not the TOPIC. A paper about AI written by a human is still human.
Look for: buzzword density, sentence uniformity, missing first-person/contractions/questions, em dash overuse, triadic lists, trailing -ing phrases, self-contained paragraphs, no digressions.
Human tells: contractions, first-person, specific names/dates, irregular punctuation, tangents, emotional shifts.

Return ONLY valid JSON:
{{"overall_score": 0-100, "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "reasoning": "one sentence"}}

Text:
---
{text}
---"""

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
        """Use Claude to analyze text for AI patterns (A_v3 calibrated prompt)."""
        _prompt_template = rules_config.ai_prompt or ANALYZE_PROMPT
        prompt = _prompt_template.format(text=text)
        result = self._run_cli(prompt)
        if "overall_score" not in result:
            raise RuntimeError("Claude analyze missing key: overall_score")
        # Normalize: ensure detected_patterns exists
        if "detected_patterns" not in result:
            result["detected_patterns"] = []
        # Ensure score is numeric and clamped
        score = result["overall_score"]
        if isinstance(score, (int, float)):
            result["overall_score"] = max(0, min(100, float(score)))
        else:
            raise RuntimeError(f"Claude returned non-numeric score: {score}")
        return result

    def rewrite(self, text: str, voice_profile_id: int = None, style_brief: str = None) -> dict:
        """Use Claude to rewrite text to sound more human.

        If style_brief is provided, uses it as the prompt (from style brief generator).
        Otherwise falls back to static REWRITE_PROMPT.
        """
        if style_brief:
            prompt = style_brief.replace("{text}", text)
        else:
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

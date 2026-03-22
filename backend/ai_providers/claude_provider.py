"""Claude AI Provider for analysis and rewriting."""
import os
from anthropic import Anthropic


class ClaudeProvider:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"

    def analyze(self, text: str) -> dict:
        """Use Claude to analyze text for AI patterns."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": f"""Analyze this text for AI-generated content patterns.
For each sentence, provide an AI probability score (0-100).
Also identify specific patterns that suggest AI generation.

Return JSON with:
- overall_score: 0-100 (higher = more likely AI)
- sentences: [{{text, score, patterns: []}}]
- detected_patterns: [{{pattern_name, description, examples}}]

Text to analyze:
{text}"""
            }],
        )
        import json
        try:
            return json.loads(response.content[0].text)
        except (json.JSONDecodeError, IndexError):
            return {"error": "Failed to parse AI response", "raw": response.content[0].text}

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
                voice_context = f"\n\nVoice profile '{profile['name']}' rules:\n{profile['rules_json']}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{
                "role": "user",
                "content": f"""Rewrite this text to sound naturally human-written, not AI-generated.
Preserve the meaning but change: sentence structure, vocabulary, rhythm, and flow.
Make it sound like a real person wrote it.{voice_context}

Return JSON with:
- rewritten_text: the full rewritten text
- changes: [{{original, rewritten, reason}}]

Text to rewrite:
{text}"""
            }],
        )
        import json
        try:
            return json.loads(response.content[0].text)
        except (json.JSONDecodeError, IndexError):
            return {"error": "Failed to parse AI response", "raw": response.content[0].text}

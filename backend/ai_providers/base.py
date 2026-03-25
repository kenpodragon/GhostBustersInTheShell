"""Abstract base class for AI provider adapters."""
import shutil
import subprocess
import json
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for AI CLI adapters. Each wraps a locally-installed CLI tool."""
    name: str = ""
    cli_command: str = ""

    def is_available(self) -> bool:
        """Check if the CLI is installed and on PATH."""
        return shutil.which(self.cli_command) is not None

    @abstractmethod
    def analyze(self, text: str) -> dict:
        """Analyze text for AI-generated patterns.
        Returns: {"overall_score": float, "detected_patterns": [], "reasoning": str}
        """

    @abstractmethod
    def rewrite(self, text: str, voice_profile_id: int = None, style_brief: str = None) -> dict:
        """Rewrite text to sound human.

        If style_brief is provided, use it as the rewrite prompt (from style brief
        generator). voice_profile_id is ignored when style_brief is set.

        Returns: {"rewritten_text": str, "changes": []}
        """

    @abstractmethod
    def health_check(self) -> dict:
        """Returns: {"available": bool, "version": str, "model": str}"""

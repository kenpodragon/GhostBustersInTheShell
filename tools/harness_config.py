"""Configuration for voice format experiment harness."""
from pathlib import Path

PROFILE_ID = 1295  # Stephen Salaka, 65 elements
API_BASE = "http://localhost:8066"
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "voice_profiles" / "format_routing_results"
TEST_INPUTS_DIR = Path(__file__).resolve().parent / "test_inputs"
CLAUDE_TIMEOUT = 120  # seconds per Claude call

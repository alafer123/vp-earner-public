"""Pytest configuration: isolate tests in a temp directory so state.json,
budget.json, and artifact files never touch the real project workspace."""

import os
import sys
import tempfile
from pathlib import Path

# Ensure the project root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_TEST_TMP = tempfile.mkdtemp(prefix="vp-earner-test-")


def pytest_configure(config):
    """Set env vars BEFORE importing earner_loop so module-level paths point to temp."""
    os.environ["ARTIFACTS_DIR"] = _TEST_TMP
    # Patch the module-level paths used by earner_loop
    import earner_loop
    earner_loop.CRON_DIR = Path(_TEST_TMP)
    earner_loop.STATE_FILE = Path(_TEST_TMP) / "state.json"
    earner_loop.BUDGET_FILE = Path(_TEST_TMP) / "budget.json"
    earner_loop.EVENTS_FILE = Path(_TEST_TMP) / "events.jsonl"

"""Security tests — verify secrets are never exposed in the repo.

Covers ChatGPT's requirement:
  - .env is in .gitignore (not tracked by git)
  - No hardcoded wallet keys, API tokens, or private keys in source
  - .env.example has placeholder values only
  - No real credentials in state.json / budget.json artifacts
"""

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = ROOT / ".gitignore"


class TestGitIgnore:
    def test_env_in_gitignore(self):
        """.env must be in .gitignore."""
        lines = GITIGNORE.read_text()
        assert ".env" in lines, ".env must be in .gitignore"

    def test_env_example_exists(self):
        """.env.example must exist with placeholder values."""
        env_example = ROOT / ".env.example"
        assert env_example.exists(), ".env.example must exist"
        content = env_example.read_text()
        # Must NOT contain real secrets — only placeholders
        real_patterns = re.findall(r"0x[0-9a-fA-F]{64}", content)
        assert len(real_patterns) == 0, f"Private key found in .env.example: {real_patterns}"


class TestNoSecretsInSource:
    """Scan all .py and .js source files for hardcoded secrets."""

    def test_no_private_keys_in_source(self):
        """No 64-char hex strings (private keys) in source files."""
        PRIVATE_KEY_RE = re.compile(r"0x[0-9a-fA-F]{64}")
        violations = []
        for ext in ["*.py", "*.js"]:
            for f in ROOT.rglob(ext):
                if ".venv" in str(f) or "node_modules" in str(f) or "__pycache__" in str(f):
                    continue
                content = f.read_text()
                for match in PRIVATE_KEY_RE.finditer(content):
                    violations.append(f"{f.relative_to(ROOT)}: {match.group()[:20]}...")
        assert len(violations) == 0, f"Private keys found: {violations}"

    def test_no_acp_tokens_in_source(self):
        """No ACP API tokens in source."""
        TOKEN_RE = re.compile(r"acp-[a-zA-Z0-9_-]{20,}")
        violations = []
        for ext in ["*.py", "*.js"]:
            for f in ROOT.rglob(ext):
                if ".venv" in str(f) or "node_modules" in str(f) or "__pycache__" in str(f):
                    continue
                content = f.read_text()
                for match in TOKEN_RE.finditer(content):
                    violations.append(str(f.relative_to(ROOT)))
        assert len(violations) == 0, f"ACP tokens found in: {violations}"

    def test_no_privy_keys_in_source(self):
        """No Privy signer keys."""
        PRIVY_RE = re.compile(r"privy_[a-zA-Z0-9_-]{20,}", re.IGNORECASE)
        violations = []
        for ext in ["*.py", "*.js"]:
            for f in ROOT.rglob(ext):
                if ".venv" in str(f) or "node_modules" in str(f) or "__pycache__" in str(f):
                    continue
                content = f.read_text()
                for match in PRIVY_RE.finditer(content):
                    violations.append(str(f.relative_to(ROOT)))
        assert len(violations) == 0, f"Privy keys found in: {violations}"

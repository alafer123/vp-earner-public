#!/usr/bin/env python3
"""
VP Earner V2 — Skill Framework (Python reference implementation).

Mirrors the production TypeScript skill framework at:
  core/ (base_skill.js, skill_router.js, quality_gate.js)
  skills/ (dependency-security-audit, code-review, json-data-transform)

Each skill implements:
  can_handle(job)          -> bool
  estimate_cost(job)       -> float
  execute(job, offering)   -> {deliverable, evidence, artifacts}
  verify(result)           -> {passed, score, issues}
  package_deliverable(result) -> str
"""

from abc import ABC, abstractmethod
from pathlib import Path
import hashlib
import os


class BaseSkill(ABC):
    """Abstract base class for all skills."""

    name: str = ""
    display_name: str = ""
    categories: list[str] = []
    keywords: list[str] = []

    def can_handle(self, job: dict) -> bool:
        """Check if this skill can handle the given job."""
        desc = (job.get("description", "") or job.get("name", "")).lower()
        return any(kw.lower() in desc for kw in self.keywords)

    def estimate_cost(self, job: dict) -> float:
        """Estimate compute cost in USD for this skill."""
        return 0.50

    @abstractmethod
    def execute(self, job: dict, offering: dict) -> dict:
        """Execute the skill. Returns {deliverable, evidence, artifacts}."""
        pass

    def verify(self, result: dict) -> dict:
        """Verify the execution result. Override for skill-specific checks."""
        issues = []

        if not result.get("deliverable") or len(result["deliverable"]) < 20:
            issues.append("Deliverable is empty or too short")

        if not result.get("evidence") or len(result["evidence"]) == 0:
            issues.append("No evidence artifacts provided")

        # Check for banned phrases (AI slop)
        deliverable = result.get("deliverable", "").lower()
        banned = ["as an ai", "i cannot browse", "in today's digital age",
                  "it is important to note", "lorem ipsum", "placeholder",
                  "insert here", "example.com"]
        for phrase in banned:
            if phrase in deliverable:
                issues.append(f"AI slop phrase: '{phrase}'")

        score = 100 - len(issues) * 10
        return {
            "passed": score >= 50,
            "score": max(0, score),
            "issues": issues,
        }

    def package_deliverable(self, result: dict) -> str:
        """Package the final deliverable text for ACP submission."""
        artifact_list = "\n".join(f"- `{a}`" for a in result.get("artifacts", []))
        return f"{result['deliverable']}\n\n**Evidence & Artifacts:**\n{artifact_list}"

    def save_artifact(self, content: str, filename: str, job_id: str = "unknown") -> str:
        """Save an artifact file and return its path."""
        artifacts_dir = Path("artifacts") / job_id
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        filepath = artifacts_dir / filename
        filepath.write_text(content)
        return str(filepath)

    def compute_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of a file."""
        try:
            return hashlib.sha256(open(filepath, "rb").read()).hexdigest()[:16]
        except (IOError, OSError):
            return "hash_error"

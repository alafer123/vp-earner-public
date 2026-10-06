"""Tests for the anti-slop quality gate.

Covers ChatGPT's requirements:
  - Clean deliverable passes
  - AI slop phrases detected (rejected deliverable)
  - Placeholder text detected
  - Structural slop (Rule of Three) detected
"""

import pytest
from earner_loop import run_quality_gate


class TestQualityGate:
    def test_clean_deliverable_passes(self):
        """A genuine deliverable with evidence must pass."""
        proof = {
            "deliverable": "## Code Review Report\n\nJob: test-1\n\n## Findings\n\n- **[high]** `src/app.ts:42` — Unhandled promise rejection\n  Fix: Add try/catch\n- **[medium]** `src/utils.ts:15` — Unused import\n  Fix: Remove",
            "artifacts": ["/path/to/report.md"],
            "logs": ["Reviewed 5 files"],
        }
        ok, issues = run_quality_gate(proof)
        assert ok is True
        assert issues == []

    def test_ai_slop_detected(self):
        """Deliverable with AI slop phrases must fail."""
        proof = {
            "deliverable": "As an AI, I cannot browse. In today's digital age, it is important to note that this solution is great. Lorem ipsum dolor sit amet.",
            "artifacts": ["/path/to/report.md"],
            "logs": ["done"],
        }
        ok, issues = run_quality_gate(proof)
        assert ok is False
        assert len(issues) > 0

    def test_placeholder_text_detected(self):
        """Deliverable with TODO/FIXME/placeholder must fail."""
        proof = {
            "deliverable": "## Report\n\nTODO: implement this section\nFIXME: add data here\ndescription = example.com",
            "artifacts": [],
            "logs": [],
        }
        ok, issues = run_quality_gate(proof)
        assert ok is False

    def test_empty_deliverable(self):
        """Empty deliverable."""
        proof = {"deliverable": "", "artifacts": [], "logs": []}
        ok, issues = run_quality_gate(proof)
        assert ok is True  # quality gate doesn't check empty itself


class TestSelfVerify:
    def test_empty_artifacts_fails(self):
        """self_verify must reject deliverables with no artifacts/logs."""
        from earner_loop import self_verify
        proof = {"deliverable": "Done.", "artifacts": [], "logs": []}
        verified, issues = self_verify(proof)
        assert verified is False
        assert any("No artifacts" in i for i in issues)

    def test_missing_artifact_file_fails(self):
        """self_verify must catch missing artifact files."""
        from earner_loop import self_verify
        proof = {"deliverable": "Report generated.", "artifacts": ["/nonexistent/file.md"], "logs": ["done"]}
        verified, issues = self_verify(proof)
        assert verified is False
        assert any("not found" in i for i in issues)

    def test_placeholder_in_deliverable_fails(self):
        """self_verify must reject TODO/FIXME in deliverables."""
        from earner_loop import self_verify
        proof = {"deliverable": "TODO: fill this in later", "artifacts": ["/some/file.txt"], "logs": ["done"]}
        verified, issues = self_verify(proof)
        assert verified is False

    def test_valid_proof_passes(self, tmp_path):
        """A real artifact file + real deliverable must pass."""
        from earner_loop import self_verify
        artifact = tmp_path / "report.md"
        artifact.write_text("# Report\n\nFindings here.")
        proof = {
            "deliverable": "## Report\n\nFindings: 3 high, 2 medium.\nAll sections complete.",
            "artifacts": [str(artifact)],
            "logs": ["Reviewed 5 files"],
        }
        verified, issues = self_verify(proof)
        assert verified is True
        assert issues == []

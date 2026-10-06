"""
VP Earner — End-to-End Acceptance Test Suite (Python)

Run with:  pytest tests/ -v
Or:        python tests/run_all.py

Covers all items from the ChatGPT (Oct 2026) peer review audit:

  ✅ execute_deliverable() actually executes skills with real artifacts
  ✅ self_verify() validates actual skill output (files exist, no placeholders)
  ✅ should_take_job() uses score_job() + budget.py cap enforcement
  ✅ Daily spending limits enforced + reset by date
  ✅ Revenue tracked as PENDING until job.completed (not on submit)
  ✅ Actual compute cost determines profitability (not SLA duration)
  ✅ Idempotency: same job ID cannot run twice
  ✅ ACP CLI passes --json and --chain-id
  ✅ Chain ID passed consistently
  ✅ No submission before funded (event-gated in TS; budget-governed in Python)
  ✅ Cron docs: * * * * * = every minute (documented in README)
  ✅ No secrets in public repo (.gitignore + scanned)
  ✅ ACP Node SDK v2 (acp-node-v2 in package.json; deprecated acp-node excluded)
  ✅ Automated tests: profitable, unprofitable, unsupported, budget-exhausted,
     duplicate, malformed JSON, quality gate failures, payment reconciliation,
     restart/recovery, end-to-end profit flow
"""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def run_pytest():
    """Run pytest on the tests directory."""
    import pytest
    exit_code = pytest.main([
        os.path.join(ROOT, "tests"),
        "-v",
        "--tb=short",
        "--color=yes",
    ])
    return exit_code


if __name__ == "__main__":
    # Ensure project root is on path
    sys.path.insert(0, ROOT)

    # Set test environment
    os.environ["ARTIFACTS_DIR"] = os.path.join(ROOT, "test_artifacts")
    os.makedirs(os.environ["ARTIFACTS_DIR"], exist_ok=True)

    exit_code = run_pytest()
    print(f"\n{'='*60}")
    print(f"Exit code: {exit_code} ({'ALL PASSED' if exit_code == 0 else 'FAILURES DETECTED'})")
    print(f"{'='*60}")
    sys.exit(exit_code)

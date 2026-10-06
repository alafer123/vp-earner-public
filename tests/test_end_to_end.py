"""End-to-end test: proves the full VP Earner profit/revenue flow.

Simulates the exact scenario ChatGPT described:
  1. Buyer creates $5 code-review job
  2. VP Earner receives & scores it (10x margin)
  3. Job accepted, budget set
  4. Skill executes, produces real artifacts
  5. Quality gate + self-verify pass
  6. Deliverable submitted → revenue PENDING
  7. Buyer completes → $5 revenue, $0.50 expense, $4.50 profit
  8. SAME job re-sent → rejected (idempotency)
"""

import json
import pytest
from datetime import date
from earner_loop import (
    score_job, should_take_job, execute_deliverable, self_verify,
    run_quality_gate, load_state, save_state, load_budget, save_budget,
    estimate_compute_cost, WEEKLY_CAP, DAILY_CAP, SCORE_THRESHOLD,
)


@pytest.fixture
def e2e_env(tmp_path, monkeypatch):
    """Isolated environment with fresh state + budget files."""
    import earner_loop
    monkeypatch.setattr(earner_loop, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(earner_loop, "BUDGET_FILE", tmp_path / "budget.json")
    monkeypatch.setattr(earner_loop, "EVENTS_FILE", tmp_path / "events.jsonl")
    monkeypatch.setattr(earner_loop, "CRON_DIR", tmp_path)
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    yield earner_loop


class TestEndToEndProfitFlow:
    def test_full_e2e_cycle(self, e2e_env):
        """The complete profitable-job → submission → payment flow."""

        # --- SETUP: Fresh state + budget ---
        state = load_state()
        budget = load_budget()
        assert budget["week_spent"] == 0.0
        assert budget["mode"] == "NORMAL"
        assert state["total_earned"] == 0.0
        assert state["total_spent"] == 0.0

        # --- 1. Buyer creates $5 code-review job ---
        job = {
            "id": "e2e-job-001",
            "priceValue": 5.0,
            "slaMinutes": 1440,
            "description": "Code Review — TypeScript/React",
            "name": "Code Review — TypeScript/React",
            "status": "pending",
        }
        offering = {
            "name": "Code Review — TypeScript/React",
            "priceUSDC": 5,
            "category": "code-review",
            "slaHours": 24,
        }

        # --- 2. VP Earner receives & scores the job ---
        accept, reason = should_take_job(job, offering, budget)
        assert accept is True, f"Job should be accepted: {reason}"
        score, reasons = score_job(job, offering, budget)
        assert score >= SCORE_THRESHOLD
        print(f"\n  Score: {score}/100 — {reasons}")

        # --- 3. Job accepted, budget set (idempotency mark) ---
        assert job["id"] not in state["processed_job_ids"]
        state["processed_job_ids"].append(job["id"])
        save_state(state)

        # --- 4. Skill executes → real artifacts ---
        proof = execute_deliverable(job, offering)
        assert len(proof["artifacts"]) > 0, "Must produce artifact files"
        assert len(proof["logs"]) > 0, "Must produce execution logs"
        assert len(proof["deliverable"]) > 50, "Deliverable must be substantive"
        assert proof["compute_cost_usd"] == 0.50

        print(f"  Artifacts: {len(proof['artifacts'])}")
        print(f"  Hashes: {proof['artifact_hashes']}")

        # --- 5. Quality gate + self-verify pass ---
        verified, issues = self_verify(proof)
        assert verified is True, f"self_verify failed: {issues}"

        quality_ok, quality_issues = run_quality_gate(proof)
        assert quality_ok is True, f"Quality gate failed: {quality_issues}"
        print(f"\n  self_verify: ✓\n  quality_gate: ✓")

        # --- 6. Submit → revenue PENDING ---
        payout = float(job["priceValue"])
        compute_cost = proof["compute_cost_usd"]
        state["pending_payments"][job["id"]] = {
            "amount": payout,
            "submitted_at": "2026-10-06T12:00:00Z",
            "offering": offering["name"],
        }
        state["total_spent"] += compute_cost
        budget["week_spent"] += compute_cost
        budget["day_spent"] += compute_cost
        save_state(state)
        save_budget(budget)

        # Verify: still pending, not yet revenue
        state = load_state()
        budget = load_budget()
        assert job["id"] in state["pending_payments"]
        assert state["total_earned"] == 0.0
        assert budget["week_revenue"] == 0.0
        assert budget["week_spent"] == 0.50

        # --- 7. Buyer completes → revenue confirmed ---
        pending = state["pending_payments"].pop(job["id"])
        state["total_earned"] += pending["amount"]
        budget["week_revenue"] += pending["amount"]
        save_state(state)
        save_budget(budget)

        # FINAL: profit calculation
        state = load_state()
        budget = load_budget()
        assert state["total_earned"] == 5.0
        assert state["total_spent"] == 0.50
        profit = state["total_earned"] - state["total_spent"]
        assert profit == 4.50
        assert budget["week_revenue"] == 5.0

        print(f"\n  FINAL:")
        print(f"    Revenue:  ${state['total_earned']:.2f}")
        print(f"    Expense:  ${state['total_spent']:.2f}")
        print(f"    Profit:   ${profit:.2f}")
        print(f"    Margin:   {(state['total_earned']/state['total_spent']):.1f}x")

    def test_duplicate_job_blocked(self, e2e_env):
        """After a job is processed, the same job ID must NOT execute again."""
        job = {"id": "dup-001", "priceValue": 5.0, "slaMinutes": 1440,
               "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 5, "category": "code-review", "slaHours": 24}
        budget = {"week_spent": 0.0, "day_spent": 0.0, "week_revenue": 0.0,
                  "day_revenue": 0.0, "mode": "NORMAL", "last_reset": date.today().isoformat()}

        # First pass — accepted + processed
        accept1, _ = should_take_job(job, offering, budget)
        assert accept1 is True

        state = load_state()
        state["processed_job_ids"].append(job["id"])
        save_state(state)

        # Second pass — must reject
        accept2, reason2 = should_take_job(job, offering, budget)
        assert accept2 is False
        assert reason2 == "already_processed"
        print(f"\n  Duplicate blocked: '{reason2}'")

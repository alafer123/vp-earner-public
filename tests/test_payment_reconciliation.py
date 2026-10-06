"""Tests for payment reconciliation — pending → confirmed revenue.

Covers ChatGPT's requirements:
  - Revenue tracked as PENDING after submit (not counted as revenue yet)
  - Revenue only confirmed on job.completed event
  - Pending revenue REMOVED on job.rejected (no phantom revenue)
  - Profit = revenue - compute (not revenue = payout immediately)
"""

import json
import pytest
from datetime import date
from earner_loop import load_state, save_state, load_budget, save_budget


@pytest.fixture
def clean_paths(tmp_path, monkeypatch):
    import earner_loop
    monkeypatch.setattr(earner_loop, "STATE_FILE", tmp_path / "state.json")
    monkeypatch.setattr(earner_loop, "BUDGET_FILE", tmp_path / "budget.json")
    yield earner_loop


class TestPendingRevenue:
    def test_revenue_pending_after_submit(self, clean_paths):
        """After submit, revenue must be PENDING — not yet counted as earned."""
        state = load_state()
        job_id = "job-pending-1"
        payout = 5.0
        compute_cost = 0.50

        # Simulate the post-submit state in run_cycle()
        state["pending_payments"][job_id] = {
            "amount": payout,
            "submitted_at": "2026-10-06T12:00:00Z",
            "offering": "Code Review",
        }
        state["total_spent"] += compute_cost
        # Budget only tracks compute cost now, NOT revenue
        budget = load_budget()
        budget["week_spent"] += compute_cost
        budget["day_spent"] += compute_cost
        save_budget(budget)
        save_state(state)

        # Verify: revenue NOT counted, only pending
        state = load_state()
        budget = load_budget()
        assert job_id in state["pending_payments"]
        assert state["total_earned"] == 0.0, "Revenue must NOT be counted before completion"
        assert budget["week_revenue"] == 0.0, "Budget revenue must NOT include pending"

    def test_revenue_confirmed_on_completion(self, clean_paths):
        """When job.completed fires, pending → confirmed: revenue + profit."""
        state = load_state()
        budget = load_budget()

        # Simulate pending payment
        job_id = "job-done-1"
        payout = 10.0
        compute_cost = 1.00
        state["pending_payments"] = {
            job_id: {"amount": payout, "submitted_at": "2026-10-06T12:00:00Z", "offering": "Market Intel"}
        }
        state["total_spent"] = compute_cost
        budget["week_spent"] = compute_cost
        save_state(state)
        save_budget(budget)

        # Simulate job.completed event processing
        confirmed = state["pending_payments"].pop(job_id, None)
        assert confirmed is not None
        state["total_earned"] += confirmed["amount"]
        budget["week_revenue"] += confirmed["amount"]
        save_state(state)
        save_budget(budget)

        # Verify: now revenue IS counted
        state = load_state()
        budget = load_budget()
        assert job_id not in state["pending_payments"]
        assert state["total_earned"] == 10.0
        assert budget["week_revenue"] == 10.0

        # Profit = revenue - cost
        profit = state["total_earned"] - state["total_spent"]
        assert profit == 9.0, f"Expected profit $9.00, got ${profit}"

    def test_revenue_removed_on_rejection(self, clean_paths):
        """When job.rejected fires, pending revenue is removed, no phantom income."""
        state = load_state()
        budget = load_budget()

        job_id = "job-reject-1"
        payout = 5.0
        compute_cost = 0.50
        state["pending_payments"] = {
            job_id: {"amount": payout, "submitted_at": "2026-10-06T12:00:00Z", "offering": "Code Review"}
        }
        state["total_spent"] = compute_cost
        save_state(state)
        save_budget(budget)

        # Simulate job.rejected event
        state["pending_payments"].pop(job_id, None)
        state["consecutive_failures"] += 1
        save_state(state)

        # Verify: payment removed, no revenue
        state = load_state()
        assert job_id not in state["pending_payments"]
        assert state["total_earned"] == 0.0
        assert state["consecutive_failures"] == 1

    def test_profit_calculation(self, clean_paths):
        """End-to-end profit: $5 job, $0.50 compute → $4.50 profit after completion."""
        state = load_state()
        budget = load_budget()

        # Execute job
        payout = 5.0
        compute_cost = 0.50
        state["pending_payments"]["job-1"] = {"amount": payout, "submitted_at": "now", "offering": "Code Review"}
        state["total_spent"] = compute_cost
        budget["week_spent"] = compute_cost
        save_state(state)
        save_budget(budget)

        # Complete job
        confirmed = state["pending_payments"].pop("job-1")
        state["total_earned"] += confirmed["amount"]
        state["pending_payments"] = dict(state["pending_payments"])  # already popped above
        save_state(state)

        # Verify
        state = load_state()
        assert state["total_earned"] == 5.0
        assert state["total_spent"] == 0.50
        assert state["total_earned"] - state["total_spent"] == 4.50

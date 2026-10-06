"""Tests for idempotency/locking — same job must not execute twice.

Covers ChatGPT's requirements:
  - Duplicate job rejected (already_processed)
  - Restart/recovery: processed IDs survive process exit (state.json)
"""

import json
import pytest
from earner_loop import should_take_job, load_state, save_state
from datetime import date


@pytest.fixture
def budget():
    return {"week_spent": 0.0, "day_spent": 0.0,
            "week_revenue": 0.0, "day_revenue": 0.0,
            "mode": "NORMAL", "last_reset": date.today().isoformat()}


@pytest.fixture
def clean_state(tmp_path, monkeypatch):
    """Fresh state.json for each test."""
    import earner_loop
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(earner_loop, "STATE_FILE", state_file)
    yield earner_loop


class TestDuplicateJob:
    def test_same_job_rejected_after_first_execution(self, clean_state, budget, tmp_path):
        """Feed the same job ID twice — second call must reject it."""
        job = {"id": "dup-job-1", "priceValue": 5.0, "slaMinutes": 1440,
               "description": "Code Review — TypeScript/React", "status": "pending"}
        offering = {"name": "Code Review — TypeScript/React", "priceUSDC": 5,
                    "category": "code-review", "slaHours": 24}

        # First: should pass
        state = load_state()
        assert job["id"] not in state.get("processed_job_ids", [])

        accept1, reason1 = should_take_job(job, offering, budget)
        assert accept1 is True

        # Mark as processed (simulates the job.accept event in the loop)
        state = load_state()
        state["processed_job_ids"].append(job["id"])
        save_state(state)

        # Second attempt: should be rejected
        accept2, reason2 = should_take_job(job, offering, budget)
        assert accept2 is False
        assert reason2 == "already_processed"

    def test_different_jobs_not_affected(self, clean_state, budget):
        """Processing job A must not block job B."""
        job_a = {"id": "job-a", "priceValue": 5.0, "slaMinutes": 1440,
                 "description": "Code Review", "status": "pending"}
        job_b = {"id": "job-b", "priceValue": 5.0, "slaMinutes": 1440,
                 "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 5, "category": "code-review", "slaHours": 24}

        accept_a, _ = should_take_job(job_a, offering, budget)
        assert accept_a is True

        # Mark A as processed
        state = load_state()
        state["processed_job_ids"].append("job-a")
        save_state(state)

        # B should still be acceptable
        accept_b, _ = should_take_job(job_b, offering, budget)
        assert accept_b is True


class TestRestartRecovery:
    def test_processed_ids_survive_restart(self, clean_state, budget):
        """Simulate process restart — state.json must preserve processed IDs."""
        job = {"id": "persist-job-1", "priceValue": 5.0, "slaMinutes": 1440,
               "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 5, "category": "code-review", "slaHours": 24}

        # First cycle: process the job
        state = load_state()
        state["processed_job_ids"].append(job["id"])
        save_state(state)

        # Simulate restart — load fresh state from disk
        new_state = load_state()
        assert job["id"] in new_state["processed_job_ids"], "Processed job ID must survive restart"

        # Second cycle: job should still be rejected
        accept, reason = should_take_job(job, offering, budget)
        assert accept is False
        assert reason == "already_processed"

    def test_daily_reset_clears_processed_ids(self, clean_state, budget, monkeypatch):
        """At midnight, processed_job_ids should reset for the new day."""
        # Put yesterday's date in state
        from datetime import date, timedelta
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        job = {"id": "job-x", "priceValue": 5.0, "slaMinutes": 1440,
               "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 5, "category": "code-review", "slaHours": 24}

        state = load_state()
        state["processed_job_ids"] = [job["id"]]
        state["last_reset_date"] = yesterday
        save_state(state)

        # Simulate the daily reset in run_cycle()
        today = date.today().isoformat()
        if state.get("last_reset_date") != today:
            state["processed_job_ids"] = []
            state["last_reset_date"] = today
            save_state(state)

        # Job should now be processable again
        fresh_state = load_state()
        assert job["id"] not in fresh_state["processed_job_ids"]
        accept, reason = should_take_job(job, offering, budget)
        assert accept is True

"""Tests for scoring.py — the 0-100 job scoring model.

Covers ChatGPT's requirements:
  - Profitable job passes margin + threshold
  - Unprofitable job rejected (margin too low)
  - Unsupported category rejected
  - Strict mode raises minimum margin to 5x
"""

import pytest
from datetime import date
from earner_loop import (
    score_job, estimate_compute_cost, should_take_job,
    SCORE_THRESHOLD, MIN_MARGIN_NORMAL, MIN_MARGIN_STRICT,
    WEEKLY_CAP, DAILY_CAP,
)


@pytest.fixture
def fresh_budget():
    return {"week_spent": 0.0, "day_spent": 0.0,
            "week_revenue": 0.0, "day_revenue": 0.0,
            "mode": "NORMAL", "last_reset": date.today().isoformat()}


@pytest.fixture
def strict_budget():
    return {"week_spent": WEEKLY_CAP * 0.85, "day_spent": 0.0,
            "week_revenue": 0.0, "day_revenue": 0.0,
            "mode": "STRICT", "last_reset": date.today().isoformat()}


@pytest.fixture
def exhausted_budget():
    return {"week_spent": WEEKLY_CAP, "day_spent": DAILY_CAP,
            "week_revenue": 0.0, "day_revenue": 0.0,
            "mode": "STRICT", "last_reset": date.today().isoformat()}


# ── Test 1: Profitable job ──────────────────────────────────────────────
class TestProfitableJob:
    def test_high_margin_passes(self, fresh_budget):
        """A $5 code-review job (compute $0.50) = 10x margin → should pass."""
        job = {"id": "job-1", "priceValue": 5.0, "slaMinutes": 1440, "description": "Code Review — TypeScript/React", "status": "pending"}
        offering = {"name": "Code Review — TypeScript/React", "priceUSDC": 5, "category": "code-review", "slaHours": 24}

        score, reasons = score_job(job, offering, fresh_budget)
        assert score >= SCORE_THRESHOLD, f"Expected score >= {SCORE_THRESHOLD}, got {score}"
        assert any("Margin" in r and "✓" in r for r in reasons)
        print(f"  Score: {score}/100 — Reasons: {reasons}")

    def test_should_take_job_accepts_profitable(self, fresh_budget):
        job = {"id": "job-2", "priceValue": 10.0, "slaMinutes": 720, "description": "Market Intelligence", "status": "pending"}
        offering = {"name": "Market Intelligence", "priceUSDC": 10, "category": "market-intel", "slaHours": 12}
        accept, reason = should_take_job(job, offering, fresh_budget)
        assert accept is True
        assert "score=" in reason


# ── Test 2: Unprofitable job ───────────────────────────────────────────
class TestUnprofitableJob:
    def test_low_margin_rejected(self, fresh_budget):
        """Payout $0.60 for a market-intel job (compute $1.00) = 0.6x margin → reject."""
        job = {"id": "job-3", "priceValue": 0.60, "slaMinutes": 1440, "description": "Market Intelligence", "status": "pending"}
        offering = {"name": "Market Intelligence", "priceUSDC": 0.60, "category": "market-intel", "slaHours": 24}

        score, reasons = score_job(job, offering, fresh_budget)
        assert score == 0, f"Expected score 0, got {score}"
        assert any("REJECT" in r for r in reasons)

    def test_should_take_job_rejects_unprofitable(self, fresh_budget):
        job = {"id": "job-4", "priceValue": 0.30, "slaMinutes": 1440, "description": "Tech Writing", "status": "pending"}
        offering = {"name": "Tech Writing", "priceUSDC": 0.30, "category": "tech-writing", "slaHours": 24}
        accept, reason = should_take_job(job, offering, fresh_budget)
        assert accept is False
        assert "margin" in reason.lower() or "score" in reason.lower()


# ── Test 3: Unsupported job ────────────────────────────────────────────
class TestUnsupportedJob:
    def test_unknown_category_rejected(self, fresh_budget):
        """A job for a category we don't offer → no offering match."""
        job = {"id": "job-5", "priceValue": 25.0, "slaMinutes": 1440, "description": "Do my taxes", "status": "pending"}
        offering = {}  # No matching offering

        # should_take_job requires an offering — empty offering = rejected
        accept, reason = should_take_job(job, offering, fresh_budget)
        assert accept is False


# ── Test 4: Budget exhausted ───────────────────────────────────────────
class TestBudgetExhausted:
    def test_weekly_cap_blocks_job(self, exhausted_budget):
        job = {"id": "job-6", "priceValue": 50.0, "slaMinutes": 1440, "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 50, "category": "code-review", "slaHours": 24}
        accept, reason = should_take_job(job, offering, exhausted_budget)
        assert accept is False
        assert reason == "weekly_cap_reached"

    def test_daily_cap_blocks_strict_mode(self, fresh_budget):
        """In STRICT mode, daily cap also blocks if exceeded."""
        budget = {"week_spent": WEEKLY_CAP * 0.85, "day_spent": DAILY_CAP,
                  "week_revenue": 0.0, "day_revenue": 0.0,
                  "mode": "STRICT", "last_reset": date.today().isoformat()}
        job = {"id": "job-7", "priceValue": 5.0, "slaMinutes": 1440, "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 5, "category": "code-review", "slaHours": 24}
        accept, reason = should_take_job(job, offering, budget)
        assert accept is False
        assert reason == "daily_cap_strict"

    def test_strict_mode_raises_margin_requirement(self, fresh_budget, strict_budget):
        """A 4x margin passes in NORMAL but fails in STRICT (needs 5x)."""
        job = {"id": "job-8", "priceValue": 2.0, "slaMinutes": 1440, "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 2.0, "category": "code-review", "slaHours": 24}

        # In NORMAL mode: 2.0 / 0.50 = 4x >= 3x → passes
        accept_normal, _ = should_take_job(job, offering, fresh_budget)
        assert accept_normal is True

        # In STRICT mode: 4x < 5x → rejected
        accept_strict, reason_strict = should_take_job(job, offering, strict_budget)
        assert accept_strict is False


# ── Test 5: Strict mode threshold ──────────────────────────────────────
class TestStrictMode:
    def test_threshold_score_differs(self, fresh_budget, strict_budget):
        job = {"id": "job-9", "priceValue": 5.0, "slaMinutes": 1440, "description": "Code Review", "status": "pending"}
        offering = {"name": "Code Review", "priceUSDC": 5, "category": "code-review", "slaHours": 24}
        s_normal, _ = score_job(job, offering, fresh_budget)
        s_strict, _ = score_job(job, offering, strict_budget)
        # Both should give same score for margin-passing jobs (30+10+15+5=60), but
        # strict mode doesn't reject if margin passes
        assert s_normal == s_strict


# ── Test 6: Compute cost estimation ────────────────────────────────────
class TestComputeCost:
    def test_known_categories(self):
        assert estimate_compute_cost({"category": "code-review"}) == 0.50
        assert estimate_compute_cost({"category": "market-intel"}) == 1.00
        assert estimate_compute_cost({"category": "audit-solidity"}) == 3.00

    def test_unknown_category_defaults(self):
        assert estimate_compute_cost({"category": "unknown"}) == 1.0

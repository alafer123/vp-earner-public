"""
Budget governor for ACP provider.

Hard limits:
- Weekly compute cap (overrides all decisions)
- Daily cap (soft)
- Mode switching: NORMAL (3x min margin) → STRICT (5x min margin) at 80% spend
- Kill-switch at N consecutive evaluation failures
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional


@dataclass
class BudgetConfig:
    weekly_cap_usd: float = 199.00
    daily_cap_usd: float = 28.00
    strict_threshold_usd: float = 159.20  # 80% of weekly
    min_margin_multiplier: float = 3.0
    strict_mode_margin_multiplier: float = 5.0
    kill_switch_failures: int = 3
    max_pending_jobs: int = 2
    weekly_reset_day: int = 0  # 0 = Monday (UTC)


@dataclass
class BudgetState:
    week_start: datetime
    spent_this_week: float = 0.0
    spent_today: float = 0.0
    revenue_this_week: float = 0.0
    consecutive_failures: int = 0
    mode: str = "NORMAL"  # NORMAL | STRICT | KILLED | BUDGET_CAP

    def effective_min_margin(self, config: BudgetConfig) -> float:
        if self.mode == "STRICT":
            return config.strict_mode_margin_multiplier
        return config.min_margin_multiplier


def get_current_mode(state: BudgetState, config: BudgetConfig) -> str:
    """Return the current operating mode based on spend and failure count."""
    if state.consecutive_failures >= config.kill_switch_failures:
        return "KILLED"
    if state.spent_this_week >= config.weekly_cap_usd:
        return "BUDGET_CAP"
    if state.spent_this_week >= config.strict_threshold_usd:
        return "STRICT"
    return "NORMAL"


def should_accept_new_job(state: BudgetState, config: BudgetConfig, pending_count: int = 0) -> tuple[bool, str]:
    """
    Return (accept, reason). If accept is False, the cycle should stop or skip.
    """
    if state.consecutive_failures >= config.kill_switch_failures:
        return False, f"kill_switch: {state.consecutive_failures} consecutive failures"
    if state.spent_this_week >= config.weekly_cap_usd:
        return False, f"budget_cap: ${state.spent_this_week:.2f} / ${config.weekly_cap_usd}"
    if pending_count >= config.max_pending_jobs:
        return False, f"max_pending: {pending_count} / {config.max_pending_jobs}"
    return True, "ok"


def record_spend(state: BudgetState, compute_cost_usd: float, payout_usdc: float) -> None:
    """Record a completed job. Updates spend, revenue, and resets failure counter."""
    state.spent_this_week += compute_cost_usd
    state.spent_today += compute_cost_usd
    state.revenue_this_week += payout_usdc
    state.consecutive_failures = 0  # reset on success


def record_failure(state: BudgetState) -> None:
    """Record a failed evaluation. May trigger kill-switch."""
    state.consecutive_failures += 1


def maybe_weekly_reset(state: BudgetState, config: BudgetConfig) -> bool:
    """
    Reset weekly counters if a new week has begun.
    Returns True if reset happened.
    """
    now = datetime.now(timezone.utc)
    if state.week_start.tzinfo is None:
        state.week_start = state.week_start.replace(tzinfo=timezone.utc)

    days_since_start = (now - state.week_start).days
    if days_since_start >= 7:
        state.week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        state.spent_this_week = 0.0
        state.revenue_this_week = 0.0
        # NOTE: do NOT reset consecutive_failures here — carry forward
        return True
    return False

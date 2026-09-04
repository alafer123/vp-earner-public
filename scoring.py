"""
Job scoring model for ACP marketplace provider.

Scores each candidate job 0-100 across four dimensions:
- Margin (40%): payout vs estimated compute cost
- Capability match (30%): can we actually deliver this?
- Deadline feasibility (15%): SLA vs our execution time
- Requester reputation (15%): on-chain history, dispute count
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Job:
    id: str
    name: str
    description: str
    sla_minutes: int
    price_value: float
    price_type: str  # "fixed" | "negotiable"
    status: str
    requester: Optional[str] = None


@dataclass
class Offering:
    id: str
    name: str
    description: str
    sla_hours: int
    price_usdc: float


@dataclass
class ScoringResult:
    score: float  # 0-100
    margin: float  # payout / compute_cost
    compute_cost_estimate: float
    payout: float
    capability_score: float
    deadline_score: float
    reputation_score: float
    should_accept: bool


def estimate_compute_cost(sla_minutes: int, complexity: float = 1.0) -> float:
    """
    Estimate LLM inference cost for a job.

    Base: $0.50/hr of SLA for simple tasks, $2/hr for complex.
    Complexity multiplier applied for known-burdensome categories.
    """
    sla_hours = sla_minutes / 60
    return sla_hours * 0.50 * complexity


def complexity_multiplier(job_name: str) -> float:
    """Return cost multiplier based on job type keywords."""
    name = job_name.lower()
    if "security" in name or "audit" in name:
        return 2.0
    if "review" in name:
        return 1.5
    if "writing" in name or "documentation" in name:
        return 1.2
    return 1.0


def score_job(job: Job, our_offerings: list[Offering], min_margin: float = 3.0) -> ScoringResult:
    """
    Score a job against our offerings and budget.

    Returns a ScoringResult with should_accept flag based on the
    60-point threshold and minimum margin requirement.
    """
    # 1. Margin
    payout = job.price_value if job.price_type == "fixed" else 0
    compute_cost = estimate_compute_cost(job.sla_minutes, complexity_multiplier(job.name))
    margin = payout / compute_cost if compute_cost > 0 else 0
    margin_score = min(100, margin * 25)  # 4x margin = perfect score

    # 2. Capability match
    capability_score = 0
    job_name_lower = job.name.lower()
    job_desc_lower = job.description.lower()
    for offering in our_offerings:
        offering_name = offering.name.lower()
        offering_desc = offering.description.lower()
        # Strong match on offering name keywords
        for kw in offering_name.split():
            if len(kw) > 3 and kw in job_name_lower:
                capability_score = 100
                break
        if capability_score == 100:
            break
        # Weaker match on description overlap
        for kw in offering_desc.split():
            if len(kw) > 4 and kw in job_desc_lower:
                capability_score = 80
                break
        if capability_score > 0:
            break

    # 3. Deadline feasibility
    deadline_score = 100 if job.sla_minutes >= 180 else (job.sla_minutes / 180 * 100)

    # 4. Requester reputation (placeholder — production should check on-chain history)
    reputation_score = 70  # neutral default

    # Weighted total
    total = (
        margin_score * 0.40
        + capability_score * 0.30
        + deadline_score * 0.15
        + reputation_score * 0.15
    )

    return ScoringResult(
        score=round(total, 2),
        margin=round(margin, 2),
        compute_cost_estimate=compute_cost,
        payout=payout,
        capability_score=capability_score,
        deadline_score=round(deadline_score, 2),
        reputation_score=reputation_score,
        should_accept=total >= 60 and margin >= min_margin,
    )

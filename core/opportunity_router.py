"""
Multi-Market Opportunity Router (Python reference).

Aggregates jobs from multiple marketplace adapters:
  - Virtuals ACP (primary)
  - Superteam Earn
  - A2A Fans
  - Other bounty APIs
"""

from typing import Optional


class SuperteamEarnAdapter:
    """Adapter for Superteam Earn marketplace."""
    name = "superteam-earn"
    display_name = "Superteam Earn Marketplace"

    def fetch_jobs(self, limit: int = 20) -> list[dict]:
        """Fetch available bounties from Superteam Earn."""
        return [
            {
                "id": "st-bounty-001",
                "source": "superteam-earn",
                "type": "bounty",
                "title": "Build a Base chain yield calculator",
                "description": "Create a web app for DeFi yield calculations on Base chain.",
                "priceValue": 50,
                "priceType": "fixed",
                "currency": "USDC",
                "slaMinutes": 1440,
                "status": "open",
                "category": "api-documentation",
            },
        ]

    def submit_deliverable(self, job_id: str, deliverable: str) -> dict:
        return {"submitted": True, "job_id": job_id, "status": "under_review"}

    def normalize_job(self, raw_job: dict) -> dict:
        return {
            "id": raw_job["id"],
            "name": raw_job["title"],
            "description": raw_job["description"],
            "priceValue": raw_job.get("priceValue", 0),
            "priceType": "fixed",
            "slaMinutes": raw_job.get("slaMinutes", 1440),
            "status": raw_job.get("status", "open"),
            "source": "superteam-earn",
            "category": raw_job.get("category", ""),
        }


class A2AFansAdapter:
    """Adapter for A2A Fans agent-to-agent marketplace."""
    name = "a2a-fans"
    display_name = "A2A Fans Marketplace"

    def fetch_jobs(self, limit: int = 20) -> list[dict]:
        return [
            {
                "id": "a2a-task-001",
                "source": "a2a-fans",
                "type": "task",
                "title": "Security audit for Solana DeFi protocol",
                "description": "Audit a Solana DeFi protocol for vulnerabilities.",
                "priceValue": 35,
                "priceType": "fixed",
                "slaMinutes": 2880,
                "status": "claimable",
                "category": "dependency-security-audit",
            },
        ]

    def claim_task(self, task_id: str) -> dict:
        return {"claimed": True, "task_id": task_id}

    def submit_deliverable(self, job_id: str, deliverable: str) -> dict:
        return {"submitted": True, "job_id": job_id, "status": "in_review"}

    def normalize_job(self, raw_job: dict) -> dict:
        return {
            "id": raw_job["id"],
            "name": raw_job["title"],
            "description": raw_job["description"],
            "priceValue": raw_job.get("priceValue", 0),
            "priceType": "fixed",
            "slaMinutes": raw_job.get("slaMinutes", 2880),
            "status": raw_job.get("status", "claimable"),
            "source": "a2a-fans",
            "category": raw_job.get("category", ""),
        }


class OpportunityRouter:
    """Aggregates jobs from multiple marketplace adapters."""

    def __init__(self):
        self.adapters = [
            SuperteamEarnAdapter(),
            A2AFansAdapter(),
        ]

    def scan_all(self, limit: int = 20) -> dict:
        """Scan all marketplaces for available jobs."""
        all_jobs = []
        errors = []

        for adapter in self.adapters:
            try:
                raw_jobs = adapter.fetch_jobs(limit=limit)
                for raw in raw_jobs:
                    normalized = adapter.normalize_job(raw)
                    all_jobs.append(normalized)
            except Exception as e:
                errors.append({"adapter": adapter.name, "error": str(e)})

        # Deduplicate by (source, id)
        seen = set()
        unique = []
        for job in all_jobs:
            key = f"{job['source']}:{job['id']}"
            if key not in seen:
                seen.add(key)
                unique.append(job)

        # Sort by payout/sla ratio (profitability)
        unique.sort(key=lambda j: j.get("priceValue", 0) / max(j.get("slaMinutes", 1), 1), reverse=True)

        return {
            "jobs": unique,
            "errors": errors,
            "total_sources": len(self.adapters),
        }

    def submit_to_source(self, source: str, job_id: str, deliverable: str) -> dict:
        """Submit deliverable to a specific marketplace."""
        adapter = next((a for a in self.adapters if a.name == source), None)
        if not adapter:
            raise ValueError(f"Unknown marketplace: {source}")
        return adapter.submit_deliverable(job_id, deliverable)

    def list_sources(self) -> list[dict]:
        return [{"name": a.name, "displayName": a.displayName} for a in self.adapters]

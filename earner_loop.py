#!/usr/bin/env python3
"""
ACP Provider Earner Loop — orchestrator.

Runs one cycle of: scan → score → negotiate → execute → verify → submit → log.
Intended to be run by cron every 15-60 minutes.

This file is a sanitized reference. The real implementation will have:
- Real offering IDs from your ACP account
- Your wallet address in the env
- A real events.jsonl from `acp events listen`
- Real deliverable generation logic in `execute_deliverable()`
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ----- Configuration -----
# Use the .cmd shim on Windows (the bare "acp" is a POSIX shell wrapper)
ACP_CLI = "acp.cmd"  # adjust to your platform's acp-cli path
CRON_DIR = Path(__file__).parent
STATE_FILE = CRON_DIR / "state.json"
BUDGET_FILE = CRON_DIR / "budget.json"
EVENTS_FILE = CRON_DIR / "events.jsonl"


def run_acp_cmd(args: list[str]) -> dict:
    """Run an acp-cli command and return parsed JSON, or an error dict."""
    cmd = [ACP_CLI] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr.strip(), "code": result.returncode}
    try:
        return json.loads(result.stdout.strip())
    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON", "raw": result.stdout}


def load_state() -> dict:
    with open(STATE_FILE) as f:
        return json.load(f)


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_budget() -> dict:
    with open(BUDGET_FILE) as f:
        return json.load(f)


def scan_jobs() -> list[dict]:
    """Fetch all active jobs from the marketplace."""
    result = run_acp_cmd(["job", "list"])
    return result.get("jobs", []) if "jobs" in result else []


def scan_events() -> list[dict]:
    """
    Drain events from the listen output file if it exists.
    `acp events drain` requires --file <path>; without it, the call fails.
    """
    if not EVENTS_FILE.exists():
        return []
    result = run_acp_cmd(["events", "drain", "--file", str(EVENTS_FILE), "--limit", "20"])
    return result.get("events", []) if isinstance(result, dict) else []


def get_our_offerings() -> list[dict]:
    """List our registered offerings."""
    return run_acp_cmd(["offering", "list"]) or []


def execute_deliverable(job: dict, offering: dict) -> dict:
    """
    Execute the actual work and return proof artifacts.

    In a real implementation this is where your LLM/tool calls happen.
    The proof object must contain real artifacts (file paths, hashes,
    logs) — not just descriptions.
    """
    # --- Replace this with your real execution logic ---
    proof = {
        "job_id": job.get("id"),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": [],
        "logs": [],
        "compute_cost_usd": 1.0,
    }
    return proof


def self_verify(proof: dict) -> bool:
    """Verify the deliverable is real before submitting."""
    return len(proof.get("artifacts", [])) > 0 or len(proof.get("logs", [])) > 0


def submit_deliverable(job_id: str, deliverable: str) -> dict:
    """
    Submit the deliverable for evaluation.

    NOTE: the flag is --deliverable, not --memo (a common gotcha).
    """
    return run_acp_cmd([
        "provider", "submit",
        "--job-id", job_id,
        "--deliverable", deliverable,
    ])


def run_cycle() -> dict:
    """One full earner cycle."""
    print(f"=== ACP Earner Cycle Start: {datetime.now().isoformat()} ===")

    state = load_state()
    budget = load_budget()

    # 1. Scan
    jobs = scan_jobs()
    events = scan_events()
    offerings = get_our_offerings()

    # Combine + dedupe
    all_jobs = list({j.get("id"): j for j in jobs + [e.get("job", {}) for e in events] if j.get("id")}.values())
    print(f"Scanned: {len(all_jobs)} jobs | Offerings: {len(offerings)}")

    # 2. Score and process each job
    stats = {"scanned": len(all_jobs), "accepted": 0, "rejected": 0, "executed": 0,
             "payout_usdc": 0.0, "compute_cost_usd": 0.0}

    for job in all_jobs:
        if job.get("status") not in ("pending", "awaiting_provider"):
            continue

        # Score (in production, use scoring.py + budget.py)
        # ... (omitted for brevity — see scoring.py for the model)
        if not should_take_job(job, offerings, budget):
            stats["rejected"] += 1
            continue

        # 3. Negotiate
        job_id = job["id"]
        payout = job.get("priceValue", 0)
        budget_result = run_acp_cmd([
            "provider", "set-budget",
            "--job-id", job_id,
            "--amount", str(payout),
        ])
        if "error" in budget_result:
            stats["rejected"] += 1
            continue

        stats["accepted"] += 1

        # 4. Execute
        proof = execute_deliverable(job, offerings[0] if offerings else {})

        # 5. Verify
        if not self_verify(proof):
            state["consecutive_failures"] += 1
            save_state(state)
            continue

        # 6. Submit
        artifact_text = ", ".join(a.get("path", "") for a in proof.get("artifacts", []))
        submit_result = submit_deliverable(job_id, f"Proof: {artifact_text}")

        if "error" in submit_result:
            state["consecutive_failures"] += 1
            save_state(state)
            continue

        # 7. Record
        stats["executed"] += 1
        stats["payout_usdc"] += payout
        stats["compute_cost_usd"] += proof["compute_cost_usd"]
        state["consecutive_failures"] = 0
        save_state(state)

    print(f"Done: {stats}")
    return stats


def should_take_job(job: dict, offerings: list[dict], budget: dict) -> bool:
    """Stub — in production, call scoring.score_job() and check margin."""
    return job.get("priceType") == "fixed" and job.get("priceValue", 0) > 0


if __name__ == "__main__":
    result = run_cycle()
    # Print nothing on quiet cycles (no jobs found / no execution)
    if result["executed"] == 0 and result["accepted"] == 0:
        print("[SILENT]")
        sys.exit(0)
    print(json.dumps(result, indent=2))

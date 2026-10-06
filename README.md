# VP Earner — Autonomous ACP Provider Agent

An autonomous earning loop for the [Virtuals Protocol](https://virtuals.io) Agent Commerce Protocol (ACP) marketplace. The agent scans for jobs, scores them by margin and capability, routes them to modular skills, passes every deliverable through a quality gate, and collects USDC — all within a hard compute budget and a kill-switch on consecutive failures.

> Sanitized reference implementation. No live credentials, wallet keys, or private offering IDs. Use as a starting point for your own ACP provider.

## What it does

1. **Scans** the ACP marketplace for active jobs (via cron every 5 minutes)
2. **Scores** each job 0-100 based on margin (40%), capability match (30%), deadline feasibility (15%), and requester reputation (15%)
3. **Routes** to the appropriate modular skill via `SkillRouter` (code review, security audit, data transform, etc.)
4. **Executes** the deliverable with real evidence — file artifacts, content hashes, execution logs
5. **Quality gate** checks every deliverable for AI slop, fabricated claims, and placeholder text before submission
6. **Self-verifies** that all artifact files exist and the proof is non-trivial
7. **Submits** the deliverable via `acp provider submit`
8. **Reconciles** on-chain USDC release — revenue is tracked as **pending** until `job.completed` fires
9. **Logs** every cycle to an append-only ledger with performance metrics

### Key fixes from peer review (Oct 2026)

| Bug | Before | After |
|---|---|---|
| `should_take_job` | Stub: accepted any fixed-price job with price > 0 | Calls `score_job()` + `budget.py` cap enforcement |
| `execute_deliverable` | Returned empty `artifacts: []`, `logs: []` | Returns real artifact file paths + hashes |
| ACP CLI | No `--json` flag, parsing stdout as JSON | Always passes `--json` + `--chain-id` |
| Budget caps | `daily_cap_usd = 28` defined but never enforced | Daily/weekly caps enforced + auto-reset |
| Payment tracking | Revenue recorded immediately on submit | Revenue tracked as **pending**, confirmed on `job.completed` |
| Idempotency | Same job could process twice | `processed_job_ids` set in `state.json` |
| Daily reset | `spent_today` never reset | Date-based reset in `load_budget()` |
| Quality gate | No anti-slop checking | Banned phrases + structural slop detection |

## Architecture (V2)

```
                     ┌──────────────────┐
                     │   Cron Schedule  │
                     │   (every 5 min)  │
                     └────────┬─────────┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │       Opportunity Router    │
              │  (scan_events + scan_jobs)  │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │         Job Analyzer        │
              │  (dedupe + idempotency)      │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │      Profit Estimator        │
              │  (score_job + budget check)  │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │      Capability Router      │
              │  (SkillRouter dispatches    │
              │   to matching skill)         │
              └──────────────┬──────────────┘
                             │
         ┌──────────────────┼───────────────────┐
         ▼                  ▼                    ▼
  Security Audit      Code Review      Data Transform
  skill.py            skill.py         skill.py
  (can_handle,        (can_handle,     (can_handle,
   estimate_cost)     estimate_cost)   estimate_cost)
         │                  │                    │
         └──────────────────┼───────────────────┘
                            ▼
              ┌─────────────────────────────┐
              │    Quality Gate (anti-slop) │
              │  - Banned AI phrases        │
              │  - Structural slop patterns │
              │  - Placeholder / TODO check │
              │  - Evidence quality score   │
              └──────────────┬──────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │     Evidence Builder        │
              │  (artifact hashing +        │
              │   proof packaging)          │
              └──────────────┬──────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │        SUBMIT               │
              │  (acp provider submit)      │
              └──────────────┬──────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │     Payment Reconcile       │
              │  (job.completed → revenue   │
              │   job.rejected → cleanup)  │
              └──────────────┬──────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │    Reputation Model         │
              │  (success rate + pricing    │
              │   learning)                 │
              └─────────────────────────────┘
```

### Skill Interface

Each skill implements five methods:

```python
can_handle(job)          → bool    # Does this skill match the job?
estimate_cost(job)       → float   # Estimated USD compute cost
execute(job)             → {deliverable, evidence, artifacts}
verify(result)           → {passed, score, issues}  # skill-specific verification
package_deliverable(result) → str   # final proof string for ACP submission
```

The `QualityGate` (anti-slop system) runs on every deliverable **before** submission:

```
BANNED PHRASES (17 checks)
  - "As an AI" / "I cannot browse" / "In today's digital age" ...

STRUCTURAL PATTERNS
  - Rule of Three: 3+ consecutive short bullet items
  - Uniform sentence length: 3+ consecutive same-length sentences
  - AI listicle openers

EVIDENCE CHECKS
  - File path references (machine-verifiable)
  - Quantitative data (counts, sizes)
  - Source citations

PASS: score >= 85/100
FAIL: regenerate or repair
```

## Service offerings

| Service | Price (USDC) | Est. Compute | Margin | Category |
|---|---|---|---|---|
| Code Review — TypeScript/React/Node | 5 | $0.50 | 10x | code-review |
| Code Review — TypeScript/React | 5 | $0.50 | 10x | code-review |
| Market Intelligence — Crypto/DeFi/AI | 10 | $1.00 | 10x | market-intel |
| Technical Writing — API Docs (OpenAPI) | 8 | $0.80 | 10x | tech-writing |
| Telegram Mini App Audit | 15 | $2.00 | 7.5x | audit |
| Smart Contract Audit — Solidity | 25 | $3.00 | 8.3x | audit-solidity |
| DeFi Yield Optimization Report | 12 | $1.00 | 12x | yield-opt |
| On-Chain Transaction Analysis | 10 | $0.75 | 13x | onchain-analysis |
| Token Vesting Schedule Analysis | 12 | $0.75 | 16x | vesting-analysis |

New Tier 1 offerings (V2):
- **Dependency Security Audit** — $5–15, machine-verifiable (SARIF + SBOM + evidence.json)
- **JSON/Data Transformation** — $1–5, schema-validated JSON output
- **API Documentation Generator** — $8–25, OpenAPI-validated specs

## Quickstart

```bash
# 1. Install the Virtuals ACP CLI
npm install -g @virtuals-protocol/acp-cli

# 2. Authenticate (uses VIRTUALS_API_KEY env var)
export VIRTUALS_API_KEY=acp-...

# 3. List your offerings
acp agent list  # find your agent ID
acp offering list  # see your registered services

# 4. Configure environment
cp .env.example .env
# Fill in VIRTUALS_API_KEY, WALLET_PRIVATE_KEY, CHAIN_ID

# 5. Run a manual cycle
python earner_loop.py

# 6. Schedule via Hermes cron (every 5 minutes)
#    Or use cron directly with the correct schedule:
#    0 */1 * * * cd /path/to/project && python earner_loop.py >> cycle.log 2>&1
#    (Note: * * * * * = every MINUTE, 0 * * * * = every HOUR)
```

## Budget governance

Hard cap: $199/week (overrides everything).
Strict mode kicks in at 80% of cap, raising minimum margin to 5x.
Kill-switch at 3 consecutive evaluation failures.
Daily reset: counters reset at midnight. Weekly reset: counters reset every Monday.

```
NORMAL MODE (0-80% spent)        STRICT MODE (80-100% spent)
  min margin: 3x                    min margin: 5x
  accept any qualifying job         accept only high-margin jobs
```

## Files

| File | Purpose |
|---|---|
| `earner_loop.py` | Main orchestrator with skill dispatch + quality gate |
| `scoring.py` | Job scoring model (margin / capability / deadline / reputation) |
| `budget.py` | Budget governor (weekly cap, mode switching, kill-switch, daily reset) |
| `core/quality_gate.py` | Anti-slop checker — banned phrases + structural + evidence checks |
| `core/skill_router.py` | Routes jobs to the right skill |
| `core/base_skill.py` | BaseSkill interface (can_handle, estimate_cost, execute, verify, package) |
| `skills/` | Modular skills (dependency-security-audit, code-review, json-data-transform) |
| `NOTICE.md` | Sanitization disclaimer |
| `.env.example` | Required env var shape (no actual values) |

## Production

The live production implementation runs in TypeScript at `vp-earner/run-cycle.ts → dist/run-cycle.js` with:
- ACP Node SDK (`@virtuals-protocol/acp-node-v2`) for event-driven job handling
- Node.js skill implementations in `core/` and `skills/`
- Same budget governor, quality gate, and payment reconciliation logic

## Security notes

- Never commit `.env` — contains wallet private key and API tokens
- The wallet must hold both ETH (for gas on Base) and USDC (for escrow buffer)
- Use a dedicated agent wallet, not your main treasury
- Set `WALLET_PRIVATE_KEY` via env, never hardcode
- Artifact hashes (SHA-256) provide tamper evidence for every deliverable

## Known limitations

- Compute budget requires approved Virtuals Spark credits
- Auto-signer policy must be approved in the Virtuals app for autonomous transactions
- First-cycle after credentials land may be slow (marketplace needs to index the new agent)

## License

MIT

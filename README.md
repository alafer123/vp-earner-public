# VP Earner — Autonomous ACP Provider Agent

An autonomous earning loop for the [Virtuals Protocol](https://virtuals.io) Agent Commerce Protocol (ACP) marketplace. The agent scans for jobs, scores them by margin and capability, executes deliverables with on-chain proof, and collects USDC. All within a hard compute budget and a kill-switch on consecutive failures.

> Sanitized reference implementation. No live credentials, wallet keys, or private offering IDs. Use as a starting point for your own ACP provider.

## What it does

1. Scans the ACP marketplace every 60 minutes for active jobs
2. Scores each job on margin (40%), capability match (30%), deadline feasibility (15%), and requester reputation (15%)
3. Negotiates budget using `acp provider set-budget`
4. Executes the deliverable with real evidence (no placeholders)
5. Self-verifies before submission
6. Submits proof via `acp provider submit --deliverable`
7. Reconciles on-chain USDC release
8. Logs every cycle to an append-only ledger

## Architecture

```
+--------------------+     +-------------------+     +-------------------+
|  Cron schedule     | --> |  earner_loop.py   | --> |  acp-cli (.cmd)   |
|  (every 60 min)    |     |  (orchestrator)   |     |  Virtuals ACP     |
+--------------------+     +-------------------+     +-------------------+
                                |                          |
                                v                          v
                         +--------------+            +---------------+
                         |  state.json  |            |  Base + Sol   |
                         | budget files |            |  USDC + ETH   |
                         +--------------+            +---------------+
```

## Quickstart

```bash
# 1. Install the Virtuals ACP CLI
npm install -g @virtuals-protocol/acp-cli

# 2. Authenticate (uses VIRTUALS_API_KEY env var)
export VIRTUALS_API_KEY=acp-...

# 3. Create your agent (or use existing)
acp agent list  # find your agent ID
acp offering list  # see your registered services

# 4. Configure environment
cp .env.example .env
# Fill in VIRTUALS_API_KEY, WALLET_PRIVATE_KEY, CHAIN_ID

# 5. Run a manual cycle
python earner_loop.py

# 6. Schedule it (cron example, every 60 minutes)
# * * * * * cd /path/to/project && python earner_loop.py >> cycle.log 2>&1
```

## Sample cycle output

```
=== VP Earner Cycle Start: 2026-09-04T01:25:09Z ===
Budget: $0.00 / $199 (0.0%) - NORMAL MODE
Min margin required: 3x
Consecutive failures: 0
Scanned: 0 jobs | Our offerings: 2

VP Earner Cycle Report - 2026-09-04 09:25 PHT
Scanned: 0 jobs | Accepted: 0 | Rejected: 0
Top rejections: none
Budget this week: $0.00 / $199 (0.0%)
Status: NORMAL MODE
Next cycle: 10:25 PHT
```

## Service offerings (sample)

A live provider registers offerings via `acp offering create`. Example structure:

| Offering | Price | SLA | Deliverable |
|---|---|---|---|
| Dependency Security Audit | 5 USDC | 6h | SARIF + Markdown + SBOM |
| Code Review (TypeScript/React) | 5 USDC | 24h | Markdown review report |
| Market Intelligence (DeFi/AI) | 10 USDC | 12h | Markdown briefing with cited sources |
| Technical Writing (API Docs) | 8 USDC | 24h | OpenAPI 3.1 spec + Markdown |

## Budget governance

Hard cap: $199/week (overrides everything).
Strict mode kicks in at 80% of cap, raising minimum margin to 5x.
Kill-switch at 3 consecutive evaluation failures.

```
NORMAL MODE (0-80% spent)        STRICT MODE (80-100% spent)
  min margin: 3x                    min margin: 5x
  accept any qualifying job         accept only high-margin jobs
```

## Files

- `earner_loop.py` - main orchestrator, run by cron
- `scoring.py` - job scoring model (margin / capability / deadline / reputation)
- `budget.py` - budget governor (weekly cap, mode switching, kill-switch)
- `NOTICE.md` - sanitization disclaimer
- `.env.example` - required env var shape (no real values)

## Security notes

- Never commit `.env` - contains wallet private key and API tokens
- The wallet must hold both ETH (for gas on Base) and USDC (for escrow buffer)
- Use a dedicated agent wallet, not your main treasury
- Set `WALLET_PRIVATE_KEY` via env, never hardcode

## Known limitations (as of Sept 2026)

- Compute budget requires approved Virtuals Spark credits
- Auto-signer policy must be approved in the Virtuals app for autonomous transactions
- First-cycle after credentials land may be slow (the marketplace needs to index the new agent)

## License

MIT

# VP Earner — Autonomous ACP Provider Agent

An autonomous earning loop for the [Virtuals Protocol](https://virtuals.io) Agent Commerce Protocol (ACP) marketplace. The agent scans for jobs, scores them by margin and capability, executes deliverables with on-chain proof, and collects USDC. All within a hard compute budget and a kill-switch on consecutive failures.

This is a sanitized, reference implementation. **No live credentials, wallet keys, or private offering IDs are included.** Use it as a starting point for your own ACP provider.

## What it does

1. **Scans** the ACP marketplace every 15–30 minutes for active jobs
2. **Scores** each job on margin (40%), capability match (30%), deadline feasibility (15%), and requester reputation (15%)
3. **Negotiates** budget using `acp provider set-budget`
4. **Executes** the deliverable with real evidence (no placeholders)
5. **Self-verifies** before submission
6. **Submits** proof via `acp provider submit --deliverable`
7. **Reconciles** on-chain USDC release
8. **Logs** every cycle to an append-only ledger for tuning

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Cron Schedule  │───▶│  earner_loop.py  │───▶│   acp-cli (.cmd)│
│  (every 60 min) │    │  (orchestrator)  │    │  Virtuals ACP   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                         │
                              ▼                         ▼
                       ┌──────────────┐         ┌──────────────┐
                       │  state.json  │         │  Base Chain  │
                       │ budget files │         │ (USDC + ETH) │
                       └──────────────┘         └──────────────┘
```

**Components:**
- `earner_loop.py` — main orchestrator, run by cron
- `scoring.py` — job scoring model (margin / capability / deadline / reputation)
- `budget.py` — budget governor with weekly cap and mode switching
- `acp/` — thin wrapper around `acp-cli` for type-safe calls

## Service offerings (sample)

A live provider registers offerings via `acp offering create`. Example structure:

| Offering | Price | SLA | Deliverable |
|---|---|---|---|
| Dependency Security Audit | 5 USDC | 6h | SARIF + Markdown + SBOM |
| Code Review (TypeScript/React) | 5 USDC | 24h | Markdown review report |

## Budget governance

Hard cap: **$199/week** (overrides everything).
Strict mode kicks in at 80% of cap, raising minimum margin to 5x.
Kill-switch at 3 consecutive evaluation failures.

## Setup

```bash
# 1. Install the Virtuals ACP CLI
npm install -g @virtuals-protocol/acp-cli

# 2. Create your agent
acp init

# 3. Create an offering
acp offering create --name "..." --price 5 --sla-hours 24

# 4. Configure environment
cp .env.example .env
# Fill in VIRTUALS_API_KEY, WALLET_PRIVATE_KEY, CHAIN_ID

# 5. Run a manual cycle
python earner_loop.py

# 6. Schedule it (cron example — every 60 minutes)
# * * * * * cd /path/to/project && python earner_loop.py >> cycle.log 2>&1
```

## Security notes

- **Never commit `.env`** — contains wallet private key and API tokens
- The wallet must hold both **ETH (for gas on Base)** and **USDC (for escrow buffer)**
- Use a **dedicated agent wallet**, not your main treasury

## License

MIT

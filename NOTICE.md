# Notice

This is a **sanitized reference implementation** of VP Earner.

No live credentials, wallet private keys, or private Virtuals ACP offering IDs
are included in this repository.

## Production vs. Reference

| Aspect | Production (vp-earner/) | This Repo (vp-earner-public/) |
|--------|------------------------|-------------------------------|
| Language | TypeScript | Python 3 |
| ACP SDK | `@virtuals-protocol/acp-node-v2` (event-driven) | `acp-cli` (polling) |
| Runtime | `node dist/run-cycle.js` (cron, every 5 min) | `python earner_loop.py` (cron, every 5 min) |
| Skills | `core/` + `skills/` (JS) | `core/` + `skills/` (Python) |

Both implementations share the same architecture:
- Scoring model (margin + capability + deadline + reputation)
- Budget governor (weekly cap, daily cap, strict mode, kill-switch)
- Quality gate (anti-slop: banned phrases + structural patterns + evidence checks)
- Skill router with idempotent job processing
- Payment reconciliation (revenue confirmed on `job.completed`)

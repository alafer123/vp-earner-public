# VP Earner — Sanitized Reference Implementation

This is a **sanitized, educational** copy of an autonomous ACP Provider agent.
All wallet addresses, offering IDs, private keys, and internal cron IDs have
been removed or replaced with placeholders.

## Use this as

- A starting point for your own ACP provider
- A reference for the scan-score-execute-deliver loop
- An example of budget governance for agent spending

## Do not

- Use the placeholder IDs in this repo as live values
- Commit a real `.env` file (see `.env.example` for the required shape)
- Run this on a wallet you can't afford to drain — bugs can cause failed transactions

## What's included

- `scoring.py` — the job scoring model (margin / capability / deadline / reputation)
- `budget.py` — the budget governor (weekly cap, mode switching, kill-switch)
- `earner_loop.py` — the orchestrator that ties them together
- `README.md` — overview, architecture, and setup

## License

MIT

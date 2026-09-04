# scripts/

Operational scripts for running the earner loop. Not part of the core reference implementation.

## setup.sh (Linux/macOS)

```bash
#!/bin/bash
# Install acp-cli, configure env, verify auth
npm install -g @virtuals-protocol/acp-cli
export VIRTUALS_API_KEY=$(grep ^VIRTUALS_API_KEY= ../../.env | cut -d= -f2-)
acp offering list  # verify auth works
```

## setup.ps1 (Windows)

```powershell
# Install acp-cli
npm install -g @virtuals-protocol/acp-cli

# Load env from hermes
Get-Content D:\AI-CORE\hermes\.env | ForEach-Object {
  if ($_ -match '^VIRTUALS_API_KEY=(.+)$') { $env:VIRTUALS_API_KEY = $matches[1] }
}

# Verify
& "D:\AI-CORE\npm-global\acp.cmd" offering list
```

## cron entry (every 60 minutes)

```cron
* * * * * cd /path/to/vp-earner-public && python earner_loop.py >> cycle.log 2>&1
```

$ErrorActionPreference = 'Stop'

Invoke-RestMethod -Uri 'http://127.0.0.1:43118/healthz' -TimeoutSec 5 | ConvertTo-Json -Depth 5

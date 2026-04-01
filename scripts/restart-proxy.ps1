$ErrorActionPreference = 'Stop'

& (Join-Path $PSScriptRoot 'stop-proxy.ps1')
& (Join-Path $PSScriptRoot 'start-proxy.ps1')

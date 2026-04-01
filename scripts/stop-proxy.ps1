$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$PidPath = Join-Path $Root 'run\proxy.pid'

if (-not (Test-Path $PidPath)) {
    Write-Host 'Proxy is not running.'
    exit 0
}

$ProxyPid = [int](Get-Content -Path $PidPath -Raw)
$Process = Get-Process -Id $ProxyPid -ErrorAction SilentlyContinue
if ($Process) {
    Stop-Process -Id $ProxyPid -Force
}

Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
Write-Host "Proxy stopped: $ProxyPid"

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$RunDir = Join-Path $Root 'run'
$LogDir = Join-Path $Root 'logs'
$PidPath = Join-Path $RunDir 'proxy.pid'
$StdoutLogPath = Join-Path $LogDir 'proxy.stdout.log'
$StderrLogPath = Join-Path $LogDir 'proxy.stderr.log'
$VenvPath = Join-Path $Root '.venv'
$VenvPython = Join-Path $VenvPath 'Scripts\python.exe'
$BasePython = (& py -3.9 -c "import sys; print(sys.executable)").Trim()
$HealthUrl = 'http://127.0.0.1:43118/healthz'

New-Item -ItemType Directory -Force -Path $RunDir, $LogDir | Out-Null

function Test-PythonExecutable {
    param([string]$PythonPath)

    if (-not $PythonPath) {
        return $false
    }

    try {
        & $PythonPath -c "import sys; print(sys.version)" | Out-Null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

if (Test-Path $PidPath) {
    $ExistingPid = [int](Get-Content -Path $PidPath -Raw)
    $ExistingProcess = Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue
    if ($ExistingProcess) {
        try {
            $Health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
            if ($Health.ok -eq $true) {
                Write-Host "Proxy already running with PID $ExistingPid"
                exit 0
            }
        } catch {
        }
        Stop-Process -Id $ExistingPid -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $VenvPython)) {
    py -3.9 -m venv $VenvPath
}

if (-not (Test-PythonExecutable $BasePython)) {
    throw 'No usable Python 3.9 runtime found for the proxy.'
}

if (-not (Test-PythonExecutable $VenvPython)) {
    if (Test-Path $VenvPath) {
        Remove-Item -LiteralPath $VenvPath -Recurse -Force
    }
    & $BasePython -m venv $VenvPath
}

$RuntimePython = $VenvPython
if (-not (Test-PythonExecutable $RuntimePython)) {
    $RuntimePython = $BasePython
}

& $RuntimePython -m pip install --upgrade pip | Out-Null
& $RuntimePython -m pip install -r (Join-Path $Root 'requirements.txt') | Out-Null

$ArgumentList = @(
    '-m', 'uvicorn', 'app:app',
    '--host', '127.0.0.1',
    '--port', '43118',
    '--log-level', 'info'
)

$Process = Start-Process -FilePath $RuntimePython `
    -ArgumentList $ArgumentList `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $StdoutLogPath `
    -RedirectStandardError $StderrLogPath `
    -PassThru

$Process.Id | Set-Content -Path $PidPath -Encoding ascii

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $Health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
        if ($Health.ok -eq $true) {
            Write-Host "Proxy started with PID $($Process.Id)"
            exit 0
        }
    } catch {
    }
}

Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PidPath -Force -ErrorAction SilentlyContinue
$RecentErrors = ''
if (Test-Path $StderrLogPath) {
    $RecentErrors = (Get-Content -Path $StderrLogPath -Tail 20 | Out-String).Trim()
}
if ($RecentErrors) {
    throw "Proxy failed to become healthy within 30 seconds.`n$RecentErrors"
}
throw 'Proxy failed to become healthy within 30 seconds.'

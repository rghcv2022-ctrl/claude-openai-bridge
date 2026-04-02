param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardArgs
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $Root 'logs\claude-wrapper'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$LogPath = Join-Path $LogDir "$Stamp-$PID.log"

function Write-WrapperLog {
    param([string]$Message)

    $Line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'), $Message
    Add-Content -Path $LogPath -Value $Line -Encoding ascii
}

function Format-EnvValue {
    param([string]$Name)

    $Value = [Environment]::GetEnvironmentVariable($Name, 'Process')
    if ([string]::IsNullOrEmpty($Value)) {
        return '<unset>'
    }

    return $Value
}

if (-not $ForwardArgs -or $ForwardArgs.Count -eq 0) {
    Write-WrapperLog 'No target executable was provided to the wrapper.'
    throw 'No target executable was provided to the wrapper.'
}

$Target = $ForwardArgs[0]
$RemainingArgs = @()
if ($ForwardArgs.Count -gt 1) {
    $RemainingArgs = $ForwardArgs[1..($ForwardArgs.Count - 1)]
}

Write-WrapperLog "cwd=$((Get-Location).Path)"
Write-WrapperLog "target=$Target"
Write-WrapperLog "arg_count=$($RemainingArgs.Count)"

for ($i = 0; $i -lt $RemainingArgs.Count; $i++) {
    Write-WrapperLog ("arg[{0}]={1}" -f $i, $RemainingArgs[$i])
}

$ObservedVars = @(
    'ANTHROPIC_BASE_URL',
    'ANTHROPIC_API_KEY',
    'ANTHROPIC_AUTH_TOKEN',
    'ANTHROPIC_CUSTOM_HEADERS',
    'CLAUDE_CODE_SKIP_AUTH_LOGIN',
    'CLAUDE_CODE_ENTRYPOINT'
)

foreach ($Name in $ObservedVars) {
    Write-WrapperLog ("env.before.{0}={1}" -f $Name, (Format-EnvValue -Name $Name))
}

$ForcedEnv = [ordered]@{
    'ANTHROPIC_BASE_URL' = 'http://127.0.0.1:43118'
    'ANTHROPIC_API_KEY' = 'local-proxy'
    'ANTHROPIC_AUTH_TOKEN' = 'local-proxy'
    'CLAUDE_CODE_SKIP_AUTH_LOGIN' = '1'
}

foreach ($Entry in $ForcedEnv.GetEnumerator()) {
    Set-Item -Path ("Env:{0}" -f $Entry.Key) -Value $Entry.Value
}

foreach ($Name in $ObservedVars) {
    Write-WrapperLog ("env.after.{0}={1}" -f $Name, (Format-EnvValue -Name $Name))
}

Write-WrapperLog 'Launching wrapped Claude process.'

try {
    & $Target @RemainingArgs
    $ExitCode = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
    Write-WrapperLog "wrapped_exit_code=$ExitCode"
    exit $ExitCode
} catch {
    Write-WrapperLog ("wrapped_exception={0}" -f $_.Exception.Message)
    throw
}

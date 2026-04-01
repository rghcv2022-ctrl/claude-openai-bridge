$ErrorActionPreference = 'Stop'

$TaskName = 'ClaudeOpenAIProxy'
$ScriptPath = Join-Path $PSScriptRoot 'start-proxy.ps1'
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`""
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType Interactive -RunLevel Limited

try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Principal $Principal -Force | Out-Null
} catch {
    if ($_.FullyQualifiedErrorId -like '*0x80070005*') {
        throw "Windows blocked scheduled task creation for '$TaskName'. Run this script in a PowerShell session that can create Task Scheduler entries for $CurrentUser."
    }
    throw
}

Write-Host "Installed task: $TaskName"

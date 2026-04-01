$ErrorActionPreference = 'Stop'

$TaskName = 'ClaudeOpenAIProxy'
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Removed task: $TaskName"

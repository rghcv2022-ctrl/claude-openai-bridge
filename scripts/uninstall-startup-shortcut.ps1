$ErrorActionPreference = 'Stop'

$StartupDir = [Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupDir 'Claude OpenAI Proxy.lnk'

if (Test-Path $ShortcutPath) {
    Remove-Item -LiteralPath $ShortcutPath -Force
    Write-Host "Removed Startup shortcut: $ShortcutPath"
    exit 0
}

Write-Host "Startup shortcut not found: $ShortcutPath"

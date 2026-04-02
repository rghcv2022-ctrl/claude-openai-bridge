$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$StartupDir = [Environment]::GetFolderPath('Startup')
$ShortcutPath = Join-Path $StartupDir 'Claude OpenAI Proxy.lnk'
$LauncherPath = Join-Path $PSScriptRoot 'start-proxy-hidden.vbs'
$WScriptPath = Join-Path $env:SystemRoot 'System32\wscript.exe'

if (-not (Test-Path $LauncherPath)) {
    throw "Launcher script not found: $LauncherPath"
}

if (-not (Test-Path $StartupDir)) {
    New-Item -ItemType Directory -Force -Path $StartupDir | Out-Null
}

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $WScriptPath
$Shortcut.Arguments = "`"$LauncherPath`""
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = 'Starts the Claude OpenAI proxy at Windows sign-in.'
$Shortcut.IconLocation = "$WScriptPath,0"
$Shortcut.Save()

Write-Host "Installed Startup shortcut: $ShortcutPath"

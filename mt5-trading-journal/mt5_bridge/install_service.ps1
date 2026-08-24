<#
.SYNOPSIS
    Registers the MT5 Bridge as a Windows Task Scheduler task so it
    starts automatically at login (or at system boot if run as SYSTEM).

.DESCRIPTION
    Run this once from an elevated PowerShell prompt:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
        .\install_service.ps1

    To remove the task later:
        Unregister-ScheduledTask -TaskName "MT5JournalBridge" -Confirm:$false

.NOTES
    Requires Python to be on PATH (python.exe accessible from the terminal).
    The bridge logs to bridge.log in this directory.
#>

param(
    [string]$TaskName   = "MT5JournalBridge",
    [string]$PythonExe  = "python",          # or full path: "C:\Python311\python.exe"
    [string]$ScriptDir  = $PSScriptRoot
)

$ScriptPath = Join-Path $ScriptDir "bridge.py"

if (-not (Test-Path $ScriptPath)) {
    Write-Error "bridge.py not found at $ScriptPath"
    exit 1
}

# ── Build the action ──────────────────────────────────────────────────────────
$Action = New-ScheduledTaskAction `
    -Execute  $PythonExe `
    -Argument "`"$ScriptPath`"" `
    -WorkingDirectory $ScriptDir

# ── Trigger: at logon of the current user ────────────────────────────────────
$Trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# ── Settings ─────────────────────────────────────────────────────────────────
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit      (New-TimeSpan -Days 365) `
    -RestartCount            10 `
    -RestartInterval         (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable      $true `
    -RunOnlyIfNetworkAvailable $false

# ── Principal: run as current user, highest privilege available ───────────────
$Principal = New-ScheduledTaskPrincipal `
    -UserId    $env:USERNAME `
    -LogonType Interactive `
    -RunLevel  Highest

# ── Register ──────────────────────────────────────────────────────────────────
$Existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Host "Task '$TaskName' already exists — updating…"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName   $TaskName `
    -Action     $Action `
    -Trigger    $Trigger `
    -Settings   $Settings `
    -Principal  $Principal `
    -Description "MT5 Journal Bridge — records trades from MetaTrader 5"

Write-Host ""
Write-Host "✓ Task '$TaskName' registered." -ForegroundColor Green
Write-Host "  It will start automatically the next time you log in."
Write-Host ""
Write-Host "  Start it right now:"
Write-Host "    Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "  Check its status:"
Write-Host "    Get-ScheduledTask -TaskName '$TaskName' | Select-Object State"
Write-Host ""
Write-Host "  View logs:"
Write-Host "    Get-Content '$ScriptDir\bridge.log' -Wait"

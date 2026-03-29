# ============================================================
# Gmail Triage Agent - Windows Task Scheduler Setup
# Run this script ONCE to schedule the agent to run every hour.
# ============================================================

$ErrorActionPreference = "Stop"

# --- Configuration ---
$TaskName = "GmailTriageAgent"
$BackupTaskName = "GmailTriageBackup"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$PythonPath = (py -3.12 -c "import sys; print(sys.executable)") 
$ScriptPath = Join-Path $ProjectDir "main.py"
$BackupScript = Join-Path $ProjectDir "backup.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Gmail Triage Agent - Scheduler Setup"   -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Python:  $PythonPath"
Write-Host "Script:  $ScriptPath"
Write-Host "Backup:  $BackupScript"
Write-Host "Project: $ProjectDir"
Write-Host ""

# --- Remove existing tasks if present ---
foreach ($tn in @($TaskName, $BackupTaskName)) {
    $existingTask = Get-ScheduledTask -TaskName $tn -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Removing existing scheduled task '$tn'..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $tn -Confirm:$false
    }
}

# --- Task 1: Main Triage (Every 60 minutes) ---
$Action1 = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`" run" -WorkingDirectory $ProjectDir
$Trigger1 = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 60)
$Settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 45) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $Action1 -Trigger $Trigger1 -Settings $Settings1 -Description "Categorizes Gmail emails using Gemini AI every hour." -RunLevel Limited

# --- Task 2: Weekly Backup (Every Sunday at 3 AM) ---
$Action2 = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$BackupScript`"" -WorkingDirectory $ProjectDir
$Trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "3:00AM"
$Settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $BackupTaskName -Action $Action2 -Trigger $Trigger2 -Settings $Settings2 -Description "Backs up the Gmail Triage database weekly." -RunLevel Limited

Write-Host ""
Write-Host "Tasks registered successfully!" -ForegroundColor Green
Write-Host "  1. $TaskName (Hourly)" -ForegroundColor Green
Write-Host "  2. $BackupTaskName (Weekly Sundays)" -ForegroundColor Green
Write-Host ""
Write-Host "You can manage them in Task Scheduler (taskschd.msc)." -ForegroundColor Gray
Write-Host ""

# ============================================================
# Gmail Triage Agent - SQLite Database Backup
# Runs weekly automatically if configured.
# ============================================================

$ErrorActionPreference = "Stop"

# --- Configuration ---
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$DbPath = Join-Path $ProjectDir "app_data.db"
$BackupDir = Join-Path $ProjectDir "backups"

# Create backup directory if not exists
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
    Write-Host "Created backup directory at $BackupDir" -ForegroundColor Cyan
}

if (-not (Test-Path $DbPath)) {
    Write-Host "No database found at $DbPath to backup." -ForegroundColor Red
    exit
}

# Generate timestamped filename
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$BackupFile = Join-Path $BackupDir "app_data_$Timestamp.db"

Write-Host "Backing up database..." -ForegroundColor Cyan
Copy-Item -Path $DbPath -Destination $BackupFile
Write-Host "Backup created: $BackupFile" -ForegroundColor Green

# --- Retention Policy: Keep only the 7 most recent backups ---
$OldBackups = Get-ChildItem -Path $BackupDir -File | Sort-Object LastWriteTime -Descending | Select-Object -Skip 7
if ($OldBackups) {
    Write-Host "Cleaning up old backups..." -ForegroundColor Yellow
    $OldBackups | Remove-Item -Force
}

Write-Host "Backup complete!" -ForegroundColor Green

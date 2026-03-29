#!/bin/bash
# ============================================================
# Gmail Triage Agent - SQLite Database Backup
# Runs automatically in cloud environment (e.g., cron or simple loop wrapper)
# ============================================================

set -euo pipefail

# --- Configuration ---
# Use the DB_PATH environment variable if available, otherwise default to Docker image's path
DB_PATH="${DB_PATH:-/app/app_data.db}"
# Create a backups directory right relative to db's parent directory
BACKUP_DIR="${BACKUP_DIR:-$(dirname "$DB_PATH")/backups}"

# Ensure backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "[INFO] Created backup directory at $BACKUP_DIR"
    mkdir -p "$BACKUP_DIR"
fi

# Verify the database file exists before backup
if [ ! -f "$DB_PATH" ]; then
    echo "[ERROR] No database found at $DB_PATH to backup."
    exit 1
fi

# --- Execution ---
# Generate timestamped filename
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
BACKUP_FILE="${BACKUP_DIR}/app_data_${TIMESTAMP}.db.gz"

echo "[INFO] Backing up and compressing database from $DB_PATH ..."
# Uses gzip to compress the database during backup
# Using sqlite3 .backup might be preferred if sqlite3 is installed, but since we're in a python-slim container, gzip is a safer bet or we just gzip the cp.
gzip -c "$DB_PATH" > "$BACKUP_FILE"
echo "[INFO] Backup created: $BACKUP_FILE"

# --- Retention Policy: Keep only the 7 most recent backups ---
echo "[INFO] Cleaning up old backups (retention cap: 7) ..."
cd "$BACKUP_DIR"

# Count total backups
BACKUP_COUNT=$(ls -1q app_data_*.db.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 7 ]; then
    TO_DELETE=$((BACKUP_COUNT - 7))
    # List by oldest first, take the top $TO_DELETE files, and remove them
    ls -tr app_data_*.db.gz | head -n "$TO_DELETE" | xargs rm -f
    echo "[INFO] Removed $TO_DELETE older backup(s)."
else
    echo "[INFO] $BACKUP_COUNT backup(s) exist; no cleanup needed."
fi

echo "[INFO] Backup process complete!"

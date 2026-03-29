"""
Gmail Triage Agent - Main Orchestrator
======================================
Runs the full pipeline: Ingest unread emails -> Process with Gemini -> Apply labels.
Enforces single-instance execution via a lock file to prevent scheduler overlap.
"""
import os
import sys
import time
import logging
import argparse
import warnings
import subprocess
from pathlib import Path
from datetime import datetime

# Suppress library deprecation warnings for a cleaner CLI experience
warnings.filterwarnings("ignore", category=FutureWarning)

# Force pure-python protobuf for Python 3.14 compatibility (safety net)
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# Project root
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.ingestor import fetch_and_queue_emails
from src.worker import process_queue
from src.db import get_connection, replay_dead_letters, count_by_status, init_db
from src.digest import generate_weekly_report

# Lock file path
LOCK_FILE = BASE_DIR / ".agent.lock"

# Logging setup
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

def setup_logging():
    """Configure rotating log output to both console and file."""
    log_file = LOG_DIR / f"agent_{datetime.now().strftime('%Y-%m-%d')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("main")

def acquire_lock():
    if LOCK_FILE.exists():
        try:
            old_pid = int(LOCK_FILE.read_text().strip())
            import psutil
            if psutil.pid_exists(old_pid):
                return False
        except (ValueError, ImportError):
            lock_age_minutes = (time.time() - LOCK_FILE.stat().st_mtime) / 60
            if lock_age_minutes < 45:
                return False
        LOCK_FILE.unlink(missing_ok=True)
    
    LOCK_FILE.write_text(str(os.getpid()))
    return True

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)

def main():
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("Gmail Triage Agent - Starting Run")
    logger.info("=" * 60)
    
    if not acquire_lock():
        logger.warning("Another instance of the agent is already running. Exiting.")
        sys.exit(0)
    
    try:
        logger.info("[Phase 1/2] Running Ingestor...")
        start = time.time()
        fetch_and_queue_emails()
        logger.info(f"[Phase 1/2] Ingestion completed in {time.time() - start:.1f}s")
        
        logger.info("[Phase 2/2] Running Worker...")
        start = time.time()
        process_queue()
        logger.info(f"[Phase 2/2] Processing completed in {time.time() - start:.1f}s")
        
        logger.info("Run completed successfully.")
        
    except Exception as e:
        logger.critical(f"Agent crashed with unhandled exception: {e}", exc_info=True)
    finally:
        release_lock()
        logger.info("Lock released. Agent shutting down.\n")

def cmd_replay():
    logger = setup_logging()
    logger.info("Replaying dead-letter emails...")
    init_db()
    with get_connection() as conn:
        count = replay_dead_letters(conn)
    print(f"\n✅ Replayed {count} dead-letter emails back to pending.")
    print("Run 'py -3.12 main.py' to process them.")

def cmd_status():
    init_db()
    with get_connection() as conn:
        stats = count_by_status(conn)
    
    print("\n" + "=" * 40)
    print(" Gmail Triage Agent - Queue Health")
    print("=" * 40)
    total = sum(stats.values())
    for status, count in sorted(stats.items()):
        bar = "█" * min(count, 30)
        print(f"  {status:15s} : {count:4d}  {bar}")
    print(f"  {'TOTAL':15s} : {total:4d}")
    print("=" * 40 + "\n")

def cmd_digest():
    """Generate and display the weekly digest."""
    init_db()
    print(generate_weekly_report())

def cmd_backup():
    """Trigger the backup script based on the current OS."""
    print("\nTriggering database backup...")
    
    if sys.platform == "win32":
        backup_script = BASE_DIR / "scripts" / "backup.ps1"
        try:
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(backup_script)], check=True)
        except Exception as e:
            print(f"❌ Backup failed: {e}")
    else:
        backup_script = BASE_DIR / "scripts" / "backup.sh"
        try:
            # Ensure the script is executable
            subprocess.run(["chmod", "+x", str(backup_script)], check=True)
            subprocess.run(["/bin/bash", str(backup_script)], check=True)
        except Exception as e:
            print(f"❌ Backup failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gmail Triage Agent")
    parser.add_argument("command", nargs="?", default="run",
                       choices=["run", "replay", "status", "digest", "backup"],
                       help="run=normal cycle, replay=requeue dead letters, status=show queue health, digest=weekly report, backup=manual backup")
    args = parser.parse_args()
    
    if args.command == "run":
        main()
    elif args.command == "replay":
        cmd_replay()
    elif args.command == "status":
        cmd_status()
    elif args.command == "digest":
        cmd_digest()
    elif args.command == "backup":
        cmd_backup()

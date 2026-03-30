import sqlite3
import os
from datetime import datetime, timedelta

def run_health_check():
    db_path = os.environ.get('DB_PATH', 'app_data.db')
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Define the 24-hour window
        limit = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')

        # Count successes
        cursor.execute("SELECT COUNT(*) FROM processed_emails WHERE status='completed' AND processed_at > ?", (limit,))
        completed = cursor.fetchone()[0]

        # Count failures
        cursor.execute("SELECT COUNT(*) FROM processed_emails WHERE status='failed' AND processed_at > ?", (limit,))
        failed = cursor.fetchone()[0]

        # Count pending/queued
        cursor.execute("SELECT COUNT(*) FROM processed_emails WHERE status='queued'")
        pending = cursor.fetchone()[0]

        status = "NOMINAL" if failed == 0 else "ATTENTION REQUIRED"
        
        print(f"[{status}] Last 24h: {completed} processed, {failed} failed. Queue: {pending} pending.")

        conn.close()
    except Exception as e:
        print(f"[ERROR] Health check failed: {e}")

if __name__ == "__main__":
    run_health_check()

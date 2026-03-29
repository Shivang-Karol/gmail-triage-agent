import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import logging

# Ensure logs are visible for DB operations
logger = logging.getLogger(__name__)

# Constants for DB connection string
DB_PATH = Path(os.environ.get("DB_PATH", Path(__file__).parent.parent / "app_data.db"))
SCHEMA_PATH = Path(__file__).parent.parent / "schema.sql"

def get_connection():
    """Provides a sterile, independent connection for thread safety."""
    conn = sqlite3.connect(
        DB_PATH,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        isolation_level=None  # We manually manage transactions for queue operations
    )
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize schema on first run"""
    if not SCHEMA_PATH.exists():
        logger.error(f"Cannot find {SCHEMA_PATH}")
        raise FileNotFoundError(f"Missing schema file at {SCHEMA_PATH}")

    with get_connection() as conn:
        with open(SCHEMA_PATH, "r") as f:
            script = f.read()
        conn.executescript(script)
        logger.info("Database schema validated.")

def upsert_email(conn, message_id, thread_id, received_at):
    """
    Idempotent enqueue: If you try to add an email twice (e.g., overlapping runs
    or network failure), SQLite will simply ignore the insert due to the UNIQUE constraint.
    """
    try:
        conn.execute("BEGIN TRANSACTION")
        conn.execute("""
            INSERT INTO emails (message_id, thread_id, received_at, status)
            VALUES (?, ?, ?, 'pending')
            ON CONFLICT(message_id) DO NOTHING;
        """, (message_id, thread_id, received_at))
        conn.execute("COMMIT TRANSACTION")
        return True
    except Exception as e:
        conn.execute("ROLLBACK TRANSACTION")
        logger.error(f"Failed to upsert message {message_id}: {e}")
        return False

def claim_batch(conn, limit=20, lease_duration_minutes=5):
    """
    The atomic leasing contract. Safely grabs a batch of emails.
    """
    lease_owner = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=lease_duration_minutes)

    try:
        conn.execute("BEGIN TRANSACTION")

        # Select emails that are:
        # 1. Pending
        # 2. Or leased but the lease expired (crash recovery)
        # 3. Or failed but they are due for their next attempt based on backoff
        conn.execute("""
            UPDATE emails 
            SET lease_owner = ?, lease_expires_at = ?, status = 'leased', updated_at = CURRENT_TIMESTAMP
            WHERE message_id IN (
                SELECT message_id FROM emails 
                WHERE (status = 'pending') 
                   OR (status = 'leased' AND lease_expires_at < CURRENT_TIMESTAMP)
                   OR (status = 'failed' AND next_attempt_at <= CURRENT_TIMESTAMP)
                LIMIT ?
            )
        """, (lease_owner, expires_at, limit))
        
        # Fetch the ones we just successfully locked
        cursor = conn.execute("SELECT * FROM emails WHERE lease_owner = ?", (lease_owner,))
        batch = cursor.fetchall()
        
        conn.execute("COMMIT TRANSACTION")
        return [dict(r) for r in batch]
    except Exception as e:
        conn.execute("ROLLBACK TRANSACTION")
        logger.error(f"Failed to claim batch: {e}")
        return []

def mark_completed(conn, message_id, classification_json, model_name, latency_ms):
    """Idempotently finalizes a successful ML classification run."""
    conn.execute("""
        UPDATE emails
        SET status = 'completed', 
            classification_json = ?, 
            model_name = ?, 
            model_latency_ms = ?,
            lease_owner = NULL,
            lease_expires_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE message_id = ?
    """, (classification_json, model_name, latency_ms, message_id))

def mark_failed(conn, message_id, error_msg, attempt_count, max_retries=5):
    """
    Handles transient vs permanent failures via Dead Letter isolation.
    Uses exponential backoff for the next_attempt_at.
    """
    if attempt_count >= max_retries:
        next_status = 'dead_letter'
        next_attempt = None
        logger.error(f"Message {message_id} reached max retries. Moving to dead_letter.")
    else:
        next_status = 'failed'
        # Exponential backoff (minutes): 1, 2, 4, 8, 16
        backoff_minutes = 2 ** attempt_count
        next_attempt = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
        logger.warning(f"Message {message_id} temporarily failed. Scheduling retry {attempt_count+1} in {backoff_minutes} mins.")

    conn.execute("""
        UPDATE emails
        SET status = ?, 
            last_error = ?,
            attempt_count = attempt_count + 1,
            next_attempt_at = ?,
            lease_owner = NULL,
            lease_expires_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE message_id = ?
    """, (next_status, error_msg, next_attempt, message_id))

# =============================================
# COST GUARDRAILS
# =============================================

def increment_daily_calls(conn):
    """Increment the daily API call counter. Returns the new count."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    conn.execute("""
        INSERT INTO api_usage (date, call_count, updated_at) 
        VALUES (?, 1, CURRENT_TIMESTAMP)
        ON CONFLICT(date) DO UPDATE SET 
            call_count = call_count + 1,
            updated_at = CURRENT_TIMESTAMP
    """, (today,))
    cursor = conn.execute("SELECT call_count FROM api_usage WHERE date = ?", (today,))
    row = cursor.fetchone()
    return row['call_count'] if row else 0

def get_daily_call_count(conn):
    """Check how many Gemini calls have been made today."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    cursor = conn.execute("SELECT call_count FROM api_usage WHERE date = ?", (today,))
    row = cursor.fetchone()
    return row['call_count'] if row else 0

# =============================================
# SYNC CHECKPOINT (Reconciliation)
# =============================================

def save_checkpoint(conn, key, value):
    """Persist a sync marker (e.g., last Gmail historyId or timestamp)."""
    conn.execute("""
        INSERT INTO sync_state (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET 
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
    """, (key, str(value)))

def load_checkpoint(conn, key):
    """Load a previously saved sync marker."""
    cursor = conn.execute("SELECT value FROM sync_state WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row['value'] if row else None

# =============================================
# DEAD-LETTER REPLAY
# =============================================

def replay_dead_letters(conn, limit=10):
    """
    Requeue dead-letter emails back to 'pending' for re-processing.
    Resets attempt_count so they get a fresh set of retries.
    Returns the number of emails replayed.
    """
    cursor = conn.execute("""
        UPDATE emails
        SET status = 'pending',
            attempt_count = 0,
            lease_owner = NULL,
            lease_expires_at = NULL,
            next_attempt_at = NULL,
            last_error = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE status = 'dead_letter' OR status = 'failed'
    """)
    count = cursor.rowcount
    logger.info(f"Replayed {count} dead-letter emails back to pending.")
    return count

def count_by_status(conn):
    """Returns a dict of status -> count for the health dashboard."""
    cursor = conn.execute("SELECT status, COUNT(*) as cnt FROM emails GROUP BY status")
    return {row['status']: row['cnt'] for row in cursor.fetchall()}

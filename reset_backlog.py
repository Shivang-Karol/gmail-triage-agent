import sqlite3

try:
    conn = sqlite3.connect('app_data.db')
    c = conn.cursor()
    
    # 1. Skip all existing pending/failed emails
    c.execute("UPDATE emails SET status = 'skipped' WHERE status IN ('pending', 'failed')")
    count = c.rowcount
    
    # 2. Reset the Checkpoint to Today
    c.execute("""
        INSERT INTO sync_state (key, value) 
        VALUES ('last_ingest_timestamp', '2026/03/29')
        ON CONFLICT(key) DO UPDATE SET value = '2026/03/29'
    """)
    
    conn.commit()
    print(f"✅ Successfully skipped {count} emails.")
    print("🚀 Fresh start: The agent will now only process emails arriving AFTER today.")
    
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    conn.close()

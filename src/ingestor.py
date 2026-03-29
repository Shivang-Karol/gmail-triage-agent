import logging
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from src.gmail_client import get_gmail_service
from src.db import init_db, upsert_email, get_connection, save_checkpoint, load_checkpoint

logger = logging.getLogger(__name__)

# Load configs
BASE_DIR = Path(__file__).resolve().parent.parent
from src.config_loader import get_config

def get_excluded_domains():
    """Reads the privacy rules from the config file."""
    config = get_config()
    return config.get('privacy_rules', {}).get('exclude_sender_domains', [])

def extract_domain(email_address):
    """Safely extracts domain from strings like 'John Doe <john@chase.com>'"""
    if '<' in email_address and '>' in email_address:
        email_address = email_address.split('<')[1].split('>')[0]
    if '@' in email_address:
        return email_address.split('@')[1].lower()
    return ""

def fetch_and_queue_emails():
    """
    Poller that pushes unread messages into the queue.
    
    Uses a DUAL strategy to avoid missing emails:
    1. Primary: Fetch all `is:unread` emails (catches new arrivals)
    2. Reconciliation: Also fetch emails `after:checkpoint` regardless of read status
       This catches emails you manually read before the agent got to them.
    """
    logger.info("Starting Ingestion Cycle...")
    
    # Ensure tables exist
    init_db()
    
    service = get_gmail_service()
    excluded_domains = get_excluded_domains()
    
    # Load the last checkpoint timestamp
    with get_connection() as conn:
        last_checkpoint = load_checkpoint(conn, 'last_ingest_timestamp')
    
    # 1. Start with the "from now on" filter
    base_filter = f"after:{last_checkpoint}" if last_checkpoint else ""
    
    # 2. Build strict queries that respect your clean slate
    queries = [f"is:unread {base_filter}".strip()]
    if base_filter:
        queries.append(base_filter) # Catch arrivals since last run (even if read)
        
    all_message_ids = set()
    all_messages = []
    
    with get_connection() as conn:
        service = get_gmail_service()
        excluded_domains = get_excluded_domains()
        
        for query in queries:
            try:
                results = service.users().messages().list(userId='me', q=query).execute()
                messages = results.get('messages', [])
                for msg in messages:
                    if msg['id'] not in all_message_ids:
                        all_message_ids.add(msg['id'])
                        all_messages.append(msg)
            except Exception as e:
                logger.error(f"Failed to query Gmail with '{query}': {e}")
        
        if not all_messages:
            logger.info("Inbox is clean. No new messages found since checkpoint.")
            save_checkpoint(conn, 'last_ingest_timestamp', 
                          datetime.now().strftime('%Y/%m/%d'))
            return

        logger.info(f"Found {len(all_messages)} candidate messages. Evaluating for queue injection...")
        
        queued_count = 0
        skipped_count = 0
        
        for msg in all_messages:
            msg_id = msg['id']
            thread_id = msg['threadId']
            
            # Fetch minimally required headers (Sender, Date)
            try:
                msg_details = service.users().messages().get(
                    userId='me', id=msg_id, format='metadata', 
                    metadataHeaders=['From', 'Date']
                ).execute()
            except Exception as e:
                logger.error(f"Failed to fetch metadata for {msg_id}: {e}")
                continue

            headers = msg_details.get('payload', {}).get('headers', [])
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "")
            
            # Privacy Check: Exclude hardcoded banks, family, etc.
            sender_domain = extract_domain(sender)
            if sender_domain in excluded_domains:
                logger.debug(f"[Privacy Filter] Ignoring email from excluded domain: {sender_domain}")
                skipped_count += 1
                continue
            
            # Idempotent upsert — SQLite silently ignores duplicates
            received_at_timestamp = int(msg_details.get('internalDate', 0)) / 1000.0
            dt_received = datetime.fromtimestamp(received_at_timestamp)

            if upsert_email(conn, msg_id, thread_id, dt_received):
                queued_count += 1
        
        # Save checkpoint for reconciliation on next run
        save_checkpoint(conn, 'last_ingest_timestamp', 
                       datetime.now().strftime('%Y/%m/%d'))
                
    logger.info(f"Ingestion complete. Queued: {queued_count}, Skipped (Privacy): {skipped_count}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    fetch_and_queue_emails()

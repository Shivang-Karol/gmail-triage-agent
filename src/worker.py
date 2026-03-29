import logging
import time
import json
from src.db import (get_connection, claim_batch, mark_completed, mark_failed,
                    increment_daily_calls, get_daily_call_count)
from src.gmail_client import get_gmail_service, setup_labels, fetch_message_body, apply_label
from src.gemini_brain import initialize_model, classify_email_text, get_config
from src.policy import PrivacyPolicy, FallbackClassifier
from src.notifier import notify_if_urgent
from src.link_follower import enrich_email_with_links

logger = logging.getLogger(__name__)

def process_queue():
    config = get_config()
    batch_size = config.get('scheduler', {}).get('batch_size', 20)
    lease_duration = config.get('queue_management', {}).get('lease_duration_minutes', 5)
    daily_cap = config.get('model_settings', {}).get('daily_call_cap', 300)
    
    service = get_gmail_service()
    categories = config.get("categories", ["UNCATEGORIZED"])
    label_map = setup_labels(service, categories + ["REVIEW_NEEDED"])

    gemini_available = True
    model = None
    model_name = "fallback_rules"
    try:
        model, model_name = initialize_model()
    except Exception as e:
        logger.warning(f"Gemini initialization failed: {e}")
        gemini_available = False

    with get_connection() as conn:
        current_calls = get_daily_call_count(conn)
        if current_calls >= daily_cap:
            gemini_available = False
        
        batch = claim_batch(conn, limit=batch_size, lease_duration_minutes=lease_duration)
        if not batch:
            return

        for email_record in batch:
            msg_id = email_record['message_id']
            attempt_count = email_record['attempt_count']
            
            # --- Initialize loop-scope variables to avoid UnboundLocalError ---
            ml_result = {"category": "UNCATEGORIZED", "confidence": 0.0}
            used_model = "none"
            latency = 0
            target_label_id = None
            category = "UNCATEGORIZED"
            confidence = 0.0
            
            try:
                body_text = fetch_message_body(service, msg_id)
                if not body_text:
                    mark_completed(conn, msg_id, json.dumps(ml_result), "none", 0)
                    continue

                privacy_rules = config.get('privacy_rules', {})
                body_text = PrivacyPolicy.apply_redaction(body_text, privacy_rules)
                body_text = enrich_email_with_links(body_text, max_links=3)

                max_tokens = config.get('model_settings', {}).get('max_tokens_per_email', 1500)
                char_limit = max_tokens * 4
                if len(body_text) > char_limit:
                    logger.info(f"Truncated {msg_id}: {len(body_text)} → {char_limit} chars")
                body_text = body_text[:char_limit]

                start_time = time.time()
                
                # Check daily cap again
                is_actually_available = gemini_available and (get_daily_call_count(conn) < daily_cap)
                
                if is_actually_available and model:
                    try:
                        ml_result = classify_email_text(model, body_text)
                        increment_daily_calls(conn)
                        used_model = model_name
                    except Exception as gemini_err:
                        logger.warning(f"Gemini error on {msg_id}: {gemini_err}. Falling back to keywords.")
                        ml_result = FallbackClassifier.classify(body_text)
                        used_model = "fallback_rules"
                else:
                    logger.info(f"Using fallback keywords for {msg_id} (Gemini unavailable)")
                    ml_result = FallbackClassifier.classify(body_text)
                    used_model = "fallback_rules"
                
                latency = int((time.time() - start_time) * 1000)
                category = ml_result.get('category', 'UNCATEGORIZED')
                confidence = ml_result.get('confidence', 0.0)

                # Determine Label
                threshold = config.get('model_settings', {}).get('confidence_auto_label_threshold', 0.80)
                if confidence >= threshold:
                    target_label_id = label_map.get(category)
                elif confidence >= 0.50:
                    target_label_id = label_map.get("REVIEW_NEEDED")

                if target_label_id:
                    apply_label(service, msg_id, target_label_id)
                    logger.info(f"Labeled {msg_id} as {category}")

                notify_if_urgent(ml_result)
                mark_completed(conn, msg_id, json.dumps(ml_result), used_model, latency)
                
                # Rate limit sleep (ONLY if we actually used AI)
                if used_model != "fallback_rules" and used_model != "none":
                    time.sleep(12)

            except Exception as e:
                logger.error(f"Failed processing {msg_id}: {e}")
                mark_failed(conn, msg_id, str(e), attempt_count)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    process_queue()

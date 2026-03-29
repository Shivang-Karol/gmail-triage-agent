"""
Link Follower - Extracts and fetches URLs from email bodies.
Provides additional context to Gemini for emails that are just "Click here to apply".
"""
import re
import logging
from urllib.parse import urlparse
import requests

logger = logging.getLogger(__name__)

# Domains we should NEVER follow (tracking pixels, unsubscribe, social media)
SKIP_DOMAINS = {
    'google.com', 'facebook.com', 'twitter.com', 'instagram.com',
    'linkedin.com', 'youtube.com', 'bit.ly', 't.co', 'goo.gl',
    'unsubscribe', 'mailchimp.com', 'sendgrid.net', 'list-manage.com',
    'doubleclick.net', 'googleapis.com'
}

# Only follow links that look like they could be job/internship pages
INTERESTING_KEYWORDS = [
    'career', 'job', 'intern', 'apply', 'recruit', 'hiring',
    'position', 'opening', 'opportunity', 'placement', 'register',
    'form', 'portal', 'admission'
]

URL_REGEX = re.compile(
    r'https?://[^\s<>"\')\]]+',
    re.IGNORECASE
)

def extract_urls(text: str) -> list:
    """Pull all HTTP(S) URLs from raw email text."""
    if not text:
        return []
    return URL_REGEX.findall(text)

def is_worth_following(url: str) -> bool:
    """
    Quick heuristic: skip tracking pixels, social media, and unsubscribe links.
    Prioritize URLs with career/job-related path segments.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        
        # Skip known junk domains
        for skip in SKIP_DOMAINS:
            if skip in domain:
                return False
        
        # Skip image/tracking URLs
        if any(path.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.svg', '.css', '.js']):
            return False
            
        # Bonus: prioritize if the URL path contains interesting keywords
        # But don't require it — unknown URLs could still be important
        return True
    except Exception:
        return False

def fetch_page_text(url: str, timeout: int = 5, max_chars: int = 2000) -> str:
    """
    Fetches a URL and extracts readable text from the page.
    Returns a truncated plain-text summary.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            return ""
        
        # Strip HTML tags crudely (we don't need beautifulsoup for this)
        text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:max_chars]
    except Exception as e:
        logger.debug(f"Could not fetch {url}: {e}")
        return ""

def enrich_email_with_links(email_text: str, max_links: int = 3) -> str:
    """
    Main entry point. Takes raw email text, finds interesting URLs,
    fetches their content, and appends a summary to the original text.
    
    This gives Gemini the full picture even when the email body is just
    "Hi, apply here: [link]".
    """
    urls = extract_urls(email_text)
    worthy_urls = [u for u in urls if is_worth_following(u)]
    
    if not worthy_urls:
        return email_text
    
    # Only follow the first few to save time and tokens
    worthy_urls = worthy_urls[:max_links]
    
    enrichments = []
    for url in worthy_urls:
        page_text = fetch_page_text(url)
        if page_text and len(page_text) > 50:  # Skip empty/tiny pages
            enrichments.append(f"[LINKED PAGE: {url}]\n{page_text}")
            logger.info(f"Enriched email with content from: {url}")
    
    if enrichments:
        email_text += "\n\n--- LINKED CONTENT (fetched by agent) ---\n"
        email_text += "\n\n".join(enrichments)
    
    return email_text

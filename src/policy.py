import re
import logging

logger = logging.getLogger(__name__)

class PrivacyPolicy:
    """Pre-processes email bodies to destroy sensitive PII prior to ML Inference."""
    
    # Common formats for North American and Indian mobile numbers
    PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    
    # Typical student ID formats (e.g., 9-digit university IDs)
    STUDENT_ID_REGEX = re.compile(r'\b(ID:?\s*)?\d{8,10}\b', re.IGNORECASE)
    
    # Standard SSN or national identifier formats
    SSN_REGEX = re.compile(r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b')
    
    @classmethod
    def apply_redaction(cls, text: str, rules: dict) -> str:
        """
        Takes raw email text and rules from config, returns redacted text.
        """
        if not text:
            return ""
            
        redacted_text = text
        
        redact_patterns = rules.get('redact_patterns', {})
        
        if redact_patterns.get('phone_numbers'):
            count = len(cls.PHONE_REGEX.findall(redacted_text))
            if count > 0:
                redacted_text = cls.PHONE_REGEX.sub('[REDACTED_PHONE]', redacted_text)
                logger.debug(f"Redacted {count} phone numbers.")
                if re.search(r'\b\d{10}\b', redacted_text):
                    logger.warning("⚠ Phone redaction may have missed some digits.")

        if redact_patterns.get('student_ids'):
            count = len(cls.STUDENT_ID_REGEX.findall(redacted_text))
            if count > 0:
                redacted_text = cls.STUDENT_ID_REGEX.sub('[REDACTED_ID]', redacted_text)
                logger.debug(f"Redacted {count} potential Student IDs.")
                
        if redact_patterns.get('ssn'):
            count = len(cls.SSN_REGEX.findall(redacted_text))
            if count > 0:
                redacted_text = cls.SSN_REGEX.sub('[REDACTED_SSN]', redacted_text)
                logger.debug(f"Redacted {count} potential National IDs.")
                
        return redacted_text


class FallbackClassifier:
    """
    Deterministic keyword-based classifier.
    Matches the new 6-category taxonomy.
    """
    RULES = [
        {
            "category": "EXAMS",
            "keywords": ["qualifier", "exam date", "assessment", "test link", "coding round", 
                         "technical round", "hall ticket", "admit card", "registration closes"],
        },
        {
            "category": "NPTEL",
            "keywords": ["nptel", "swayam", "iitm", "assignment unit", "course update"],
        },
        {
            "category": "PLACEMENT_CELL",
            "keywords": ["placement", "tpo", "hiring", "recruitment", "campus drive", 
                         "shortlisted", "offer letter", "interview invitation"],
        },
        {
            "category": "COLLEGE",
            "keywords": ["circular", "university", "hostel", "library", "research project", 
                         "admin", "college notice"],
        },
        {
            "category": "COURSES",
            "keywords": ["certification", "workshop", "learn", "enroll", "masterclass", 
                         "training program"],
        },
        {
            "category": "NEWSLETTER",
            "keywords": ["institute update", "weekly digest", "roundup", "newsletter"],
        },
        {
            "category": "PROMOTION",
            "keywords": ["% off", "discount", "sale", "limited time", "exclusive offer", 
                         "coupon", "shop now"],
        },
        {
            "category": "SOCIAL",
            "keywords": ["linkedin", "github", "skool", "connection request", "follower"],
        },
    ]

    @classmethod
    def classify(cls, text: str) -> dict:
        """Returns a classification dict matching Gemini's schema but with low confidence."""
        text_lower = text.lower()

        for rule in cls.RULES:
            for keyword in rule["keywords"]:
                if keyword in text_lower:
                    return {
                        "category": rule["category"],
                        "confidence": 0.55,  # Flags for REVIEW_NEEDED
                        "reasoning": f"Fallback: matched keyword '{keyword}' (Gemini unavailable)",
                        "summary": f"Keyword-matched as {rule['category']} during model outage"
                    }

        return {
            "category": "UNCATEGORIZED",
            "confidence": 0.30,
            "reasoning": "Fallback: no keywords matched (Gemini unavailable)",
            "summary": "Unclassified during model outage"
        }

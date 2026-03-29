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
    Used when Gemini API is unavailable (outage, rate limit exhaustion, quota exceeded).
    Results are marked with low confidence so they can be re-evaluated later.
    """
    
    RULES = [
        {
            "category": "PLACEMENT",
            "keywords": ["placement", "job offer", "recruitment", "hiring", "we are pleased",
                         "selected", "shortlisted", "offer letter", "campus drive"],
        },
        {
            "category": "INTERNSHIP",
            "keywords": ["internship", "intern", "summer training", "winter training",
                         "stipend", "trainee", "apprentice"],
        },
        {
            "category": "INTERVIEW_SCHEDULE",
            "keywords": ["interview", "aptitude test", "coding round", "assessment",
                         "scheduled for", "appear for", "test link"],
        },
        {
            "category": "DEADLINE_ALERT",
            "keywords": ["deadline", "last date", "expires on", "submit by",
                         "registration closes", "apply before"],
        },
        {
            "category": "REJECTION",
            "keywords": ["regret to inform", "not selected", "unable to proceed",
                         "not shortlisted", "unfortunately"],
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
                        "confidence": 0.55,  # Low confidence — flags for REVIEW_NEEDED
                        "reasoning": f"Fallback: matched keyword '{keyword}' (Gemini unavailable)",
                        "summary": f"Keyword-matched as {rule['category']} during model outage"
                    }
        
        # No keywords matched
        return {
            "category": "OTHER",
            "confidence": 0.30,
            "reasoning": "Fallback: no keywords matched (Gemini unavailable)",
            "summary": "Unclassified during model outage"
        }

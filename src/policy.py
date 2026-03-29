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

    IMPORTANT: Category names MUST match the official 12-category taxonomy
    defined in config/agent_config.yaml. Do NOT invent new names here.
    """

    # Ordered by the same precedence as the Gemini prompt (high → low priority)
    RULES = [
        {
            "category": "OFFER_LETTER",
            "keywords": ["offer letter", "we are pleased to offer", "compensation package",
                         "onboarding", "joining date", "welcome aboard"],
        },
        {
            "category": "INTERVIEW_CONFIRMATION",
            "keywords": ["interview scheduled", "interview invitation", "zoom meeting",
                         "google meet", "appear for interview", "interview link",
                         "calendar invite"],
        },
        {
            "category": "ASSESSMENT_NOTIFICATION",
            "keywords": ["coding assessment", "online test", "hackerrank", "leetcode",
                         "aptitude test", "test link", "coding round", "technical round"],
        },
        {
            "category": "CAREER_OPPORTUNITY",
            "keywords": ["job opening", "hiring", "recruitment", "we are looking for",
                         "internship", "intern", "placement", "campus drive",
                         "shortlisted", "referral", "stipend", "apply now"],
        },
        {
            "category": "REJECTION",
            "keywords": ["regret to inform", "not selected", "unable to proceed",
                         "not shortlisted", "unfortunately", "we will not be moving forward"],
        },
        {
            "category": "ACADEMIC_ALERTS",
            "keywords": ["nptel", "exam date", "college circular", "deadline",
                         "last date", "registration closes", "submit by",
                         "classroom", "assignment due"],
        },
        {
            "category": "FINANCIAL_ALERTS",
            "keywords": ["transaction", "payment", "bank alert", "credited",
                         "debited", "upi", "account statement"],
        },
        {
            "category": "SOCIAL_NOTIFICATIONS",
            "keywords": ["linkedin", "github", "skool", "someone viewed your profile",
                         "new follower", "mentioned you", "pull request"],
        },
        {
            "category": "NEWSLETTER",
            "keywords": ["newsletter", "weekly digest", "roundup", "substack",
                         "unsubscribe", "blog post"],
        },
        {
            "category": "PROMOTION",
            "keywords": ["% off", "limited time", "discount", "sale", "shop now",
                         "exclusive offer", "coupon", "promo code"],
        },
        {
            "category": "SPAM",
            "keywords": ["win a prize", "click here to claim", "nigerian prince",
                         "act now", "you have been selected to receive"],
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

        # No keywords matched — use official fallback label
        return {
            "category": "UNCATEGORIZED",
            "confidence": 0.30,
            "reasoning": "Fallback: no keywords matched (Gemini unavailable)",
            "summary": "Unclassified during model outage"
        }

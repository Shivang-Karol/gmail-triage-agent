import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.gemini_brain import initialize_model, classify_email_text
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_precedence():
    client, model_name = initialize_model()
    
    test_cases = [
        {
            "name": "Mixed Signal: Career in Newsletter",
            "text": "Weekly Student Roundup: We have an exciting Internship Opening at Google! Check it out below along with some other news.",
            "expected": "CAREER_OPPORTUNITY"
        },
        {
            "name": "Mixed Signal: Interview in Social",
            "text": "LinkedIn: Shivang, someone viewed your profile. Also, you have an Interview Scheduled for tomorrow at 10am on Zoom.",
            "expected": "INTERVIEW_CONFIRMATION"
        },
        {
            "name": "Generic Noise",
            "text": "Get 50% off on all items! Limited time offer. Shop now at Amazon.",
            "expected": "PROMOTION"
        },
        {
            "name": "Unknown Content",
            "text": "The quick brown fox jumps over the lazy dog.",
            "expected": "UNCATEGORIZED"
        }
    ]
    
    logger.info(f"Starting Brain Smoke Test using model: {model_name}")
    
    for case in test_cases:
        logger.info(f"Testing: {case['name']}")
        try:
            result = classify_email_text(client, case['text'])
            category = result.get('category')
            
            if category == case['expected']:
                logger.info(f"✅ PASS: Got {category}")
            else:
                logger.warning(f"❌ FAIL: Expected {case['expected']}, but got {category}")
                logger.warning(f"   Reasoning: {result.get('reasoning')}")
        except Exception as e:
            logger.error(f"💥 ERROR during testing: {e}")

if __name__ == "__main__":
    test_precedence()

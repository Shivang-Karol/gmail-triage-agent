"""
Gemini Brain — Migrated to google.genai SDK (replaces deprecated google.generativeai)
Uses Pydantic models for type-safe structured output.
Classifies emails into a strict 12-category closed taxonomy.
"""
import os
import logging
import json
import warnings
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Suppress any remaining deprecation noise
warnings.filterwarnings("ignore", category=FutureWarning)

logger = logging.getLogger(__name__)

# Load config and keys
BASE_DIR = Path(__file__).resolve().parent.parent
from src.config_loader import get_config
load_dotenv(BASE_DIR / ".env")

# =============================================
# Pydantic Schema (replaces the old dict schema)
# =============================================

class EmailClassification(BaseModel):
    """Strict output schema that Gemini must adhere to."""
    category: str = Field(description="The classification label for this email")
    confidence: float = Field(description="Float between 0.0 and 1.0 indicating certainty")
    reasoning: str = Field(description="1 sentence explanation of why this category was chosen")
    summary: str = Field(description="A concise 10-word summary of the email content")

# =============================================
# Client Initialization
# =============================================

_client = None

def get_client():
    """Lazy-initialize the genai Client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        _client = genai.Client(api_key=api_key)
    return _client

def initialize_model():
    """
    Returns a tuple of (client, model_name) for compatibility with the worker.
    The new SDK is stateless — the client handles everything.
    """
    config = get_config()
    categories = config.get("categories", ["UNCATEGORIZED"])
    model_name = config.get("model_settings", {}).get("name", "gemini-2.5-flash")
    client = get_client()
    return client, model_name

def classify_email_text(client, email_body_text):
    """
    Sends the email text to Gemini using the new google.genai SDK.
    Returns a dict matching our classification schema.
    """
    config = get_config()
    model_name = config.get("model_settings", {}).get("name", "gemini-2.5-flash")
    
    system_instruction = (
        "You are a Senior Executive Assistant specializing in Student Career Management. "
        "Your goal is to triage incoming emails with 100% precision.\n\n"
        
        "### PRECEDENCE TABLE (Strict High-to-Low Priority)\n"
        "If an email matches multiple categories, you MUST pick the one highest on this list:\n"
        "1. OFFER_LETTER: Congratulatory hire notices, salary/bonus discussion, onboarding tasks.\n"
        "2. INTERVIEW_CONFIRMATION: Meet/Zoom links, calendar invites, 'Interview Scheduled'.\n"
        "3. ASSESSMENT_NOTIFICATION: Online tests, coding assessments (HackerRank/LeetCode), tech round invites.\n"
        "4. CAREER_OPPORTUNITY: Job/Internship openings, recruitment outreach, referral opportunities.\n"
        "5. REJECTION: Negative decisions regarding applications.\n"
        "6. ACADEMIC_ALERTS: NPTEL updates, college circulars, exam dates, classroom posts.\n"
        "7. FINANCIAL_ALERTS: Bank alerts, transaction receipts, payment notices.\n"
        "8. SOCIAL_NOTIFICATIONS: LinkedIn activity, Skool community posts, GitHub notifications.\n"
        "9. NEWSLETTER: Periodic educational content, blog roundups, substack updates.\n"
        "10. PROMOTION: Brand marketing, discounts, product launches, e-commerce ads.\n"
        "11. SPAM: Phishing, 'Win a Prize', generic marketing noise.\n"
        "12. UNCATEGORIZED: The mandatory fallback if NO other category matches.\n\n"
        
        "### RULES:\n"
        "- CLOSED SET: You MUST classify into one of the 12 categories above. Do NOT invent or suggest new categories under any circumstances.\n"
        "- PRIORITY OVERRIDE: If an email looks like a NEWSLETTER but contains a specific INTERVIEW link, label it INTERVIEW_CONFIRMATION.\n"
        "- NEUTRALITY: Be objective. Do not let promotional tone obscure job-related keywords.\n"
    )
    
    logger.debug("Prompting Gemini API (new SDK)...")
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=email_body_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=EmailClassification,
                temperature=0.1,
                max_output_tokens=256,
            )
        )
        
        # Log token usage from response metadata
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            um = response.usage_metadata
            logger.info(f"Token usage — prompt: {um.prompt_token_count}, "
                        f"output: {um.candidates_token_count}, "
                        f"total: {um.total_token_count}")
        
        # Parse the structured response
        result = json.loads(response.text)
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}")
        raise ValueError("Model failed to adhere to JSON Schema.")
    except Exception as e:
        logger.error(f"API Error during Gemini classification: {e}")
        raise

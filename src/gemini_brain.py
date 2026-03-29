"""
Gemini Brain — Migrated to google.genai SDK (replaces deprecated google.generativeai)
Uses Pydantic models for type-safe structured output.
Supports dynamic label creation when Gemini encounters new significant categories.
"""
import os
import logging
import json
import yaml
import warnings
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
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
    suggested_new_label: Optional[str] = Field(
        default=None,
        description="If the email doesn't fit any existing category well, suggest a new label name. Otherwise null."
    )

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
    categories = config.get("categories", ["OTHER"])
    
    system_instruction = (
        "You are a Ruthless Executive Assistant for a college student. "
        "Your sole purpose is to triage their incoming email.\n\n"
        f"Available categories: {', '.join(categories)}\n\n"
        "Rules:\n"
        "- If an email is a job offer, interview, placement test, or recruitment outreach → PLACEMENT\n"
        "- If an email is regarding applying for or advertising an internship → INTERNSHIP\n"
        "- If an email has a specific interview/test date and time → INTERVIEW_SCHEDULE\n"
        "- If an email mentions an upcoming deadline → DEADLINE_ALERT\n"
        "- If an email is a rejection → REJECTION\n"
        "- If an email is a standard college circular or newsletter → NEWSLETTER\n"
        "- If an email is irrelevant marketing → SPAM\n"
        "- If none of the above fit, use OTHER and set low confidence.\n"
        "- If you believe this email represents a SIGNIFICANT new category that would be "
        "useful to track (e.g., SCHOLARSHIP, HACKATHON, EXAM_NOTIFICATION), put the "
        "suggested label name in 'suggested_new_label'. Otherwise set it to null.\n"
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
            )
        )
        
        # Parse the structured response
        result = json.loads(response.text)
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Gemini returned invalid JSON: {e}")
        raise ValueError("Model failed to adhere to JSON Schema.")
    except Exception as e:
        logger.error(f"API Error during Gemini classification: {e}")
        raise

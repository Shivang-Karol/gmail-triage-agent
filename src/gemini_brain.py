"""
Gemini Brain — Migrated to google.genai SDK (replaces deprecated google.generativeai)
Uses Pydantic models for type-safe structured output.
Classifies emails into a strict 8-category closed taxonomy.
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
# Pydantic Schema (Corrected for Chain-of-Thought)
# =============================================

class EmailClassification(BaseModel):
    """Strict output schema that Gemini must adhere to. Ordered for Chain-of-Thought."""
    reasoning: str = Field(description="Step-by-step logical deduction comparing the email to Category Precedence rules. THIS MUST BE DEBATED BEFORE PICKING A CATEGORY.")
    category: str = Field(description="The final classification label for this email selected from the strict taxonomy.")
    confidence: float = Field(description="Float between 0.0 and 1.0 indicating certainty based on the Scoring Guide.")
    summary: str = Field(description="A concise 10-word summary of the email content.")

# =============================================
# Client Initialization
# =============================================

_client = None

def get_client():
    """Lazy-initialize the genai Client."""
    global _client
"""
Gemini Brain — Migrated to google.genai SDK (replaces deprecated google.generativeai)
Uses Pydantic models for type-safe structured output.
Classifies emails into a strict 8-category closed taxonomy.
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
# Pydantic Schema (Corrected for Chain-of-Thought)
# =============================================

class EmailClassification(BaseModel):
    """Strict output schema that Gemini must adhere to. Ordered for Chain-of-Thought."""
    reasoning: str = Field(description="Step-by-step logical deduction comparing the email to Category Precedence rules. THIS MUST BE DEBATED BEFORE PICKING A CATEGORY.")
    category: str = Field(description="The final classification label for this email selected from the strict taxonomy.")
    confidence: float = Field(description="Float between 0.0 and 1.0 indicating certainty based on the Scoring Guide.")
    summary: str = Field(description="A concise 10-word summary of the email content.")

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
    """Returns a tuple of (client, model_name) for compatibility with the worker."""
    config = get_config()
    model_name = config.get("model_settings", {}).get("name", "gemini-2.0-flash")
    client = get_client()
    return client, model_name

def classify_email_text(client, sender: str, subject: str, body_text: str) -> dict:
    """
    Sends the email metadata and text to Gemini using the provided client.
    Uses Google Search tool for sender verification and Chain-of-Thought for precision.
    """
    config = get_config()
    model_name = config.get("model_settings", {}).get("name", "gemini-2.0-flash")
    
    # Dynamically load examples so the user can update them without editing code
    examples_path = BASE_DIR / "config" / "few_shot_examples.json"
    few_shot_text = "No examples loaded."
    if examples_path.exists():
        with open(examples_path, "r", encoding="utf-8") as f:
            try:
                examples = json.load(f)
                few_shot_text = json.dumps(examples, indent=2)
            except json.JSONDecodeError:
                logger.error("Failed to parse few_shot_examples.json")

    system_instruction = (
        "You are an Elite Executive Assistant to a high-achieving student. "
        "Your goal is to triage incoming emails with 100% precision.\n\n"
        
        "### YOUR TOOLS:\n"
        "- GOOGLE SEARCH: If the sender's domain or the organization mentioned is unknown to you, "
        "you MUST use Google Search to verify their identity and purpose (e.g., 'What is [sender domain]?'). "
        "This is critical for distinguishing between a valid COURSE opportunity and a generic PROMOTION.\n\n"
        
        "### CATEGORIES & CONFLICT RESOLUTION (Strict Rules):\n"
        "1. EXAMS: Qualifier tests, technical assessments, or college circulars that specifically state you are *registered* for an exam or *must take* an exam. High priority.\n"
        "2. NPTEL: Assignments, hall tickets, call letters, and core communications from IITM or NPTEL. (Exception: NPTEL Newsletters go to NEWSLETTER. Coursera courses go to COURSES).\n"
        "3. PLACEMENT_CELL: Official communications from the university Placement Office or campus recruitment drives.\n"
        "4. COURSES: Genuine learning opportunities from major, multi-million user platforms like Udemy, Coursera, or edX. These are valid opportunities, not promotions.\n"
        "5. COLLEGE: General college brochures, timetables, study materials from teachers, research projects. (Exception: Casual, non-productive messages do not belong here).\n"
        "6. NEWSLETTER: Informative/promotional updates specifically from major institutes (IITs, NITs, NPTEL).\n"
        "7. PROMOTION: Marketing brochures, generic discounts from unknown/small ed-tech companies.\n"
        "8. SOCIAL: Casual connections, non-productive networking, LinkedIn requests. Note: If a message has study material from a teacher, it is COLLEGE, not SOCIAL.\n"
        "9. UNCATEGORIZED: The fallback if absolutely no other category fits.\n\n"
        
        "### CONFIDENCE SCORING GUIDE:\n"
        "You must calibrate your confidence float strictly according to this guide so the backend can automate correctly:\n"
        "- 0.95 to 0.99: Perfect match with the Few-Shot Examples or explicitly defined pre-approved sources (NPTEL, Classroom, Udemy).\n"
        "- 0.85 to 0.94: High certainty based on strong keywords and clear intent without needing a search.\n"
        "- 0.60 to 0.75: You relied heavily on the Google Search Tool to determine the company's legitimacy and made an educated deduction.\n"
        "- Below 0.50: Pure guess. Highly ambiguous.\n\n"
        
        "### FEW-SHOT EXAMPLES (For Calibration):\n"
        f"{few_shot_text}\n\n"
        
        "### INPUT FORMAT:\n"
        "You will receive:\n"
        "- SENDER: The 'From' field.\n"
        "- SUBJECT: The email title.\n"
        "- BODY: The redacted content of the email.\n\n"
        
        "### RULES:\n"
        "- Be skeptical of PROMOTIONS disguised as COURSES. Use search to verify the platform's reputation.\n"
        "- If an email is from LinkedIn but is about an INTERVIEW, it is PLACEMENT_CELL or EXAMS depending on context.\n"
    )
    
    prompt = f"SENDER: {sender}\nSUBJECT: {subject}\nBODY: {body_text}"
    
    logger.debug("Prompting Gemini API with Search Tool...")
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                response_schema=EmailClassification,
                temperature=0.1,
                max_output_tokens=512,
            )
        )
        
        # Log token usage
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            um = response.usage_metadata
            logger.info(f"Token usage — prompt: {um.prompt_token_count}, total: {um.total_token_count}")
        
        return json.loads(response.text)
        
    except Exception as e:
        logger.error(f"API Error during Gemini classification: {e}")
        raise

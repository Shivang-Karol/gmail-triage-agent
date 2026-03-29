import sys
from pathlib import Path
import json
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Add src to the path
sys.path.append(str(Path(__file__).parent.parent))

from src.gemini_brain import initialize_model, classify_email_text

def test_gemini():
    print("Initializing Gemini Model (NEW google.genai SDK)...")
    try:
        client, model_name = initialize_model()
        
        mock_email = """
        Hi Shiva, 
        
        We were very impressed with your resume. We would like to invite you 
        to interview for the Summer Software Engineering Internship role at 
        our firm next week. Please let us know your availability.
        
        Best,
        The Recruitment Team
        """
        
        print(f"Model: {model_name}")
        print(f"Sending mock email...")
        
        result = classify_email_text(client, mock_email)
        
        print("\n✅ Intelligence Working Perfectly (NEW SDK)!")
        print(f"Strict JSON Output:")
        print(json.dumps(result, indent=4))
        
        # Check if dynamic label was suggested
        if result.get('suggested_new_label'):
            print(f"\n🏷️  Gemini suggested a new label: {result['suggested_new_label']}")
        
    except Exception as e:
        print(f"\n❌ Intelligence Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini()

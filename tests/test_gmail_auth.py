import sys
from pathlib import Path

# Add src to the path so we can import our new module
sys.path.append(str(Path(__file__).parent.parent))

from src.gmail_client import get_gmail_service, setup_labels
import logging
import yaml

logging.basicConfig(level=logging.INFO)

def main():
    print("Attempting to connect to Gmail APIs...")
    try:
        service = get_gmail_service()
        print("\n✅ Authentication Successful! A token.json file was created.")
        
        from src.config_loader import get_config
        config = get_config()
            
        required_categories = config.get("categories", [])
        print(f"\nChecking your Gmail account for {len(required_categories)} necessary Agent labels...")
        
        label_ids = setup_labels(service, required_categories)
        print("\n✅ All labels verified/created successfully:")
        for name, internal_id in label_ids.items():
            print(f"   - {name} (ID: {internal_id})")
            
        print("\nSetup of Gmail Auth is Complete! The Agent can now talk to your inbox.")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("Please ensure credentials.json is saved directly in the 'gmail-triage' folder.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()

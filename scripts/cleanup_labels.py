"""
Cleanup script to remove invalid or old dynamic categories from your Gmail account.
It retrieves all your Gmail labels, checks them against the official 12 categories,
and gives you the option to manually delete any extraneous ones.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.gmail_client import get_gmail_service
from src.config_loader import get_config

def cleanup_labels():
    service = get_gmail_service()
    config = get_config()
    official_labels = set(config.get("categories", []))
    official_labels.add("REVIEW_NEEDED")  # System label

    print("Fetching current labels from Gmail...")
    results = service.users().labels().list(userId='me').execute()
    existing_labels = results.get('labels', [])

    # The Gmail API returns system labels (like INBOX, UNREAD) which we should NOT touch.
    # System labels typically have `type: 'system'`
    user_labels = [label for label in existing_labels if label.get('type') == 'user']
    
    rogue_labels = []
    for label in user_labels:
        # Check if the name is not in our official list
        if label['name'] not in official_labels:
            rogue_labels.append(label)

    if not rogue_labels:
        print("\n✅ Your Gmail is clean! No rogue labels found outside the official taxonomy.")
        return

    print(f"\nFound {len(rogue_labels)} unrecognized user labels:")
    for label in rogue_labels:
        print(f" - {label['name']} (ID: {label['id']})")

    print("\nDo you want to delete these rogue labels from your Gmail account?")
    print("WARNING: This will remove the label from any emails that had it applied, but it will NOT delete the emails themselves.")
    
    choice = input("Type 'yes' to delete them all, or 'no' to keep them: ").strip().lower()
    if choice == 'yes':
        for label in rogue_labels:
            try:
                service.users().labels().delete(userId='me', id=label['id']).execute()
                print(f"🗑️ Deleted label: {label['name']}")
            except Exception as e:
                print(f"❌ Failed to delete {label['name']}: {e}")
        print("\nCleanup complete!")
    else:
        print("Cleanup aborted. The labels were not deleted.")

if __name__ == "__main__":
    cleanup_labels()

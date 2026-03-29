import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# The scope we need to read and modify labels
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Paths to the Secrets
BASE_DIR = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = BASE_DIR / 'credentials.json'
TOKEN_PATH = BASE_DIR / 'token.json'

def get_gmail_service():
    """
    Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail token...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(f"Missing {CREDENTIALS_PATH}. Please download it from Google Cloud Console.")
            logger.info("Starting initial OAuth login flow. Please check your browser.")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES)
            # This opens the browser!
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    # Build the service object
    service = build('gmail', 'v1', credentials=creds)
    return service

def setup_labels(service, required_labels):
    """
    Checks if the required labels exist in the user's Gmail.
    If they don't, creates them with color coding for visual scanning.
    Returns a dictionary mapping label names to their internal Gmail IDs.
    """
    # Gmail API label color options
    # See: https://developers.google.com/gmail/api/reference/rest/v1/users.labels
    LABEL_COLORS = {
        'PLACEMENT':          {'textColor': '#ffffff', 'backgroundColor': '#fb4c2f'},  # Red
        'INTERNSHIP':         {'textColor': '#ffffff', 'backgroundColor': '#16a765'},  # Green
        'INTERVIEW_SCHEDULE': {'textColor': '#ffffff', 'backgroundColor': '#ff7537'},  # Orange
        'DEADLINE_ALERT':     {'textColor': '#ffffff', 'backgroundColor': '#ffad47'},  # Yellow-Orange
        'REJECTION':          {'textColor': '#ffffff', 'backgroundColor': '#98a0a6'},  # Gray
        'NEWSLETTER':         {'textColor': '#ffffff', 'backgroundColor': '#4986e7'},  # Blue
        'SPAM':               {'textColor': '#ffffff', 'backgroundColor': '#b99aff'},  # Purple
        'OTHER':              {'textColor': '#ffffff', 'backgroundColor': '#68dfa9'},  # Teal
        'REVIEW_NEEDED':      {'textColor': '#ffffff', 'backgroundColor': '#e07798'},  # Pink
    }
    
    results = service.users().labels().list(userId='me').execute()
    existing_labels = results.get('labels', [])
    
    label_map = {label['name']: label['id'] for label in existing_labels}
    created_map = {}
    
    for req in required_labels:
        if req in label_map:
            created_map[req] = label_map[req]
        else:
            logger.info(f"Creating missing label: {req}")
            label_body = {
                'name': req,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            # Apply color if we have one defined
            if req in LABEL_COLORS:
                label_body['color'] = LABEL_COLORS[req]
            
            new_label = service.users().labels().create(
                userId='me',
                body=label_body
            ).execute()
            created_map[req] = new_label['id']
            
    return created_map

def fetch_message_body(service, message_id):
    """
    Given an email ID, recursively searches for the plaintext body.
    """
    try:
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        # Traverse payload to find 'text/plain' or 'text/html'
        def extract_parts(parts):
            text = ""
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    import base64
                    data = part['body'].get('data')
                    if data:
                        text += base64.urlsafe_b64decode(data).decode('utf-8')
                elif 'parts' in part:
                    text += extract_parts(part['parts'])
            return text

        payload = msg.get('payload', {})
        if payload.get('mimeType') == 'text/plain' and 'data' in payload.get('body', {}):
            import base64
            body_text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        else:
            body_text = extract_parts(payload.get('parts', []))
            
        return body_text.strip()
    except Exception as e:
        logger.error(f"Failed to fetch body for {message_id}: {e}")
        return ""

def apply_label(service, message_id, label_id):
    """Applies a label idempotently to a specific email."""
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={
                'addLabelIds': [label_id],
                # If we want to remove from inbox we would do:
                # 'removeLabelIds': ['INBOX']
            }
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Failed to apply label {label_id} to {message_id}: {e}")
        return False

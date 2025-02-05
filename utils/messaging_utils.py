# utils/messaging_utils.py

from twilio.rest import Client
from utils.logger import app_logger as logger
from config import load_config
import json


# Load Twilio configuration
config = load_config()

account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']

# External api configs

patient_list_api = config['fetch_pt_list']

# Initialize Twilio Client
client = Client(account_sid, auth_token)

def send_whatsapp_message(to: str, body: str = None, content_sid: str = None, content_variables: dict = None) -> bool:
    """
    Sends a WhatsApp message using Twilio.
    add_pt_cta"""
    try:
        if content_sid:
            client.messages.create(
                from_=twilio_whatsapp_number,
                content_sid=content_sid,
                content_variables=json.dumps(content_variables) if content_variables else None,
                to=to
            )
        else:
            client.messages.create(
                body=body,
                from_=twilio_whatsapp_number,
                to=to
            )
        logger.info(f"Message sent successfully to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message to {to}: {e}")
        return False
    

def clean_mobile_number_for_api(mobile: str) -> str:
    """Cleans the mobile number for external APIs (10 digits only)."""
    mobile = mobile.strip()
    if mobile.startswith("whatsapp:"):
        mobile = mobile.replace("whatsapp:", "").strip()
    if mobile.startswith("+91"):
        mobile = mobile[3:]  # Remove '+91' prefix
    if not mobile.isdigit() or len(mobile) != 10:
        raise ValueError(f"Invalid mobile number. Must be 10 digits. Received: {mobile}")
    return mobile

def format_mobile_for_twilio(mobile: str) -> str:
    """
    Formats the mobile number for Twilio usage (adds 'whatsapp:+91' if not already formatted).
    """
    mobile = mobile.strip()

    # Remove any existing 'whatsapp:' or '+91' prefixes
    if mobile.startswith("whatsapp:"):
        mobile = mobile.replace("whatsapp:", "").strip()
    if mobile.startswith("+91"):
        mobile = mobile[3:]

    # Ensure the number is 10 digits
    if not mobile.isdigit() or len(mobile) != 10:
        raise ValueError(f"Invalid mobile number. Must be 10 digits. Received: {mobile}")

    # Reformat to 'whatsapp:+91<number>'
    formatted_mobile = f"whatsapp:+91{mobile}"
    return formatted_mobile


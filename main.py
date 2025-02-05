from twilio.rest import Client
from config import load_config

# Import utilities
from utils.messaging_utils import clean_mobile_number_for_api, format_mobile_for_twilio
from utils.logger import app_logger as logger

# Import new_user
from new_user.new_user_reg import handle_greeting, handle_user_registration_flow
from new_user.user_address import add_new_address
from new_user.book_presc import booking_with_prescription

# Import state manager
from state.state_manager import user_registration_state

# Import existing_user
from booking.self_booking import add_patient_flow_self
from existing_user.user_address_existing import existing_user_address
from existing_user.booking_details import booking_details
from existing_user.download_reports import handle_download_report
from existing_user.existing_user import handle_user_interaction

from booking.other_booking import add_patient_flow_others
from booking.add_family import add_family_member
# Load configuration
logger.info("Loading configuration.")
config = load_config()

# WhatsApp configurations
account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']

# Initialize Twilio client
client = Client(account_sid, auth_token)

# Core Function: Process Messages
def process_message(mobile: str, message: str, request_data: dict) -> dict:
    """
    Processes the incoming message and routes it based on the user's current state.
    """
    logger.info(f"Processing message from {mobile}.")
    mobile_api = clean_mobile_number_for_api(mobile)
    mobile_twilio = format_mobile_for_twilio(mobile)

    # Handle greeting: Reset state and restart
    if message.lower().strip() in ["hi", "hello"]:
        logger.info(f"User {mobile_api} said 'hi'. Restarting the conversation.")
        if mobile_api in user_registration_state:
            del user_registration_state[mobile_api]
        return handle_greeting(mobile_api, mobile_twilio)

    # Check user's current state
    user_state = user_registration_state.get(mobile_api, {})
    action = user_state.get("action")

    # Handle existing user interactions
    if action == "existing_user":
        logger.info(f"User {mobile_api} selected option: {message.strip()}")
        return handle_user_interaction(mobile_api, mobile_twilio, message.strip())

    if action == "user_registration":
        # Handle user registration flow
        registration_response = handle_user_registration_flow(mobile_api, mobile_twilio, message)
        if registration_response.get("status") == "success" and "registration successful" in registration_response.get("message", "").lower():
            # Automatically transition to Add Patient
            logger.info(f"Registration successful for {mobile_api}. Transitioning to Add Patient flow.")
            return add_patient_flow_self(mobile_api, mobile_twilio)
        return registration_response



    elif action == "booking_person":
        return add_patient_flow_self(mobile_api, mobile_twilio, message)

    elif action == "other_booking":
        return add_patient_flow_others(mobile_api, mobile_twilio, message, request_data)
    
    elif action == "family_member_booking":
        return add_family_member(mobile_api, mobile_twilio, message)


    elif action == "add_new_address":
        # Handle Add Address flow
        return add_new_address(mobile_api, mobile_twilio, message)


    elif action == "booking_with_prescription":
        # Handle Booking with Prescription flow
        return booking_with_prescription(mobile_api, mobile_twilio, message, request_data)



    elif action == "download_report":
        # Handle Download Report flow
        return handle_download_report(mobile_api, mobile_twilio, message)

    elif action == "booking_details":
        # Handle Booking Details flow
        return booking_details(mobile_api, mobile_twilio, message)

    elif action == "existing_address":
        # Handle Address Flow
        logger.debug(f"Routing to existing_user_address for {mobile_api}. Current state: {user_registration_state.get(mobile_api)}")
        return existing_user_address(mobile_api, mobile_twilio, message)

    # Fallback for unrecognized input
    logger.warning(f"Unhandled message from {mobile_api}: {message}")
    return {
        "status": "ignored",
        "message": "Type 'hi' to start the conversation."
    }

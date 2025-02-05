# existing/existing_user.py

from twilio.rest import Client
import requests
from config import load_config
from utils.logger import app_logger as logger
from utils.messaging_utils import format_mobile_for_twilio
from existing_user.download_reports import handle_download_report
from existing_user.booking_details import booking_details
from booking.self_booking import add_patient_flow_self
from state.state_manager import user_registration_state
import json

# Load configuration
config = load_config()
user_view = config['user_view']
account_sid = config['account_sid']
auth_token = config['auth_token']

twilio_whatsapp_number = config['phone_number']
existing_user_options_sid = config['existing_user_options_sid']


# Initialize Twilio Client
client = Client(account_sid, auth_token)


def handle_user_interaction(mobile_api: str, mobile_twilio: str, option: str = None) -> dict:
    """
    Handles interaction with an existing user, including greeting and processing chosen options.
    """
    logger.info(f"Handling user interaction for {mobile_api} with option: {option}")

    if not option:
        # Initial greeting and option presentation
        try:
            payload = {"UserName": mobile_api}
            response = requests.post(user_view, json=payload)
            response.raise_for_status()

            user_data = response.json()
            if user_data.get("SuccessFlag") == "true" and user_data.get("Code") == 200:
                user_name = user_data["Message"][0].get("Name", "User")
            else:
                user_name = "User"
        except requests.RequestException as e:
            logger.error(f"Error fetching user name from API for {mobile_api}: {e}")
            user_name = "User"

        # Update user state  
        user_registration_state[mobile_api] = {"action": "existing_user", "step": "awaiting_option"}

        # Inline logic to send quick reply template
        try:

            # Format the mobile number for Twilio
            to = format_mobile_for_twilio(mobile_twilio)
            content_variables = {"1": user_name}
            logger.debug(f"Content Variables: {content_variables}")

            # Send the quick reply template using content SID
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=existing_user_options_sid,
                content_variables=json.dumps(content_variables)
            )
            logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
            return {"status": "success", "message_sid": message.sid}
        except ValueError as ve:
            logger.error(f"Invalid mobile number provided: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
            return {"status": "error", "error": str(e)}

    # Handle the user's choice
    option = option.strip()
    if option == "New booking":
        logger.info("Option 1 selected: Asking booking person.")
        user_registration_state[mobile_api] = {"action": "booking_person", "step": "ask_booking_person"}
        return add_patient_flow_self(mobile_api, mobile_twilio)

    elif option == "Booking details":
        logger.info("Option 2 selected: Fetching existing booking details.")
        user_registration_state[mobile_api] = {"action": "booking_details", "step": "fetch_booking_list"}
        return booking_details(mobile_api, mobile_twilio)

    elif option == "Download reports":
        logger.info("Option 3 selected: Downloading old reports.")
        return handle_download_report(mobile_api, mobile_twilio)

    else:
        try:
            # Format the mobile number for Twilio
            to = format_mobile_for_twilio(mobile_twilio)

            # Resend the quick reply template using content SID
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=existing_user_options_sid
            )
            logger.info(f"Quick reply template re-sent to {to} with SID: {message.sid}")
            return {"status": "success", "message_sid": message.sid}
        except ValueError as ve:
            logger.error(f"Invalid mobile number provided: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to resend quick reply template to {mobile_twilio}: {e}")
            return {"status": "error", "error": str(e)}

# new_user/user_add.py

import requests
from config import load_config
from state.state_manager import user_registration_state
from twilio.rest import Client
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message, format_mobile_for_twilio
from new_user.book_presc import booking_with_prescription

# Load configuration
config = load_config()
add_address_api = config['add_user_address_api']
account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']

# Initialize Twilio Client
client = Client(account_sid, auth_token)


province_sid = config['province_sid']
user_address_confirmation = config['user_address_confirmation']

def add_new_address(mobile_api: str, mobile_twilio: str, message: str = None) -> dict:
    """
    Handles the complete address addition flow in a single function.
    If message is None, starts the flow. Otherwise, processes the current step.
    """
    # Start flow if message is None
    if message is None:
        user_registration_state[mobile_api] = {"action": "add_new_address", "step": "ask_door_apartment"}
        response_message = "Please enter your door number and apartment name (e.g., 12, Sunshine Apartment)."
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}

    # Check if state exists
    if mobile_api not in user_registration_state:
        logger.warning(f"No state found for user {mobile_api}. Reinitializing address flow.")
        return add_new_address(mobile_api, mobile_twilio)

    state = user_registration_state[mobile_api]

    # Handle each step
    if state["step"] == "ask_door_apartment":
        state["door_apartment"] = message.strip()
        state["step"] = "ask_locality"
        user_registration_state[mobile_api] = state
        response_message = "Please enter your locality (e.g., Abha Street)."
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}

    elif state["step"] == "ask_locality":
        state["locality"] = message.strip()
        state["step"] = "ask_zip_code"
        user_registration_state[mobile_api] = state
        response_message = "Please enter your zip code (5 digits, e.g., 13525)."
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}

    elif state["step"] == "ask_zip_code":
        if not message.strip().isdigit() or len(message.strip()) != 5:
            response_message = "Invalid zip code. Please enter a valid 5-digit zip code (e.g., 13525)."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

        state["zip_code"] = message.strip()
        state["step"] = "ask_province"
        user_registration_state[mobile_api] = state

        try:
            to = format_mobile_for_twilio(mobile_twilio)
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=province_sid
            )
            logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
            return {"status": "success", "message_sid": message.sid}
        except Exception as e:
            logger.error(f"Failed to send province options: {e}")
            return {"status": "error", "error": str(e)}

    elif state["step"] == "ask_province":
        province_mapping = {
            "1": "Riyadh", "2": "Jeddah", "3": "Dammam",
            "4": "Mecca", "5": "Medina"
        }


        # Ask Province
        province = province_mapping.get(message.strip())
        if not province:
            try:
                to = format_mobile_for_twilio(mobile_twilio)
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid=province_sid
                )
                return {"status": "success", "message_sid": message.sid}
            except Exception as e:
                return {"status": "error", "error": str(e)}

        state["province"] = province
        state["country"] = "Saudi Arabia"
        state["step"] = "confirm_address"
        user_registration_state[mobile_api] = state

        # address Confirmation
        try:
            to = format_mobile_for_twilio(mobile_twilio)
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=user_address_confirmation
            )
            return {"status": "success", "message_sid": message.sid}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    elif state["step"] == "confirm_address":
        city_to_region_mapping = {
            "Riyadh": "Riyadh Region",
            "Jeddah": "Makkah Region",
            "Dammam": "Eastern Province",
            "Mecca": "Makkah Region",
            "Medina": "Madinah Region"
        }

        if message.strip().lower() == "yes":
            city = state["province"]
            region = city_to_region_mapping.get(city, city)
            payload = {
                "Username": mobile_api,
                "Address_Type": "01",
                "Street": state["door_apartment"],
                "Place": state["locality"],
                "City": city,
                "State": region,
                "Country": state["country"],
                "Pincode": state["zip_code"],
                "Location": "Updated Location",
                "Landmark": "Updated Landmark",
                "Latitude": "14.025649",
                "Longitude": "79.125487"
            }

            response = requests.post(add_address_api, json=payload)
            if response.status_code == 200 and response.json().get("SuccessFlag") == "true":
                response_message = "Your address has been added successfully!"
                send_whatsapp_message(mobile_twilio, body=response_message)
                return booking_with_prescription(mobile_api, mobile_twilio)

            response_json = response.json()
            if response.status_code == 404 and response_json.get("Message", [{}])[0].get("Message") == "This User is already mapped this address type!":
                logger.error("The user is already mapped with this address")
                return booking_with_prescription(mobile_api, mobile_twilio)

            response_message = "Failed to add the address. Type 'hi' to start the conversation again."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

        elif message.strip().lower() == "no":
            state["step"] = "ask_door_apartment"
            user_registration_state[mobile_api] = state
            response_message = "Let's restart. Please enter your door number and apartment name (e.g., 12, Sunshine Apartment)."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "success", "message": response_message}

        else:

            # address Confirmation
            try:
                to = format_mobile_for_twilio(mobile_twilio)
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid=user_address_confirmation
                )
                return {"status": "success", "message_sid": message.sid}
            except Exception as e:
                return {"status": "error", "error": str(e)}

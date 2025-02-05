
# new_user/booking_details.py

import requests
from twilio.rest import Client
from config import load_config
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message, format_mobile_for_twilio
from state.state_manager import user_registration_state
import json
config = load_config()

get_booking_api = config['get_booking_api']
booking_list = config['booking_list']

account_sid = config['account_sid']
auth_token = config['auth_token']

twilio_whatsapp_number = config['phone_number']
client = Client(account_sid, auth_token)

# Twilio content sid
booking_details_sid = config['booking_details_sid']

def booking_details(mobile_api: str, mobile_twilio: str, message: str | None = None) -> dict:
    """
    Handles the flow for fetching and displaying booking details.
    """
    # Initialize flow if no message is provided
    if not message:
        user_registration_state[mobile_api] = {
            "action": "booking_details",
            "step": "fetch_booking_list"
        }

    state = user_registration_state[mobile_api]
    logger.info(f"Handling booking details flow for user {mobile_api}. Current state: {state}")

    # Step 1: Fetch and Display Booking List
    if state["step"] == "fetch_booking_list":
        try:
            # API call to fetch booking list
            response = requests.post(booking_list, json={"Username": mobile_api})
            response.raise_for_status()
            api_response = response.json()

            booking_list_data = api_response.get("Message", [{}])[0].get("Booking_Detail", [])
            if not booking_list_data:
                response_message = "No bookings found for the provided information."
                send_whatsapp_message(mobile_twilio, body=response_message)
                del user_registration_state[mobile_api]
                return {"status": "not_found", "message": response_message}

            # Save the booking list in state
            state["booking_list"] = {
                str(idx): booking for idx, booking in enumerate(booking_list_data[:3], 1)
            }


            # Prepare the content variables for Quick Reply
            content_variables = {}
            used_texts = set()  # To track and avoid duplicate button text

            for idx, booking in state["booking_list"].items():
                booking_date = booking["Booking_Date"]
                pt_name = booking["Pt_Name"].split()[0]  # Use only the first name


                # Convert booking_date to datetime and format it
                from datetime import datetime
                booking_datetime = datetime.strptime(booking_date, '%Y/%m/%d')
                formatted_date = booking_datetime.strftime('%d/%m/%Y')  # Format as '01-Jan'
                combined_text = f"{formatted_date} {pt_name}"

                # Truncate to fit within 24 characters
                if len(combined_text) > 24:
                    max_length = 24 - len(booking_date) - 1  # Reserve 1 space between date and name
                    pt_name = pt_name[:max_length].strip() + "..."  # Truncate name if necessary
                    combined_text = f"{booking_date} {pt_name}"

                # Ensure unique button text by appending a unique index if necessary
                while combined_text in used_texts:
                    if len(combined_text) >= 24:
                        combined_text = combined_text[:23] + str(idx)  # Truncate further and append index
                    else:
                        combined_text += f" ({idx})"

                used_texts.add(combined_text)
                content_variables[str(idx)] = combined_text

            # Fill placeholders for any missing slots (up to 3)
            for i in range(1, 4):
                if str(i) not in content_variables:
                    content_variables[str(i)] = "No Booking Available"

            # Log the content variables for debugging
            logger.debug(f"Final Content Variables (24-char limit): {content_variables}")

            # Send Quick Reply template
            to = format_mobile_for_twilio(mobile_twilio)
            client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid= booking_details_sid,  
                content_variables=json.dumps(content_variables)  # Convert content_variables
            )

            state["step"] = "fetch_booking_details"
            return {"status": "success", "message": "Booking list sent to the user."}

        except requests.RequestException as e:
            logger.error(f"Error fetching booking list for {mobile_api}: {e}")
            response_message = "Unable to fetch bookings. Please try again later."
            send_whatsapp_message(mobile_twilio, body=response_message)
            del user_registration_state[mobile_api]
            return {"status": "error", "message": response_message}




# Step 2: Fetch and Display Booking Details
    elif state["step"] == "fetch_booking_details":
        user_input = message.strip()  # Strip any extra spaces
        user_input = str(user_input)  # Ensure the input is a string

        # Fetch the selected booking using the input as a key
        selected_booking = state["booking_list"].get(user_input)

        # Log debugging information
        logger.debug(f"User input: {user_input}")
        logger.debug(f"Booking list keys: {state['booking_list'].keys()}")
        logger.debug(f"Selected booking: {selected_booking}")

        if not selected_booking:
            # Notify user that no booking exists for the selected option
            response_message = f"No booking found for the selected option: {user_input}. Please choose a valid option."
            send_whatsapp_message(mobile_twilio, body=response_message)

            # Resend the Quick Reply template
            to = format_mobile_for_twilio(mobile_twilio)
            content_variables = {
                str(idx): f"{booking['Booking_Date']} {booking['Pt_Name'].split()[0]} ({idx})"
                for idx, booking in state["booking_list"].items()
            }
            for i in range(1, 4):
                if str(i) not in content_variables:
                    content_variables[str(i)] = "No Booking Available"

            client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=booking_details_sid,
                content_variables=json.dumps(content_variables)
            )
            return {"status": "error", "message": response_message}

        # Valid booking selected, send detailed information
        logger.info(f"Selected Booking: {selected_booking}")

        # Prepare and send the booking details message
        response_message = (
            f"Here are the booking details:\n\n"
            f"Name: {selected_booking.get('Pt_Name', 'N/A')}\n"
            f"Booking Date: {selected_booking.get('Booking_Date', 'N/A')}\n"
            f"Report Status: {selected_booking.get('Report_Status', 'N/A')}\n"
            f"Booking Status: {selected_booking.get('Booking_Status_Desc', 'N/A')}\n"
            f"Branch Name: {selected_booking.get('Branch_Name', 'N/A')}\n\n"
            "Thank you for choosing us! 😊\n\n"
            "Type *Hi* to restart the conversation."
        )
        send_whatsapp_message(mobile_twilio, body=response_message)

        # Clear user state after processing
        del user_registration_state[mobile_api]
        return {"status": "success", "message": response_message}

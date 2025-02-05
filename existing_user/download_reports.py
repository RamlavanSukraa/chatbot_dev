# new_user/download_reports.py

import requests
from twilio.rest import Client
from config import load_config
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message, format_mobile_for_twilio
from state.state_manager import user_registration_state
import json
from datetime import datetime

# Load configuration
config = load_config()

download_reports = config['download_reports']
booking_list = config['booking_list']

account_sid = config['account_sid']
auth_token = config['auth_token']

client = Client(account_sid, auth_token)

twilio_whatsapp_number = config['phone_number']

# Content sid
booking_details_sid = config['booking_details_sid']


def handle_download_report(mobile_api: str, mobile_twilio: str, message: str = None) -> dict:
    """
    Handles the flow for downloading reports, including fetching and displaying booking list first.
    """
    # Initialize state for the download report flow
    if not message:
        user_registration_state[mobile_api] = {
            "action": "download_report",
            "step": "fetch_booking_list"
        }

    state = user_registration_state.get(mobile_api, {})
    logger.info(f"Handling download report flow for user {mobile_api}. Current state: {state}")

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

            # Prepare content variables for Quick Reply
            content_variables = {}
            for idx, booking in state["booking_list"].items():
                booking_date = booking["Booking_Date"]
                pt_name = booking["Pt_Name"].split()[0]  # Use only the first name

                # Convert booking_date to datetime and format it
                booking_datetime = datetime.strptime(booking_date, '%Y/%m/%d')
                formatted_date = booking_datetime.strftime('%d/%m/%Y')  # Format as 'DD/MM/YYYY'
                combined_text = f"{formatted_date} {pt_name}"

                # Truncate text to fit within 24 characters
                if len(combined_text) > 24:
                    pt_name = pt_name[:24 - len(formatted_date) - 1].strip() + "..."
                    combined_text = f"{formatted_date} {pt_name}"

                content_variables[str(idx)] = combined_text

            # Fill placeholders for any missing slots (up to 3)
            for i in range(1, 4):
                if str(i) not in content_variables:
                    content_variables[str(i)] = "No Booking Available"

            # Log content variables for debugging
            logger.debug(f"Final Content Variables (24-char limit): {content_variables}")

            # Send Quick Reply template
            to = format_mobile_for_twilio(mobile_twilio)
            client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=booking_details_sid,
                content_variables=json.dumps(content_variables)
            )

            state["step"] = "ask_booking_no"
            return {"status": "success", "message": "Booking list sent to the user."}

        except requests.RequestException as e:
            logger.error(f"Error fetching booking list for {mobile_api}: {e}")
            response_message = "Unable to fetch bookings. Please try again later."
            send_whatsapp_message(mobile_twilio, body=response_message)
            del user_registration_state[mobile_api]
            return {"status": "error", "message": response_message}

    # Step 2: Handle User Input for Booking Selection
    elif state["step"] == "ask_booking_no":
        user_input = str(message.strip())  # Ensure input is treated as a string
        selected_booking = state["booking_list"].get(user_input)

        if not selected_booking:
            # Handle invalid booking selection
            response_message = f"No booking found for the selected option: {user_input}. Please choose a valid option."
            send_whatsapp_message(mobile_twilio, body=response_message)

            # Resend Quick Reply template
            to = format_mobile_for_twilio(mobile_twilio)
            content_variables = {
                str(idx): f"{datetime.strptime(booking['Booking_Date'], '%Y/%m/%d').strftime('%d/%m/%Y')} {booking['Pt_Name'].split()[0]}"
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

        # Step 3: Fetch and Send the Report
        booking_id = selected_booking["Booking_No"]
        logger.info(f"Fetching report for Booking ID: {booking_id}")



        try:
            report_url_endpoint = f"{download_reports}/{booking_id}"
            response = requests.get(report_url_endpoint)
            response.raise_for_status()
            api_response = response.json()

            report_url = api_response.get("pdf_url")
            if report_url:
                response_message = (
                    "Here is your report.👇\n\n"
                    f"{report_url}\n\n"
                    "Thank you for using us! 😊\n"
                    "Type *Hi* to restart the conversation."
                )
                send_whatsapp_message(mobile_twilio, body=response_message)
                del user_registration_state[mobile_api]
                return {"status": "success", "message": response_message}
            else:
                raise ValueError("PDF URL not found in API response.")

        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 404:
                logger.error(f"Report not found for Booking ID: {booking_id}. URL: {report_url_endpoint}")
                response_message = (
                    "There are no reports available for this booking."
                    "Type *Hi* to restart the conversation."
                )
            else:
                logger.error(f"HTTP error occurred: {http_err}")
                response_message = "Unable to fetch the report due to a server error. Please try again later."

        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error while accessing the Report API: {report_url_endpoint}")
            response_message = "Unable to connect to the report server. Please check your internet connection or try again later."

        except requests.exceptions.Timeout:
            logger.error(f"Timeout while accessing the Report API: {report_url_endpoint}")
            response_message = "The request to fetch the report timed out. Please try again later."

        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            response_message = "An unexpected error occurred while fetching the report. Please try again later."

        # Send the fallback error message to the user
        send_whatsapp_message(mobile_twilio, body=response_message)
        del user_registration_state[mobile_api]
        return {"status": "error", "message": response_message}



    # Default fallback for unexpected input or state
    response_message = "Unexpected input. Type 'Hi' to restart the process."
    send_whatsapp_message(mobile_twilio, body=response_message)
    del user_registration_state[mobile_api]
    return {"status": "error", "message": "Invalid state or unrecognized input."}

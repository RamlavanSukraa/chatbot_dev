# controller/view_pt.py

import requests

from config import load_config
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message

config = load_config()

patient_list_api = config['fetch_pt_list']


def fetch_patient_details(username: str, mobile_twilio: str, user_state: dict) -> dict:
    """
    Fetch patient details from the external API.
    """
    logger.info(f"Fetching patient details for {username}.")
    try:
        response = requests.post(patient_list_api, json={"Username": username})

        # If the user is not found (404)
        if response.status_code == 404:
            if user_state.get("cta_sent", False):
                return {"status": "error", "message": "No patient details found."}

            logger.warning(f"No patient details found for user: {username}")
            # Mark CTA as sent to avoid duplicate prompts
            return {"status": "error", "message": "Message sent for adding patient."}

        # Successful fetch of patient details
        elif response.status_code == 200 and response.json().get("SuccessFlag") == "true":
            logger.info("Patient details fetched successfully.")
            return response.json()

        # If API response is unsuccessful
        else:
            logger.error("Failed to fetch patient details or no data found.")
            if not user_state.get("cta_sent", False):
                response_message = (
                    "Failed to fetch patient details.\n"
                )
                send_whatsapp_message(mobile_twilio, body=response_message)
                user_state["cta_sent"] = True
            return {"status": "error", "message": "CTA sent for adding patient."}

    except requests.RequestException as e:
        # Handle API connection failure
        logger.error(f"Failed to connect to patient details API: {e}")
        if not user_state.get("cta_sent", False):
            response_message = (
                "Failed to connect to the server.\n"
            )
            send_whatsapp_message(mobile_twilio, body=response_message)
            user_state["cta_sent"] = True
        return {"status": "error", "message": "CTA sent for server error."}

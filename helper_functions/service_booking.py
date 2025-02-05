

import requests
from config import load_config
from utils.logger import app_logger as logger
from new_user.view_pt_det import fetch_patient_details
from state.state_manager import user_registration_state
from utils.messaging_utils import send_whatsapp_message

config = load_config()
save_booking_url = config['save_booking_url']


def save_booking_to_db(api_response: dict):
    """
    Calls the FastAPI endpoint to save booking data to MongoDB.
    """
    try:
        # Endpoint for the FastAPI save_booking API
        

        # POST the booking response to the save_booking API
        response = requests.post(
            save_booking_url,
            json=api_response
        )
        response.raise_for_status()

        # Log and handle the response from the save_booking API
        if response.status_code == 200:
            logger.info("Booking details successfully saved to the database.")
            return {"status": "success", "message": "Booking saved to database."}
        else:
            logger.error(f"Failed to save booking to database. Response: {response.json()}")
            return {"status": "error", "message": "Failed to save booking to database."}

    except requests.RequestException as e:
        logger.error(f"Error while calling save_booking API: {e}")
        return {"status": "error", "message": str(e)}



def handle_patient_details(mobile_api: str, mobile_twilio: str) -> dict:
    """
    Fetch and send all patient details to the user with detailed logging.
    """
    user_state = user_registration_state.setdefault(mobile_api, {})

    logger.info(f"Fetching patient details for user: {mobile_api}")

    # Fetch patient details
    patient_details = fetch_patient_details(mobile_api, mobile_twilio, user_state)
    logger.debug(f"API Response: {patient_details}")

    if patient_details.get("status") == "error":
        logger.warning(f"No patient details found for user: {mobile_api}")
        return {"status": "error", "message": patient_details["message"]}

    try:
        patient_list = patient_details.get("Message", [])[0].get("Patient_Detail", [])
        if not patient_list:
            raise KeyError("Missing 'Patient_Detail' in response.")

        response_message = "👩‍⚕️ *Patient Details*\n\n"

        for idx, patient in enumerate(patient_list, start=1):
            response_message += (
                f"*{idx}.* {patient.get('Pt_Name', 'N/A')} ({patient.get('Pt_First_Age', 'N/A')} {patient.get('Pt_First_Age_Period', 'N/A')}, {patient.get('Pt_Gender', 'N/A')})\n"
                f"    ID: {patient.get('Pt_Code', 'N/A')}\n"
            )

        response_message += "\n👉 *Reply with the serial number* (e.g., 1, 2, etc.) of the patient you want to proceed with."
        send_whatsapp_message(mobile_twilio, body=response_message)




        logger.info(f"All patient details sent successfully to {mobile_twilio}")
        return {"status": "success", "message": response_message}

    except KeyError as e:
        logger.error(f"KeyError while processing patient details: {e}")
        return {"status": "error", "message": "An error occurred while fetching patient details."}
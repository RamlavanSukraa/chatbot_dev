

# existing/add_pt_existing.py

import requests
from config import load_config

from twilio.rest import Client

from existing_user.user_address_existing import existing_user_address
from new_user.user_address import add_new_address
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message
from utils.messaging_utils import clean_mobile_number_for_api
from state.state_manager import user_registration_state, self_state, relationship_state

config = load_config()

# Load Twilio configuration

account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']

# External api configs
add_patient_api = config['add_patient']
get_user_address_api = config['get_user_address_api']



# Initiate Twilio Client
client = Client(account_sid, auth_token)

# Db apis
check_nationality_api = config['check_nationality_api']
save_user_details_api = config['save_user_details_api']
update_nationality_api = config['update_nationality_api']
check_surname_api = config['check_surname_api']




# Function to send the Add Patient API request
def add_patient_to_api(mobile_api: str, mobile_twilio: str, state: dict) -> dict:
    """
    Sends the Add Patient API request and handles the response.
    """
    try:
        # Clean the mobile number for API use
        username = clean_mobile_number_for_api(mobile_api)
        logger.debug(f"Cleaned mobile number: {username}")
    except ValueError as e:
        logger.error(f"Error validating Username: {e}")
        send_whatsapp_message(mobile_twilio, body="Invalid mobile number. Please provide a valid 10-digit mobile number.")
        return {"status": "error", "message": str(e)}

    # Prepare the payload to send to the Add Patient API
    payload = {
        "Username": username,
        "Pt_Name": f"{state.get('first_name')} {state.get('surname')}",
        "First_Name": state.get("first_name"),
        "Sur_Name": state.get("surname"),
        "Dob": state.get("dob"),
        "Gender": state.get("gender"),
        "Mobile_No": state.get("mobile", username),
        "Street": state.get("street"),
        "Place": state.get("place"),
        "City": state.get("city"),
        "RelationShip_Code": state.get("relation_code"),
        "MedicalAid_No": None,
        "Ref_Code": None,
        "Nationality": state.get("nationality", "Saudi"),
    }

    logger.debug(f"Payload sent to Add Patient API: {payload}")

    # Make the request to Add Patient API
    response = requests.post(add_patient_api, json=payload)
    api_response = response.json()

    # Log the API response status and content
    logger.debug(f"API Response Status Code: {response.status_code}")
    logger.debug(f"API Response Content: {api_response}")   




    # Handle 200 OK Response (Patient Added)

    if api_response.get("SuccessFlag") == "true":
        patient_code = api_response["Message"][0].get("Patient_Code", "N/A")


        # Check if the "self" flag is present in self_state for mobile_api
        if mobile_api not in self_state:
            self_state[mobile_api] = {}       
            # Save the patient code to the state only when self is present
            self_state[mobile_api]["patient_code"] = patient_code
            logger.debug(f"Patient code saved to self_state for {mobile_api}: {self_state[mobile_api]}")
            logger.info(f"Patient added successfully with Patient Code: {patient_code}")



        del user_registration_state[mobile_api]

        # Check if the patient has an address
        address_payload = {"Username": mobile_api}
        address_response = requests.post(get_user_address_api, json=address_payload)  # Use POST as per request format

        if address_response.status_code == 200:
            address_data = address_response.json()
            user_message_data = address_data.get("Message", [{}])

            if isinstance(user_message_data, list) and len(user_message_data) > 0:
                user_address_list = user_message_data[0].get("User_Address", [])

                if isinstance(user_address_list, list) and len(user_address_list) > 0:
                    logger.info(f"Address found for {mobile_api}, proceeding to existing address flow.")
                    return existing_user_address(mobile_api, mobile_twilio, message="")

        # If no address exists, prompt the user to add a new address
        logger.info(f"No address found for {mobile_api}, proceeding to add new address flow.")
        return add_new_address(mobile_api, mobile_twilio)




    
    elif response.status_code == 404 and "Patient is already registered" in api_response.get("Message", [{}])[0].get("Message", ""):
        message = api_response["Message"][0].get("Message", "")

        # Extract patient code safely
        if "Patient Code is :" in message:
            patient_code = message.split("Patient Code is :")[1].strip()
            logger.info(f"Patient already registered. Patient Code: {patient_code}")

            # Ensure self_state exists before updating
            if mobile_api not in self_state:
                self_state[mobile_api] = {}

            # Save the patient code to the state
            self_state[mobile_api]["patient_code"] = patient_code
            logger.debug(f"Patient code saved to self_state: {self_state}")

            # Update nationality for self-users
            if state.get("nationality"):
                try:
                    update_payload = {
                        "mobile_api": mobile_api,
                        "nationality": state["nationality"].strip(),
                    }
                    update_response = requests.put(update_nationality_api, json=update_payload)
                    if update_response.status_code == 200:
                        logger.info(f"Nationality updated successfully to {state['nationality']} for {mobile_api}")
                    else:
                        logger.error(f"Failed to update nationality for {mobile_api}. Status Code: {update_response.status_code}")
                except Exception as e:
                    logger.error(f"Error updating nationality for {mobile_api}: {e}")

            del user_registration_state[mobile_api]

            # Check if the patient has an address
            address_payload = {"Username": mobile_api}
            address_response = requests.post(get_user_address_api, json=address_payload)  # Use POST as per request format

            if address_response.status_code == 200:
                address_data = address_response.json()
                user_message_data = address_data.get("Message", [{}])

                if isinstance(user_message_data, list) and len(user_message_data) > 0:
                    user_address_list = user_message_data[0].get("User_Address", [])

                    if isinstance(user_address_list, list) and len(user_address_list) > 0:
                        logger.info(f"Address found for {mobile_api}, proceeding to existing address flow.")
                        return existing_user_address(mobile_api, mobile_twilio, message="")

            # If no address exists, prompt the user to add a new address
            logger.info(f"No address found for {mobile_api}, proceeding to add new address flow.")
            return add_new_address(mobile_api, mobile_twilio)

        else:
            logger.error("Patient Code not found in the response message.")
            send_whatsapp_message(mobile_twilio, body="An error occurred. Try again later.")
            return {"status": "error", "message": "Patient code not found."}

    # Handle any other unexpected API response or error
    else:
        logger.error(f"Unexpected error or failure during patient registration: {api_response}")
        send_whatsapp_message(mobile_twilio, body="An error occurred. Try again later.")
        return {"status": "error", "message": "Unknown error occurred."}

# existing/add_pt_existing.py

import requests
from config import load_config

from twilio.rest import Client
from booking.other_booking import add_patient_flow_others


from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message, format_mobile_for_twilio

from helper_functions.fetch_userdetails import fetch_user_details_from_api
from helper_functions.add_patient_api import add_patient_to_api
from state.state_manager import user_registration_state, self_state
config = load_config()

# Load Twilio configuration

account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']

# External api configs
add_patient_api = config['add_patient']
get_user_address_api = config['get_user_address_api']


# Twilio SID
relationship_sid = config['relationship_sid']
nationality_sid = config['nationality_sid']
someone_else_relationship = config['someone_else_relationship']
patient_nationality_someone = config['patient_nationality_someone']
someone_else_gender = config['someone_else_gender']

# Initiate Twilio Client
client = Client(account_sid, auth_token)

# Db apis
check_nationality_api = config['check_nationality_api']
save_user_details_api = config['save_user_details_api']
update_nationality_api = config['update_nationality_api']
check_surname_api = config['check_surname_api']






def add_patient_flow_self(mobile_api: str, mobile_twilio: str, message: str = None) -> dict:

    # Initialize the user registration state

    # Step 1: Initialize state management
    # Create a new state entry if user doesn't exist in registration state
    if mobile_api not in user_registration_state:
        user_registration_state[mobile_api] = {
            "action": "booking_person",
            "step": "ask_booking_person"
        }

    # Get current state for the user
    state = user_registration_state.get(mobile_api, {"step": "ask_booking_person"})
    logger.debug(f"Current state for {mobile_api}: {state}")

    # Step 2: Handle Booking Person Selection Flow
    if state["step"] == "ask_booking_person":

        # 2.1: Initial booking person selection SID
        if message is None:
            # Send Twilio template asking if booking for Self or Someone else
            try:
                to = format_mobile_for_twilio(mobile_twilio)
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid=relationship_sid
                )
                logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
                return {"status": "success", "message_sid": message.sid}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}

        # 2.2: Check booking person selection if it is self or someone else
        booking_person = message.strip()

        if booking_person.lower() == "someone else":
            logger.info(f"User selected {booking_person} for {mobile_api}.")            

            #  Ensure action is updated correctly
            user_registration_state[mobile_api]["action"] = "other_booking"  
            user_registration_state[mobile_api]["step"] = "show_patient_list"

            logger.debug(f"Updated state for {mobile_api}: {user_registration_state[mobile_api]}")
            
            return add_patient_flow_others(mobile_api, mobile_twilio, message)





        elif booking_person.lower() == "self":  # Handle Self booking case

            user_details = fetch_user_details_from_api(mobile_api)

            # 3.1: Validate fetched user details
            if not user_details:
                response_message = "Failed to fetch your details. Please try again later."
                send_whatsapp_message(mobile_twilio, body=response_message)
                logger.error(f"Failed to fetch user details for {mobile_api}")
                return {"status": "error", "message": response_message}

            # 3.2: Get the user name 
            # Split and format full name into first name and surname
            full_name = f"{user_details.get('first_name', '').strip()} {user_details.get('surname', '').strip()}".strip()
            name_parts = full_name.split(" ", 1)
            user_details["first_name"] = name_parts[0]
            user_details["surname"] = name_parts[1] if len(name_parts) > 1 else None


            # Step 4: Surname Validation Process
            # 4.1: Check if surname exists for registered user in API response
            if user_details.get("surname"):
                logger.debug(f"Surname already found in API response: {user_details['surname']}")
                state.update(user_details)
            else:
                # 4.2: If surname missing, check MongoDB
                logger.warning(f"Surname missing in API response for {mobile_api}. Checking MongoDB...")
                try:
                    api_payload = {"mobile_api": mobile_api}
                    response = requests.post(check_surname_api, json=api_payload)
                    logger.debug(f"🔄 Sent request to check_surname_api for {mobile_api}. Response Status: {response.status_code}")

                    # 4.3: If Surname found in MongoDB, update state
                    if response.status_code == 200:
                        api_response = response.json()
                        saved_surname = api_response.get("surname")

                        if saved_surname:
                            user_details["surname"] = saved_surname
                            logger.debug(f"Surname found in MongoDB for {mobile_api}: {saved_surname}")
                            state.update(user_details)
                        else:
                            # 4.4: Ask user for surname if not found anywhere both in Mongo db and API response
                            state.update(user_details)
                            state["step"] = "ask_surname_self" # Update state to ask for surname
                            send_whatsapp_message(mobile_twilio, body="Please provide your surname:")
                            logger.debug(f"Surname missing for {mobile_api}. Asking user...")
                            return {"status": "success", "message": "Requesting surname"}

                    else:
                        logger.error(f"Failed to check surname in MongoDB. Status Code: {response.status_code}, Response: {response.text}")
                        send_whatsapp_message(mobile_twilio, body="An error occurred while processing your request. Please try again later.")
                        return {"status": "error", "message": "Failed to check surname via API"}

                except requests.RequestException as e:
                    logger.error(f"Request to check surname API failed: {e}")
                    send_whatsapp_message(mobile_twilio, body="An error occurred while processing your request. Please try again later.")
                    return {"status": "error", "message": "API request failed"}


            # Step 5: Update state with complete user details
            state.update(user_details)
            logger.debug(f"Final state updated for {mobile_api}: {state}")

            # Step 6: Nationality Check Process
            # 6.1: Query MongoDB for existing nationality
            try:
                api_payload = {"mobile_api": mobile_api}
                logger.info(f"Checking nationality via API: {api_payload}")
                
                response = requests.post(check_nationality_api, json=api_payload)

                # 6.2: Process nationality check response
                if response.status_code == 200:
                    api_response = response.json()
                    saved_nationality = api_response.get("nationality")
                    if saved_nationality:
                        state["nationality"] = saved_nationality
                        logger.info(f"Nationality found for {mobile_api}: {saved_nationality}")
                        return add_patient_to_api(mobile_api, mobile_twilio, state)
                    else:
                        logger.info(f"No nationality found for {mobile_api}. Proceeding to ask.")
                else:
                    logger.error(f"Failed to check nationality via API. Status Code: {response.status_code}, Response: {response.text}")
                    send_whatsapp_message(mobile_twilio, body="An error occurred while processing your request. Please try again later.")
                    return {"status": "error", "message": "Failed to check nationality via API"}

            except requests.RequestException as e:
                logger.error(f"Request to check nationality API failed: {e}")
                send_whatsapp_message(mobile_twilio, body="An error occurred while processing your request. Please try again later.")
                return {"status": "error", "message": "API request failed"}

            # Step 7: Save User Details to MongoDB
            try:
                api_payload = {
                    "mobile_api": mobile_api,
                    "first_name": state.get("first_name"),
                    "surname": state.get("surname"),
                    "gender": state.get("gender"),
                    "dob": state.get("dob"),
                    "mobile": state.get("mobile"),
                    "nationality": state.get("nationality") or ""
                }

                logger.info(f"Sending user details to save API: {api_payload}")
                    
                response = requests.post(save_user_details_api, json=api_payload)

                # 7.1: Process save response
                if response.status_code == 200:
                    api_response = response.json()
                    if api_response.get("message") == "User details saved successfully":
                        logger.info(f"User details saved successfully via API for {mobile_api}")
                    elif api_response.get("message") == "User already exists":
                        logger.info(f"User already exists in MongoDB for {mobile_api}")
                    else:
                        logger.warning(f"Unexpected response from save API: {api_response}")
                else:
                    logger.error(f"Failed to save user details via API. Status Code: {response.status_code}, Response: {response.text}")
                    send_whatsapp_message(mobile_twilio, body="An error occurred while saving your details. Please try again later.")
                    return {"status": "error", "message": "Failed to save details via API"}

            except requests.RequestException as e:
                logger.error(f"Request to save user details API failed: {e}")
                send_whatsapp_message(mobile_twilio, body="An error occurred while saving your details. Please try again later.")
                return {"status": "error", "message": "API request failed"}

            # Step 8: Proceed to nationality collection
            state["step"] = "ask_nationality"
            logger.debug(f"State updated to: {state}")

            # 8.1: Send nationality question template
            try:
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=mobile_twilio,
                    content_sid=nationality_sid
                )
                logger.info(f"Quick reply template sent to {mobile_twilio} with SID: {message.sid}")
                return {"status": "success", "message_sid": message.sid}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}

    # Step 9: Handle Surname Collection Flow
    elif state["step"] == "ask_surname_self":
        surname = message.strip()
        
        if not surname:
            send_whatsapp_message(mobile_twilio, body="Surname cannot be empty. Please provide your surname:")
            logger.warning(" Empty surname provided.")
            return {"status": "error", "message": "Invalid surname"}

        #  Save the surname and update the step
        state["surname"] = surname
        state["step"] = "ask_nationality"
        user_registration_state[mobile_api] = state  #  Persist updated state
        logger.debug(f" Surname saved for {mobile_api}. Moving to ask_nationality. Updated state: {state}")

        #  Call MongoDB Save API
        try:
            api_payload = {
                "mobile_api": mobile_api,
                "first_name": state.get("first_name"),
                "surname": state.get("surname"),
                "gender": state.get("gender"),
                "dob": state.get("dob"),
                "mobile": state.get("mobile"),
                "nationality": state.get("nationality", "")  # Default to empty string if not available
            }

            logger.info(f" Sending user details to MongoDB save API: {api_payload}")
            response = requests.post(save_user_details_api, json=api_payload)

            if response.status_code == 200:
                api_response = response.json()
                if api_response.get("message") == "User details saved successfully":
                    logger.info(f" User details saved successfully in MongoDB for {mobile_api}")
                elif api_response.get("message") == "User already exists":
                    logger.info(f" User already exists in MongoDB for {mobile_api}")
                else:
                    logger.warning(f" Unexpected response from save API: {api_response}")
            else:
                logger.error(f" Failed to save user details in MongoDB. Status Code: {response.status_code}, Response: {response.text}")
                send_whatsapp_message(mobile_twilio, body="An error occurred while saving your details. Please try again later.")
                return {"status": "error", "message": "Failed to save details via API"}

        except requests.RequestException as e:
            logger.error(f" Request to save user details API failed: {e}")
            send_whatsapp_message(mobile_twilio, body="An error occurred while saving your details. Please try again later.")
            return {"status": "error", "message": "API request failed"}

        #  Now ask for nationality only once
        try:
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=mobile_twilio,
                content_sid=nationality_sid
            )
            logger.info(f" Quick reply template sent to {mobile_twilio} for nationality. SID: {message.sid}")
            return {"status": "success", "message_sid": message.sid}
        except Exception as e:
            logger.error(f" Failed to send quick reply template to {mobile_twilio}: {e}")
            return {"status": "error", "error": str(e)}




    # Step 10: Handle Nationality Collection Flow
    elif state["step"] == "ask_nationality":
        nationality = message.strip().lower()

        if nationality == "yes":
            state["nationality"] = "Saudi"

            # Save nationality and update MongoDB
            user_registration_state[mobile_api] = state  # Ensure nationality is stored

            try:
                api_payload = {
                    "mobile_api": mobile_api,
                    "first_name": state.get("first_name"),
                    "surname": state.get("surname"),
                    "gender": state.get("gender"),
                    "dob": state.get("dob"),
                    "mobile": state.get("mobile"),
                    "nationality": state["nationality"],  # Ensure nationality is included
                }
                response = requests.post(save_user_details_api, json=api_payload)

                if response.status_code == 200:
                    logger.info(f"Nationality successfully saved for {mobile_api}")
                else:
                    logger.error(f"Failed to save nationality for {mobile_api}. API response: {response.text}")

            except requests.RequestException as e:
                logger.error(f"Error saving nationality to database: {e}")
                send_whatsapp_message(mobile_twilio, body="An error occurred while saving your nationality. Please try again later.")
                return {"status": "error", "message": "Nationality update failed"}

            return add_patient_to_api(mobile_api, mobile_twilio, state)

        elif nationality == "no":
            state["step"] = "ask_custom_nationality"
            send_whatsapp_message(mobile_twilio, body="Please specify your nationality:")
            return {"status": "success", "message": "Requesting custom nationality"}

        else:
            # If the user types something other than Yes or No, send the quick reply template again
            try:
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=mobile_twilio,
                    content_sid=nationality_sid,
                    
                )
                logger.info(f"Quick reply template sent to {mobile_twilio} with SID: {message.sid}")
                return {"status": "success", "message_sid": message.sid}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}

    # Step 11: Handle Custom Nationality Collection
    elif state["step"] == "ask_custom_nationality":
        # Validate and process custom nationality
        custom_nationality = message.strip().title()

        if not custom_nationality.isalpha():
            send_whatsapp_message(mobile_twilio, body="Invalid nationality. Please enter a valid nationality:")
            return {"status": "error", "message": "Invalid nationality"}

        state["nationality"] = custom_nationality

        # Save custom nationality before proceeding
        user_registration_state[mobile_api] = state  # Ensure nationality is stored

        try:
            api_payload = {
                "mobile_api": mobile_api,
                "first_name": state.get("first_name"),
                "surname": state.get("surname"),
                "gender": state.get("gender"),
                "dob": state.get("dob"),
                "mobile": state.get("mobile"),
                "nationality": state["nationality"],  # Ensure nationality is included
            }
            response = requests.post(save_user_details_api, json=api_payload)

            if response.status_code == 200:
                logger.info(f"Custom nationality successfully saved for {mobile_api}")
            else:
                logger.error(f"Failed to save custom nationality for {mobile_api}. API response: {response.text}")

        except requests.RequestException as e:
            logger.error(f"Error saving custom nationality to database: {e}")
            send_whatsapp_message(mobile_twilio, body="An error occurred while saving your nationality. Please try again later.")
            return {"status": "error", "message": "Nationality update failed"}

        return add_patient_to_api(mobile_api, mobile_twilio, state)

    





   

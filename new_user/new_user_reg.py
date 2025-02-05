# new_user/new_user_reg.py

import requests
from datetime import datetime
from config import load_config
from state.state_manager import user_registration_state
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message,format_mobile_for_twilio
from existing_user.existing_user import handle_user_interaction
from twilio.rest import Client

config = load_config()
user_view_api = config['user_view']
user_registration_api = config['user_registration']
account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']

# Twilio SID
gender_new_user = config['gender_new_user']
# Initiate Twilio Client
client = Client(account_sid, auth_token)


def handle_greeting(mobile_api: str, mobile_twilio: str) -> dict:
    """
    Handles user greeting and checks registration status.
    Redirects existing users to existing_user.py and starts registration for new users.
    """
    api_payload = {"Username": mobile_api}

    # Reset user state to restart
    if mobile_api in user_registration_state:
        logger.info(f"Resetting state for user: {mobile_api}.")
        del user_registration_state[mobile_api]

    try:
        logger.info(f"Checking user registration status for {mobile_api}.")
        response = requests.post(user_view_api, json=api_payload)

        # If user is found, redirect to existing_user.py
        if response.status_code == 200 and response.json().get("SuccessFlag") == "true":
            logger.info(f"User {mobile_api} found. Redirecting to existing_user.py.")
            return handle_user_interaction(mobile_api, mobile_twilio)

        # If user is not found, start the registration flow
        logger.info(f"User not found for {mobile_api}. Triggering User Registration flow.")
        user_registration_state[mobile_api] = {"action": "user_registration", "step": "ask_name"}
        response_message = (
            "Hi! Welcome to Sukraa Labs!👋\n\n"
            "It looks like you’re not registered with us🤔\n"
            "Kindly enter your name to register."
        )
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}

    except requests.RequestException as e:
        logger.error(f"Failed to connect to User_View API: {e}")
        response_message = "We are having trouble connecting to the server. Please try again later."
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "error", "message": response_message}




# Handle User registration
def handle_user_registration_flow(mobile_api: str, mobile_twilio: str, message: str) -> dict:
    """
    Handles the multi-step flow for user registration.
    Automatically uses the user's WhatsApp number for Username and Mobile_No.
    """
    state = user_registration_state[mobile_api]

    
    # Step 1: Ask for Full Name
    if state["step"] == "ask_name":
        full_name = message.strip()

        # Normalize the name: Handle dots, extra spaces, and ensure consistent capitalization
        full_name = full_name.replace('.', '. ').replace('  ', ' ').strip()
        full_name = ' '.join(part.capitalize() for part in full_name.split())  # Capitalize each part

        # Split the name into parts and remove invalid placeholders like "None"
        name_parts = [part for part in full_name.split() if part.lower() != "none"]

        # Validate that at least two parts are provided
        if len(name_parts) < 2:
            response_message = "Please enter your full name with at least two parts (e.g., John Doe or Jane A.):"
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

        # Assign name parts based on the number of parts provided
        state["first_name"] = name_parts[0].strip('. ')
        if len(name_parts) == 2:  # If only first and last names are provided
            state["middle_name"] = ""
            state["surname"] = name_parts[1].strip('. ')
        elif len(name_parts) == 3:  # If first, middle, and last names are provided
            state["middle_name"] = name_parts[1].strip('. ')
            state["surname"] = name_parts[2].strip('. ')
        else:  # If more than three parts, combine the rest into the surname
            state["middle_name"] = name_parts[1].strip('. ')
            state["surname"] = ' '.join(name_parts[2:]).strip('. ')

        # Ensure the state is updated with proper name parts
        logger.info(f"Parsed Name - First Name: {state['first_name']}, Middle Name: {state['middle_name']}, Surname: {state['surname']}")

        # Update state and prompt for the next step
        state["step"] = "ask_gender"
        try:

            # Format the mobile number for Twilio
            to = format_mobile_for_twilio(mobile_twilio)


            # Send the quick reply template using content SID
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=gender_new_user
            )
            logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
            return {"status": "success", "message_sid": message.sid}
        except ValueError as ve:
            logger.error(f"Invalid mobile number provided: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
            return {"status": "error", "error": str(e)}



    # Step 2: Ask for Gender
    elif state["step"] == "ask_gender":
        if message.upper() not in ["MALE", "FEMALE", "OTHER"]:
            try:

                # Format the mobile number for Twilio
                to = format_mobile_for_twilio(mobile_twilio)


                # Send the quick reply template using content SID
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid=gender_new_user
                )
                logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
                return {"status": "success", "message_sid": message.sid}
            except ValueError as ve:
                logger.error(f"Invalid mobile number provided: {ve}")
                return {"status": "error", "error": str(ve)}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}
            
        gender_replacement = (
            message.replace("MALE", "M")
                .replace("FEMALE", "F")
                .replace("OTHER", "O")
        )
        state["gender"] = gender_replacement


        state["step"] = "ask_dob"
        response_message = "Great! Now, please enter your Date of Birth (DD/MM/YYYY):"
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}


    # Step 3: Ask for Date of Birth
    elif state["step"] == "ask_dob":
        try:

            dob = message.strip()

            # Check if the input is empty
            if not dob:
                raise ValueError("Input is empty")

            # Normalize the date format by replacing '-' with '/'
            normalized_dob = dob.replace("-", "/")

            # Parse the visit date in DD/MM/YYYY format
            dob_date = datetime.strptime(normalized_dob, "%d/%m/%Y").date()

            # Ensure the date is not in the future
            if dob_date > datetime.today().date():
                raise ValueError("Date cannot be in the future")

            # Validate realistic age (e.g., not older than 150 years)
            age = datetime.today().year - dob_date.year - (
                (datetime.today().month, datetime.today().day) < (dob_date.month, dob_date.day)
                
            )
            if age > 150:
                raise ValueError("Unrealistic age derived from the DOB")

            # If all validations pass, update the state with formatted DOB
            state["dob"] = dob_date.strftime("%Y/%m/%d")  # Store as YYYY/MM/DD

            state["step"] = "finalize_registration"

            # Finalize registration and call the User Registration API
            payload = {
                "Name": f"{state['first_name']} {state['surname']}",
                "UserName": mobile_api,  # Automatically taken from WhatsApp number
                "Gender": state["gender"],
                "DOB": state["dob"],
                "Mobile_No": mobile_api  # Automatically taken from WhatsApp number
            }
            logger.info(f"Submitting user registration payload: {payload}")

            # Make API call to User_Registration
            response = requests.post(user_registration_api, json=payload)

            if response.status_code == 200 and response.json().get("SuccessFlag") == "true":
                response_message = "Registration successful!\n"
                send_whatsapp_message(mobile_twilio, body=response_message)
                del user_registration_state[mobile_api]  # Clear the state
                logger.info(f"User registration successful for {mobile_api}")
                return {"status": "success", "message": response_message}
            else:
                response_message = "Registration failed. Please try again later."
                logger.error(f"User registration failed: {response.text}")
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}

        except ValueError as e:
            # Handle invalid DOB format or unrealistic age
            response_message = (
                "Please enter your Date of Birth in DD/MM/YYYY format "
            )
            logger.warning(f"DOB validation failed: {e}")
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

        except requests.RequestException as e:
            # Handle API request failures
            logger.error(f"Error during user registration: {e}")
            response_message = "An error occurred while completing registration. Please try again later."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

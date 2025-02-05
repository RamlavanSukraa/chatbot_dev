# booking/add_family.py


from config import load_config
from datetime import datetime, date

from twilio.rest import Client

from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message, format_mobile_for_twilio
from helper_functions.add_patient_api import add_patient_to_api
from state.state_manager import user_registration_state


config = load_config()

# External api configs
add_patient_api = config['add_patient']
update_nationality_api = config['update_nationality_api']
booking_api_presc = config['booking_presc_api']
booking_list = config['booking_list']

# Load Twilio configuration
account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']

# Twilio SID
someone_else_relationship = config['someone_else_relationship']
patient_nationality_someone = config['patient_nationality_someone']
someone_else_gender = config['someone_else_gender']


# Initiate Twilio Client
client = Client(account_sid, auth_token)

def add_family_member(mobile_api: str, mobile_twilio: str, message: str = None) -> dict:

    if mobile_api not in user_registration_state:
        user_registration_state[mobile_api] = {
            "action": "family_member_booking",
            "step":"ask_relationship"
        }
    state = user_registration_state[mobile_api]
    logger.debug(f"Current state for {mobile_api}: {state}")

    

    # Step 3: Handle Relationship Selection
    if state["step"] == "ask_relationship":
        relationship = message.strip().lower()


        # If user chooses "Someone else", show relationship options
        if relationship in ["someone else", "someone"]:
            logger.info(f"Sending Relationship Quick Reply for {mobile_api}")

            try:
                sid_message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=mobile_twilio,
                    content_sid=someone_else_relationship  
                )
                logger.info(f"Relationship selection template sent to {mobile_twilio} with SID: {sid_message.sid}")
                return {"status": "success", "message_sid": sid_message.sid}
            except Exception as e:
                logger.error(f" Failed to send relationship options to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}
        


        relationship_mapping = {
            "1": "003", # Mother
            "2": "004", # Father
            "3": "006", # Wife
            "4": "001", # Brother
            "5": "002", # Sister
            
        }


        if relationship not in relationship_mapping:
            logger.error(f" Invalid relationship selection: {relationship}")

            # Resend the relationship options
            try:
                sid_message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=mobile_twilio,
                    content_sid=someone_else_relationship  
                )
                logger.info(f"Relationship selection template sent to {mobile_twilio} with SID: {sid_message.sid}")
                return {"status": "success", "message_sid": sid_message.sid}
            except Exception as e:
                logger.error(f" Failed to send relationship options to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}

        
        state["relation_code"] = relationship_mapping[relationship]
        state["step"] = "ask_other_person_name"
        state = user_registration_state[mobile_api]

        # Log the state before and after updating `user_registration_state`
        logger.debug(f"Before saving, state for {mobile_api}: {state}")

        #  Save the updated state
        state = user_registration_state[mobile_api]

        logger.debug(f"Current state for {mobile_api}: {user_registration_state[mobile_api]}")
        send_whatsapp_message(mobile_twilio, body="Please enter their full name (e.g., John Doe):")
        return {"status": "success", "message": "Requesting Name"}





    # Step : Handle Name Input
    elif state["step"] == "ask_other_person_name":
        full_name = message.strip()

        if not full_name or len(full_name.split()) < 2:
            send_whatsapp_message(mobile_twilio, body="Please enter a valid full name with at least two parts (e.g., John Doe):")
            logger.warning(f"Invalid full name input: {message}")
            return {"status": "error", "message": "Invalid full name"}

        full_name = full_name.replace('.', '. ').replace('  ', ' ').strip()

        name_parts = []  # Create an empty list to store name parts
        # Split the full name into words
        for part in full_name.split():
            if part.lower() != "none":  # Ignore the word "none"
                name_parts.append(part.capitalize())  # Capitalize the word and add it to the list



        state["first_name"] = name_parts[0]

        if len(name_parts) == 2:
            state["middle_name"] = ""
            state["surname"] = name_parts[1]
        elif len(name_parts) >= 3:
            state["middle_name"] = name_parts[1]
            state["surname"] = ' '.join(name_parts[2:])


        state["step"] = "ask_other_person_nationality"
        logger.debug(f"State updated to: {state}")

        try:
            to = format_mobile_for_twilio(mobile_twilio)

            message = client.messages.create(
                from_= twilio_whatsapp_number,
                to = to,
                content_sid = patient_nationality_someone
            )
            logger.info(f"Quick reply sent to {to}")
            return {"status":"success", "message_sid":message.sid}
        except ValueError as ve:
            logger.error(f"Invalid number provided: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to send qucik reply template to {mobile_twilio}: {e}")
            return {"status":"error", "error": {e}}





    # Step : Handle Nationality Selection

    elif state["step"] == "ask_other_person_nationality":
        nationality = message.strip()


        if nationality == "Yes":
            state["nationality"] = "Saudi"
            state["step"] = "ask_other_person_dob"
            logger.debug(f"State updated to: {state}")
            send_whatsapp_message(mobile_twilio, body="Please enter their date of birth (DD/MM/YYYY):")
            return {"status": "success", "message": "Requesting DOB"}

        elif nationality == "No":
            state["step"] = "ask_other_person_custom_nationality"
            logger.debug(f"State updated to: {state}")
            send_whatsapp_message(mobile_twilio, body="Please specify their nationality:")
            return {"status": "success", "message": "Requesting custom nationality"}

        else:

            logger.warning(f"Invalid nationality input: {message}")
            return {"status": "error", "message": "Invalid nationality"}
        




    # Step 6: Handle Custom Nationality Input
    elif state["step"] == "ask_other_person_custom_nationality":
        custom_nationality = message.strip()
        if not custom_nationality.isalpha():
            send_whatsapp_message(mobile_twilio, body="Please specify their nationality:")
            logger.warning(f"Invalid custom nationality input: {message}")
            return {"status": "error", "message": "Invalid custom nationality"}
        state["nationality"] = custom_nationality

        state["step"] = "ask_other_person_dob"
        logger.debug(f"State updated to: {state}")
        send_whatsapp_message(mobile_twilio, body="Please enter their date of birth (DD/MM/YYYY):")
        return {"status": "success", "message": "Requesting DOB"}






    # Step 7: Handle Date of Birth Input
    elif state["step"] == "ask_other_person_dob":
        dob = message.strip()

        try:
            normalized_dob = dob.replace("-", "/")
            logger.debug(f"DOB normalized: {normalized_dob}")
            parsed_dob = datetime.strptime(normalized_dob, "%d/%m/%Y").date()

            if parsed_dob > date.today():
                send_whatsapp_message(mobile_twilio, body="The date of birth cannot be in the future. Please provide a valid DOB (DD/MM/YYYY):")
                logger.warning(f"DOB is in the future: {dob}")
                return {"status": "error", "message": "DOB is in the future"}

            age = date.today().year - parsed_dob.year - ((date.today().month, date.today().day) < (parsed_dob.month, parsed_dob.day))


            if age < 0 or age > 150:
                send_whatsapp_message(mobile_twilio, body="The age derived from the DOB is not realistic. Please provide a valid DOB (DD/MM/YYYY):")
                logger.warning(f"Unrealistic DOB age ({age} years): {dob}")
                return {"status": "error", "message": "Unrealistic DOB age"}


            formatted_dob = parsed_dob.strftime("%Y/%m/%d")
            state["dob"] = formatted_dob


            state["step"] = "ask_other_person_gender"
            logger.debug(f"State updated to: {state}")

            try:
                to = format_mobile_for_twilio(mobile_twilio)

                message = client.messages.create(
                    from_ = twilio_whatsapp_number,
                    to = to,
                    content_sid=someone_else_gender
                )
                logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
                return {"status": "success", "message_sid": message.sid}
            except ValueError as ve:
                logger.error(f"Invalid mobile number provided: {ve}")
                return {"status": "error", "error": str(ve)}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}

        except ValueError:
            send_whatsapp_message(mobile_twilio, body="Invalid DOB format. Please provide in DD/MM/YYYY format:")
            logger.warning(f"Invalid DOB format or value: {dob}")
            return {"status": "error", "message": "Invalid DOB format"}
        



    # Step 8: Handle Gender Selection
    elif state["step"] == "ask_other_person_gender":
        gender = message.lower().strip()
        if gender not in ["male", "female", "other"]:
            try:
                to = format_mobile_for_twilio(mobile_twilio)

                message = client.messages.create(
                    from_ = twilio_whatsapp_number,
                    to = to,
                    content_sid=someone_else_gender
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
            message.replace("male", "M")
                .replace("female", "F")
                .replace("other", "O")
        )
        state["gender"] = gender_replacement
        state["step"] = "ask_other_person_mobile"
        logger.debug(f"State updated to: {state}")
        send_whatsapp_message(mobile_twilio, body="Please enter their 10-digit mobile number:")
        return {"status": "success", "message": "Requesting mobile number"}



    # Step 9: Handle Mobile Number Input
    elif state["step"] == "ask_other_person_mobile":
        mobile_no = message.strip()
        if not mobile_no.isdigit() or len(mobile_no) != 10:
            send_whatsapp_message(mobile_twilio, body="Invalid mobile number. Please enter a valid 10-digit mobile number:")
            logger.warning(f"Invalid mobile number input: {message}")
            return {"status": "error", "message": "Invalid mobile number"}
        state["mobile"] = mobile_no
        return add_patient_to_api(mobile_api, mobile_twilio, state)

    logger.error(f"Unhandled step in state for {mobile_api}: {state}")
    return {"status": "error", "message": "Unhandled step"}







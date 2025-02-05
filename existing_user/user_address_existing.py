# existing/user_address_existing.py

from twilio.rest import Client
import requests
from config import load_config
from state.state_manager import user_registration_state
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message, format_mobile_for_twilio
from new_user.book_presc import booking_with_prescription
import json

# Load configuration
config = load_config()
get_user_address_api = config['get_user_address_api']
edit_user_address_api = config['edit_user_address_api']
account_sid = config['account_sid']
auth_token = config['auth_token']
twilio_whatsapp_number = config['phone_number']
existing_address = config['existing_address']  # Add your Twilio content SID for this template

# Initialize Twilio Client
client = Client(account_sid, auth_token)

# Twilio content sid
province_sid = config['province_sid']
user_address_confirmation = config['user_address_confirmation']

def existing_user_address(mobile_api: str, mobile_twilio: str, message: str = None) -> dict:
    """
    Handles fetching, presenting, and editing the user address using Twilio templates,
    with a step-by-step input for Saudi addresses.
    """
    state = user_registration_state.get(mobile_api, {})

    # Step 1: Fetch and display existing address
    if state.get("step") is None:
        try:
            response = requests.post(get_user_address_api, json={"Username": mobile_api})
            response.raise_for_status()
            api_response = response.json()

            if api_response.get("SuccessFlag") == "True" and api_response.get("Code") == 200:
                user_address = api_response["Message"][0]["User_Address"][0]
                state.update({"action": "existing_address", "step": "confirm_or_edit", "address": user_address})
                user_registration_state[mobile_api] = state

                # Send Twilio template with the fetched address
                try:
                    full_address = user_address.get("Full_Address", "No address available.")
                    content_variables = {"1": full_address}

                    logger.debug(f"Content Variables: {content_variables}")

                    to = format_mobile_for_twilio(mobile_twilio)
                    message = client.messages.create(
                        from_=twilio_whatsapp_number,
                        to=to,
                        content_sid=existing_address,
                        content_variables=json.dumps(content_variables)
                    )
                    logger.info(f"Address confirmation template sent successfully. Message SID: {message.sid}")
                    return {"status": "success", "message_sid": message.sid}

                except Exception as e:
                    logger.error(f"Error sending address confirmation template: {e}")
                    return {"status": "error", "message": str(e)}

            else:
                logger.error(f"Failed to fetch address: {api_response.get('Message', 'Unknown error')}")
                response_message = "Unable to fetch your address. Please try again later."
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}

        except requests.RequestException as e:
            logger.error(f"Error fetching address for {mobile_api}: {e}")
            response_message = "Unable to fetch your address. Please try again later."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

    # Step 2: Handle user response (use or edit address)
    elif state["step"] == "confirm_or_edit":
        if message.strip().lower() == "yes":
            # Use the same address and proceed to booking
            return booking_with_prescription(mobile_api, mobile_twilio)

        elif message.strip().lower() == "no":
            # Start the step-by-step address flow
            state["step"] = "ask_door_apartment"
            user_registration_state[mobile_api] = state
            response_message = "Please enter your door number and apartment name (e.g., 12, Sunshine Apartment)."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "success", "message": response_message}

        else:
            # Re-prompt with the saved address
            try:
                full_address = state.get("address", {}).get("Full_Address", "No address available.")
                content_variables = {"1": full_address}

                logger.debug(f"Re-prompt Content Variables: {content_variables}")

                to = format_mobile_for_twilio(mobile_twilio)
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid=existing_address,
                    content_variables=json.dumps(content_variables)
                )
                logger.info(f"Re-prompt template sent successfully. Message SID: {message.sid}")
                return {
                    "status": "success",
                    "message_sid": message.sid,
                    "message": "Invalid response. Please reply 'Yes' to confirm the address or 'No' to edit it."
                }
            except Exception as e:
                logger.error(f"Error sending re-prompt address confirmation template: {e}")
                return {"status": "error", "message": str(e)}


    # Step 3: Ask for door number and apartment name
    elif state["step"] == "ask_door_apartment":
        state["door_apartment"] = message.strip()
        state["step"] = "ask_locality"
        user_registration_state[mobile_api] = state
        response_message = "Please enter your locality (e.g., Abha Street)."
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}

    # Step 4: Ask for locality
    elif state["step"] == "ask_locality":
        state["locality"] = message.strip()
        state["step"] = "ask_zip_code"
        user_registration_state[mobile_api] = state
        response_message = "Please enter your zip code (5 digits, e.g., 13525)."
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}

    # Step 5: Ask for zip code
    elif state["step"] == "ask_zip_code":
        if not message.strip().isdigit() or len(message.strip()) != 5:
            response_message = "Invalid zip code. Please enter a valid 5-digit zip code (e.g., 13525)."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

        state["zip_code"] = message.strip()
        state["step"] = "ask_province"
        user_registration_state[mobile_api] = state

        # Province SID
        try:
            # Format the mobile number for Twilio
            to = format_mobile_for_twilio(mobile_twilio)

            # Resend the quick reply template using content SID
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=province_sid
            )
            logger.info(f"Quick reply template re-sent to {to} with SID: {message.sid}")
            return {"status": "success", "message_sid": message.sid}
        except ValueError as ve:
            logger.error(f"Invalid mobile number provided: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to resend quick reply template to {mobile_twilio}: {e}")
            return {"status": "error", "error": str(e)}


    # Step 6: Ask for province/city
    elif state["step"] == "ask_province":
        province_mapping = {
            "1": "Riyadh",
            "2": "Jeddah",
            "3": "Dammam",
            "4": "Mecca",
            "5": "Medina",
        }
        province = province_mapping.get(message.strip())
        if not province:
            response_message = "Invalid choice. Please select a valid option (1-5)."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

        state["province"] = province
        state["country"] = "Saudi Arabia"
        user_registration_state[mobile_api] = state

        # Confirm the full address
        full_address = (
            f"{state['door_apartment']}, {state['locality']}, "
            f"{state['zip_code']}, {state['province']}, {state['country']}"
        )
        state["step"] = "confirm_address"
        user_registration_state[mobile_api] = state

        # address confirmation template
        try:
            # Format the mobile number for Twilio
            to = format_mobile_for_twilio(mobile_twilio)

            # Resend the quick reply template using Content SID
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid=user_address_confirmation
            )
            logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
        except ValueError as ve:
            logger.error(f"Invalid mobile number provided: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
            return {"status": "error", "error": str(e)}




    # Step 7: Save the address or restart
    elif state["step"] == "confirm_address":

        city_to_region_mapping = {
            "Riyadh": "Riyadh Region", 
            "Jeddah": "Makkah Region", 
            "Dammam": "Eastern Province",
            "Mecca": "Makkah Region",
            "Medina": "Madinah Region"  
        }


        # Handle user response
        if message.strip().lower() == "yes":
            # Prepare payload for Edit User Address API
            city = state["province"]
            region = city_to_region_mapping.get(city, city)
            payload = {
                "Username": mobile_api,
                "Address_Type": "01",
                "Street": state["door_apartment"],
                "Place": state["locality"],
                "City": city,
                "State":  region,
                "Country": state["country"],
                "Pincode": state["zip_code"],
                "Location": "Updated Location",
                "Landmark": "Updated Landmark",
                "Latitude": "14.025649",
                "Longitude": "79.125487",
            }

            try:
                response = requests.post(edit_user_address_api, json=payload)
                response.raise_for_status()
                api_response = response.json()

                if api_response.get("SuccessFlag") == "true" and api_response.get("Code") == 200:
                    response_message = "Your address has been saved successfully!"
                    send_whatsapp_message(mobile_twilio, body=response_message)
                    return booking_with_prescription(mobile_api, mobile_twilio)
                else:
                    raise ValueError("Failed to save address.")
                

            except Exception as e:
                logger.error(f"Error saving address: {e}")
                response_message = "Failed to save your address. Please try again later."
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}



        elif message.strip().lower() == "no":
            # Restart the address flow
            state["step"] = "ask_door_apartment"
            user_registration_state[mobile_api] = state
            response_message = "Let's restart. Please enter your door number and apartment name (e.g., 12, Sunshine Apartment)."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "success", "message": response_message}



        else:

            # address confirmation template
            try:
                # Format the mobile number for Twilio
                to = format_mobile_for_twilio(mobile_twilio)

                # Resend the quick reply template using Content SID
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid=user_address_confirmation
                )
                logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
            except ValueError as ve:
                logger.error(f"Invalid mobile number provided: {ve}")
                return {"status": "error", "error": str(ve)}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}



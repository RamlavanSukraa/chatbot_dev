# new_user/book_presc.py

from datetime import datetime, timedelta
import requests
from requests.auth import HTTPBasicAuth
from twilio.rest import Client
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from config import load_config
from utils.logger import app_logger as logger
from utils.messaging_utils import send_whatsapp_message, format_mobile_for_twilio
from state.state_manager import user_registration_state, relationship_state, self_state
from new_user.view_pt_det import fetch_patient_details
  
from helper_functions.service_booking import handle_patient_details, save_booking_to_db

config = load_config()

account_sid = config['account_sid']
auth_token = config['auth_token']
booking_api_presc = config['booking_presc_api']
booking_list = config['booking_list']

twilio_whatsapp_number = config['phone_number']


# Twilio Client
client = Client(account_sid, auth_token)

# Twilio Sid
booking_options_sid = config['booking_options_sid']
day_slot_sid = config['day_slot_sid']
morning_slot_sid = config['morning_slot_sid']
afternoon_slot_sid = config['afternoon_slot_sid']
evening_slot_sid = config['evening_slot_sid']





def booking_with_prescription(mobile_api: str, mobile_twilio: str, message: str = None, request_data: dict = None) -> dict:
    """
    Handles the Booking with Prescription flow, including initialization.
    """
    # Check if this is the initial call (no message/request_data)
    if message is None and request_data is None:
        # Initialize the flow with the first step
        user_registration_state[mobile_api] = {
            "action": "booking_with_prescription",
            "step": "ask_booking_type"
        }

        try:
            to = format_mobile_for_twilio(mobile_twilio)
            message = client.messages.create(
                from_=twilio_whatsapp_number,
                to=to,
                content_sid = booking_options_sid
            )

            logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
            return {"status": "success", "message": f"Hi {user_name}, your menu is sent.", "sid": message.sid}
        except ValueError as ve:
            logger.error(f"Invalid mobile number provided: {ve}")
            return {"status": "error", "error": str(ve)}
        except Exception as e:
            logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
            return {"status": "error", "error": str(e)}




    state = user_registration_state[mobile_api]
    logger.info(f"Handling booking with prescription for user: {mobile_api}. Current state: {state['step']}")



    # Step 1: Ask for Booking Type
    if state["step"] == "ask_booking_type":
        booking_type = message.strip().upper()
        if booking_type not in ["HOME COLLECTION", "WALK IN"]:
            logger.warning(f"Invalid booking type received for {mobile_api}: {message}")

            try:
                to = format_mobile_for_twilio(mobile_twilio)
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid = booking_options_sid
                )

                logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
                return {"status": "success", "message_sid": message.sid}
            except ValueError as ve:
                logger.error(f"Invalid mobile number provided: {ve}")
                return {"status": "error", "error": str(ve)}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}

        # Save the valid booking type to the state
        booking_type_replacement = (
            booking_type.replace("HOME COLLECTION", "H")
            .replace("WALK IN", "W")

        )
        
        state["booking_type"] = booking_type_replacement
        logger.debug(f"Booking type saved for {mobile_api}: {state['booking_type']}")

        state["step"] = "ask_visit_date"
        logger.info(f"Booking type saved for {mobile_api}: {booking_type}")

        response_message = "Please provide the visit date (DD/MM/YYYY):"
        send_whatsapp_message(mobile_twilio, body=response_message)
        return {"status": "success", "message": response_message}




    # Step 2: Ask for Visit Date
    elif state["step"] == "ask_visit_date":
        try:


            normalized_date = message.strip().replace('-', '/')

            # Parse the visit date in DD/MM/YYYY format (user input)
            visit_date = datetime.strptime(normalized_date, "%d/%m/%Y").date()

            # Check if the visit date is in the past
            if visit_date < datetime.utcnow().date():
                raise ValueError("Visit date cannot be in the past.")

            # Reformat visit date to YYYY/MM/DD for the API request
            state["visit_date"] = visit_date.strftime("%Y/%m/%d")
            state["step"] = "ask_visit_time"  # Transition to the next step


            state["step_detail"] = "choose_period"  
            logger.info(f"Visit date saved for {mobile_api}: {state['visit_date']}")
                # Inline logic to send quick reply template
            try:

                # Format the mobile number for Twilio
                to = format_mobile_for_twilio(mobile_twilio)

                # Send the quick reply template using content SID
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    to=to,
                    content_sid=day_slot_sid
                )
                logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
                return {"status": "success", "message_sid": message.sid}
            except ValueError as ve:
                logger.error(f"Invalid mobile number provided: {ve}")
                return {"status": "error", "error": str(ve)}
            except Exception as e:
                logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                return {"status": "error", "error": str(e)}


        except ValueError as e:
            # Handle invalid date format or past dates
            logger.warning(f"Invalid date format or past date received for {mobile_api}: {message} - {e}")
            response_message = (
                "Invalid date. Please provide the visit date in DD/MM/YYYY format and ensure it is not in the past."
            )
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}



    # Step 3: Ask Visit Time
    elif state["step"] == "ask_visit_time":
        try:
            logger.info(f"Validating visit time for user {mobile_api}")

            # Step 3.1: Prompt for time period selection
            if "step_detail" not in state:
                state["step_detail"] = "choose_period"
                # Inline logic to send quick reply template
                try:
                    # Format the mobile number for Twilio
                    to = format_mobile_for_twilio(mobile_twilio)

                    # Send the quick reply template using content SID
                    message = client.messages.create(
                        from_=twilio_whatsapp_number,
                        to=to,
                        content_sid=day_slot_sid
                    )
                    logger.info(f"Quick reply template sent to {to} with SID: {message.sid}")
                    return {"status": "success", "message_sid": message.sid}
                except ValueError as ve:
                    logger.error(f"Invalid mobile number provided: {ve}")
                    return {"status": "error", "error": str(ve)}
                except Exception as e:
                    logger.error(f"Failed to send quick reply template to {mobile_twilio}: {e}")
                    return {"status": "error", "error": str(e)}

            # Step 3.2: Display slots for the selected period using Twilio Content Builder
            elif state["step_detail"] == "choose_period":
                day_message = message.strip().lower()

                if day_message in ["morning", "afternoon", "evening"]:
                    state["selected_period"] = day_message
                    state["step_detail"] = "choose_slot"

                    # Use Twilio Content Builder CTA to display slots
                    if day_message == "morning":
                        content_sid = morning_slot_sid  # Morning slots Content SID
                    elif day_message == "afternoon":
                        content_sid = afternoon_slot_sid  # Afternoon slots Content SID
                    elif day_message == "evening":
                        content_sid = evening_slot_sid  # Evening slots Content SID

                    # Trigger Twilio Content Builder template
                    client.messages.create(
                        from_=twilio_whatsapp_number,
                        to=mobile_twilio,
                        content_sid=content_sid
                    )
                    logger.info(f"Slots sent via Twilio Content Builder for {day_message.capitalize()} period.")
                    return {"status": "success", "message": f"Slots sent for {day_message.capitalize()}."}

                else:
                    # Invalid period selection
                    response_message = "Invalid selection. Please reply with 'Morning', 'Afternoon', or 'Evening'."
                    send_whatsapp_message(mobile_twilio, body=response_message)
                    return {"status": "error", "message": response_message}

            # Step 3.3: Validate and save the selected slot
            elif state["step_detail"] == "choose_slot":

                try:
                    # Validate slot selection based on the slot text
                    selected_item_id = message.strip()  # The slot selected by the user (e.g., "2 PM to 4 PM")

                    # Slot mappings for each time period
                    slot_mappings = {
                        "morning": {
                            "1": "7 AM to 8 AM",
                            "2": "8 AM to 9 AM",
                            "3": "9 AM to 10 AM",
                            "4": "10 AM to 11 AM",
                            "5": "11 AM to 12 PM"
                        },
                        "afternoon": {
                            "1": "12 PM to 1 PM",
                            "2": "1 PM to 2 PM",
                            "3": "2 PM to 3 PM",
                            "4": "3 PM to 4 PM",
                            "5": "4 PM to 5 PM",
                            "6": "5 PM to 6 PM"
                        },
                        "evening": {
                            "1": "6 PM to 7 PM",
                            "2": "7 PM to 8 PM",
                            "3": "8 PM to 9 PM",
                            "4": "9 PM to 10 PM",
                            "5": "10 PM to 11 PM"
                        }
                    }

                    # Get slots for the selected period
                    selected_period = state.get("selected_period", "")
                    period_slots = slot_mappings.get(selected_period, {})  # Get the slot mapping for the selected period


                    # Map the Item ID to the actual slot name
                    mapped_slot = period_slots.get(selected_item_id, None)



                    if mapped_slot:
                        selected_slot = mapped_slot  # Use the mapped slot for further processing
                    else:
                        # Handle invalid Item ID
                        logger.error(f"Invalid Item ID received: '{selected_item_id}'. Mapping: {period_slots}")
                        response_message = "Invalid selection. Please choose a valid slot from the list."
                        send_whatsapp_message(mobile_twilio, body=response_message)
                        return {"status": "error", "message": response_message}


                    # Validate the selected slot with both date and time
                    visit_date_str = state.get("visit_date", "")  # Get the visit date from the state
                    visit_date = datetime.strptime(visit_date_str, "%Y/%m/%d").date()  # Convert visit date to a datetime object


                    # Define the India timezone
                    india_timezone = ZoneInfo("Asia/Kolkata")
                    current_time = datetime.now(india_timezone)
                    current_date = current_time.date()  # Extract current date


                    # Extract the start and end times of the slot
                    start_time_12hr = selected_slot.split(" ")[0] + " " + selected_slot.split(" ")[1]  # e.g., "9 AM"
                    end_time_12hr = selected_slot.split(" ")[3] + " " + selected_slot.split(" ")[4]  # e.g., "11 AM"


                    # Parse the start and end times as naive datetime objects
                    start_time_naive = datetime.strptime(start_time_12hr, "%I %p")  # E.g., "9 AM"
                    end_time_naive = datetime.strptime(end_time_12hr, "%I %p")  # E.g., "11 AM"


                    # Combine with visit date and localize to India timezone
                    start_time_ist = datetime.combine(visit_date, start_time_naive.time(), india_timezone)
                    end_time_ist = datetime.combine(visit_date, end_time_naive.time(), india_timezone)


                    # Debugging: Log the current date and slot times
                    logger.debug(f"Visit Date: {visit_date}, Current Date: {current_date}")
                    logger.debug(f"Slot Start Time (IST): {start_time_ist}, Slot End Time (IST): {end_time_ist}")


                    # Validate the slot based on the date and time
                    if visit_date == current_date:



                        # If visit date is today, validate based on the current time
                        if current_time < start_time_ist:
                            # Case 1: Slot is in the future; add 40 minutes to the slot's start time
                            visit_time_ist = (start_time_ist + timedelta(minutes=40)).strftime("%H:%M")
                            logger.info(f"Future slot selected for today. Visit time set to: {visit_time_ist}")
                        elif start_time_ist <= current_time <= end_time_ist:
                            # Case 2: Slot is near or within the current time; add 40 minutes to the current time
                            visit_time_ist = (current_time + timedelta(minutes=40)).strftime("%H:%M")
                            logger.info(f"Slot is within the valid time range. Visit time set to: {visit_time_ist}")
                        else:
                            # Case 3: Slot has already passed
                            logger.error(
                                f"Current time '{current_time.strftime('%I:%M %p')}' is outside the range of the selected slot: "
                                f"{selected_slot} ({start_time_ist.strftime('%I:%M %p')} - {end_time_ist.strftime('%I:%M %p')})."
                            )
                            response_message = (
                                f"The current time is '{current_time.strftime('%I:%M %p')}'. The selected slot '{selected_slot}' has passed. "
                                "Please choose a valid slot."
                            )
                            send_whatsapp_message(mobile_twilio, body=response_message)

                            # Resend the content SID for the period selection
                            state["step_detail"] = "choose_period"  # Reset the step to period selection

                            client.messages.create(
                                from_=twilio_whatsapp_number,
                                to=mobile_twilio,
                                content_sid=day_slot_sid  # Resend the day slot selection template
                            )
                            return {"status": "error", "message": response_message}


                    else:
                        # Case 4: Visit date is in the future
                        logger.info(f"Future date selected: {visit_date}. Using slot start time for calculation.")
                        visit_time_ist = (start_time_ist + timedelta(minutes=40)).strftime("%H:%M")


                    # Save the processed time in the state
                    state["visit_time"] = visit_time_ist  # Save the adjusted time in 24-hour format


                    # Check if patient_code is already in state
                    if "patient_code" in self_state.get(mobile_api, {}):
                        patient_id = self_state[mobile_api]["patient_code"]
                        logger.info(f"Patient code found in self_state for {mobile_api}: {patient_id}")


                        # Directly move to the prescription upload step
                        state["patient_code"] = patient_id
                        state["step"] = "upload_prescription"



                        response_message = "Please upload the prescription image."
                        send_whatsapp_message(mobile_twilio, body=response_message)
                        return {"status": "success", "message": response_message}

                    # If no patient_code, proceed to fetch and display the patient list
                    state["step"] = "ask_patient_code"
                    del state["step_detail"]

                    logger.info(f"Visit time validated and saved for user {mobile_api}: {state['visit_time']}")
                    logger.info(f"No patient code found. Fetching patient list for {mobile_api}")

                    # Fetch and display the patient list
                    patient_details_response = handle_patient_details(mobile_api, mobile_twilio)
                    if patient_details_response["status"] == "error":
                        response_message = "Sorry, no patient details found. Please try again later."
                        send_whatsapp_message(mobile_twilio, body=response_message)
                        return {"status": "error", "message": response_message}

                    return {"status": "success", "message": patient_details_response["message"]}




                except Exception as e:
                    # Handle unexpected errors
                    logger.error(f"Unexpected error during time validation for {mobile_api}: {e}")
                    response_message = "Something went wrong. Please try again."
                    send_whatsapp_message(mobile_twilio, body=response_message)
                    return {"status": "error", "message": response_message}


        except Exception as e:
            logger.error(f"Unexpected error during process for {mobile_api}: {e}")
            response_message = "Something went wrong. Please try again."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}



    # Step 4: Ask for Patient Code
    elif state["step"] == "ask_patient_code":
        try:


            selected_index = int(message.strip()) - 1  # Convert serial number to index
            patient_list = fetch_patient_details(mobile_api, mobile_twilio, user_registration_state[mobile_api]).get("Message", [])[0].get("Patient_Detail", [])


            if 0 <= selected_index < len(patient_list):
                selected_patient = patient_list[selected_index]
                patient_id = selected_patient.get("Pt_Code", "N/A")

                state["patient_code"] = patient_id
                state["step"] = "upload_prescription"
                logger.info(f"User selected patient with ID: {patient_id}")

                response_message = "Please upload the prescription image."
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "success", "message": response_message}
            
            else:
                response_message = "Invalid selection. Please reply with a valid serial number."
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}
            

        except (ValueError, KeyError) as e:
            logger.warning(f"Invalid input or patient selection error for {mobile_api}: {e}")
            response_message = "Invalid input. Please reply with a valid serial number (e.g., 1, 2, etc.)."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}




    
    # Step 5: Upload Prescription Image
    elif state["step"] == "upload_prescription":
        prescription_image = request_data.get("MediaUrl0", "")

        if not prescription_image:
            response_message = "No image detected. Please upload the prescription image."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}

        try:

            # Attempt to download the file
            try:
                image_response = requests.get(
                    prescription_image,
                    auth=HTTPBasicAuth(account_sid, auth_token)
                )
                image_response.raise_for_status()

                # Validate content type to ensure it's an image
                content_type = image_response.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    raise ValueError("Invalid file type uploaded. Expected an image.")

                # Extract and save file extension and content
                file_extension = content_type.split("/")[-1].lower()
                state["prescription_image_content"] = image_response.content
                state["file_extension"] = file_extension

                logger.info(f"Prescription image validated successfully for user {mobile_api}.")

            except requests.RequestException as e:
                logger.error(f"Error downloading prescription image for user {mobile_api}: {e}")
                response_message = "Failed to download the prescription image. Please try uploading again."
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}
            except ValueError as e:
                logger.warning(f"Invalid file type uploaded by user {mobile_api}: {e}")
                response_message = (
                    "Invalid file type detected. Please upload a valid prescription image (e.g., JPG, PNG)."
                )
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}

            # Prepare booking payload
            payload = {
                "UserName": mobile_api,
                "Booking_Type": state["booking_type"],
                "Firm_No": "01",
                "Visit_Date": state["visit_date"],
                "Visit_Time": state["visit_time"],
                "Pt_Code": state["patient_code"],
                "Address_Type": "01",
                "IsValidated": False,
                "Doctor_Code": "005006",
                "Client_Type": "P",
                "File_Extension1": state["file_extension"],
            }
            files = {
                "Prescription_File1": (
                    f"prescription.{state['file_extension']}",

                    state["prescription_image_content"],

                    f"image/{state['file_extension']}"
                )
            }

            # Submit booking to API
            try:
                response = requests.post(
                    booking_api_presc,
                    data=payload,
                    files=files
                )
                logger.info(f"Request URL: {booking_api_presc}")
                logger.info(f"Request Payload: {payload}")

                response.raise_for_status()
                api_response = response.json()

                logger.info(f"API Response Status Code: {response.status_code}")
                logger.info(f"API Response Body: {response.text}")

                if response.status_code == 200 and api_response.get("SuccessFlag") == "true":
                    # Extract Booking Number
                    booking_no = api_response.get("Message", [{}])[0].get("Booking_No", "N/A")[-6:]
                    response_message = (
                        f"Booking successful! Booking Number: {booking_no}.\n\n"
                        "You'll receive the invoice shortly.😊\n"
                            "Type *Hi* to start the conversation."
                    )
                    send_whatsapp_message(mobile_twilio, body=response_message)
                    logger.info(f"Booking successful for user {mobile_api}. Booking Number: {booking_no}")


                    # Fetch additional booking details from booking_list for backend saving
                    try:


                        fetch_payload = {"Username": mobile_api}
                        fetch_response = requests.post(booking_list, json=fetch_payload)
                        fetch_response.raise_for_status()

                        fetch_data = fetch_response.json()

                        if fetch_data.get("SuccessFlag") == "true" and fetch_data.get("Code") == 200:


                            # Save the booking_list response to MongoDB
                            save_fetched_result = save_booking_to_db(fetch_data)
                            if save_fetched_result["status"] == "success":
                                logger.info(f"Fetched and saved booking details for {mobile_api}")
                            else:
                                logger.error(f"Failed to save fetched booking details for {mobile_api}")
                        else:
                            logger.warning(f"Failed to fetch booking details for user {mobile_api}: {fetch_data}")



                    except requests.RequestException as e:
                        logger.error(f"Error while fetching booking details for user {mobile_api}: {e}")


                    # Clear user state
                    del user_registration_state[mobile_api]

                    # Clear `self_state` after booking is completed
                    if mobile_api in self_state:
                        del self_state[mobile_api]
                        logger.info(f"Cleared self_state for {mobile_api} after successful booking.")
                        
                    return {"status": "success", "message": response_message}

                else:
                    # Handle booking failure
                    error_desc = api_response.get("Message", [{}])[0].get("Description", "Booking failed.")
                    response_message = "Booking failed. Please type 'Hi' to restart the conversation."
                    logger.error(f"Booking API failed for user {mobile_api}. Error: {error_desc}")
                    send_whatsapp_message(mobile_twilio, body=response_message)
                    return {"status": "error", "message": response_message}



            except requests.RequestException as e:
                logger.error(f"Error connecting to Booking API for user {mobile_api}: {e}")
                response_message = "Unable to connect to the server. Please try again later."
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}
            except ValueError as e:
                logger.error(f"Invalid JSON response from Booking API for user {mobile_api}: {e}")
                response_message = "Unexpected server response. Please try again later."
                send_whatsapp_message(mobile_twilio, body=response_message)
                return {"status": "error", "message": response_message}



        except Exception as e:
            logger.error(f"Unexpected error during prescription upload for user {mobile_api}: {e}")
            response_message = "Something went wrong. Please try again later."
            send_whatsapp_message(mobile_twilio, body=response_message)
            return {"status": "error", "message": response_message}


    # Unexpected input or state
    logger.error(f"Unexpected state for user {mobile_api}: {state}")
    response_message = "Unexpected input. Please restart the process by typing 'Hi'."
    send_whatsapp_message(mobile_twilio, body=response_message)
    return {"status": "error", "message": response_message}

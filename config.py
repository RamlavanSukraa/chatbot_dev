# config.py

from utils.logger import app_logger as logger
import configparser
import os

def load_config():
    """
    Loads configuration from the config.ini file.
    """
    
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if os.path.exists(config_path):
        config.read(config_path)
    else:
        logger.error("Config file not found.")
        raise FileNotFoundError('Config file not found.')
    
    try:
        # Twilio configuration
        twilio_config = {
            "account_sid": config['twilio']['account_sid'],
            "auth_token": config['twilio']['auth_token'],
            "phone_number": config['twilio']['phone_number'],
        }
        
        # API endpoints
        patient_app_api_config = {
            "user_registration": config['apis']['user_registration'],
            "user_view": config['apis']['user_view'],
            "fetch_pt_list": config['apis']['fetch_pt_list'],
            "add_patient": config['apis']['add_patient'],
            "add_user_address_api": config['apis']['user_address_api'],
            "show_address_api": config['apis']['show_address_api'],
            "booking_presc_api": config['apis']['booking_presc_api'],
            "booking_slot_api": config['apis']['booking_slot'],
            "booking_details": config['apis']['booking_details'],
            "branch_details": config['apis']['branch_details'],
            "invoice": config['apis']['invoice'],
            'booking_list': config['apis']['booking_list'],
            'edit_user_address_api': config['apis']['edit_user_address_api'],
            'get_user_address_api': config['apis']['get_user_address_api'],
        }
        

        
        # Prepend base_url to all API endpoints in patient_app_api_config
        api_base_url = config['apis']['base_url']
        for key, value in patient_app_api_config.items():
            if api_base_url == "base_url":
                continue
            patient_app_api_config[key] = api_base_url + value



        # Database API endpoints
        db_api_config = {
            'get_booking_api': config['db_api']['get_booking_api'],
            'save_booking_url': config['db_api']['save_booking_url'],
            'download_reports': config['db_api']['download_reports'],
            'check_nationality_api': config['db_api']['check_nationality_api'],
            'save_user_details_api': config['db_api']['save_user_details_api'],
            'update_nationality_api': config['db_api']['update_nationality_api'],
            'check_surname_api': config['db_api']['check_surname_api']
        }




        # Prepend base_url to all API endpoints in db_api_config
        db_base_url = config['db_api']['base_url']
        for key, value in db_api_config.items():
            if db_base_url == "base_url":
                continue
            db_api_config[key] = db_base_url + value



        # Content SIDs
        content_sid_config = {
            'existing_user_options_sid': config['content_sid']['existing_user_options_sid'],
            'relationship_sid': config['content_sid']['relationship_sid'],
            'nationality_sid': config['content_sid']['nationality_sid'],
            'patient_nationality_someone': config['content_sid']['patient_nationality_someone'],
            'someone_else_relationship': config['content_sid']['someone_else_relationship'],
            'someone_else_gender': config['content_sid']['someone_else_gender'],
            'existing_address': config['content_sid']['existing_address'],
            'booking_options_sid': config['content_sid']['booking_options_sid'],
            'day_slot_sid': config['content_sid']['day_slot_sid'],
            'gender_new_user': config['content_sid']['gender_new_user'],
            'morning_slot_sid': config['content_sid']['morning_slot_sid'],
            'afternoon_slot_sid': config['content_sid']['afternoon_slot_sid'],
            'evening_slot_sid': config['content_sid']['evening_slot_sid'],
            'booking_details_sid': config['content_sid']['booking_details_sid'],
            'province_sid': config['content_sid']['province_sid'],
            'user_address_confirmation': config['content_sid']['user_address_confirmation'],
            'add_family_patient': config['content_sid']['add_family_patient']
        }
        
        # Combine all configurations
        loaded_config = {}
        
        # Add each config dictionary to the combined config
        loaded_config.update(twilio_config)
        loaded_config.update(patient_app_api_config)
        loaded_config.update(db_api_config)
        loaded_config.update(content_sid_config)
        
        return loaded_config
        
    except KeyError as e:
        logger.error(f"Missing required configuration key: {e}")
        raise
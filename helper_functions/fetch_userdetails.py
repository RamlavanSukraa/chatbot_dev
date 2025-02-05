
from config import load_config
import requests
from utils.logger import app_logger as logger

config = load_config()
user_view_api = config['user_view']


# Function to fetch user details from the User View API
def fetch_user_details_from_api(mobile_api: str) -> dict:
    """
    Fetches user details from the User View API based on the mobile API.
    """
    try:
        api_payload = {"Username": mobile_api}
        response = requests.post(user_view_api, json=api_payload)

        if response.status_code == 200:
            api_response = response.json()
            if api_response.get("SuccessFlag") == "true":
                user_details = api_response["Message"][0]
                return {
                    "first_name": user_details.get("First_Name"),
                    "surname": user_details.get("Sur_Name"),
                    "gender": user_details.get("User_Gender"),
                    "dob": user_details.get("User_DOB"),
                    "mobile": user_details.get("User_Mobile_No"),
                }
            else:
                logger.error(f"Failed to fetch user details for {mobile_api}.")
                return {}
        else:
            logger.error(f"Failed to fetch user details from User View API for {mobile_api}.")
            return {}

    except requests.RequestException as e:
        logger.error(f"Error while fetching user details from User View API: {e}")
        return {}

# WhatsApp Chatbot Setup Guide

This guide provides detailed steps to set up, configure, and run the WhatsApp Chatbot locally or on a production server.

---

## Project Overview

The WhatsApp Chatbot handles multiple user interactions, including:
- Adding patient details.
- Viewing patient and address details.
- Booking services with or without prescriptions.
- Viewing booking slots and branch details.

The project uses the Twilio API for WhatsApp messaging, a state management system, and external APIs for patient registration, booking, and more.

---

## Project Structure

```
whatsapp-bot/
├── app.py                    # FastAPI app entry point
├── config.py                 # Configuration loader for settings and API details
├── config.ini                # Configuration file with API keys and endpoints
├── main.py                   # Core logic for processing messages and chatbot routing
├── state_manager.py          # Manages user-specific interaction states
├── README.md                 # Documentation and setup guide
├── requirements.txt          # Python dependencies
├── utils/                    # Utility functions and helpers
│   ├── logger.py             # Logger setup and utility
│   ├── messaging_utils.py    # Functions to send and format WhatsApp messages
│   ├── number_utils.py       # Functions for cleaning and formatting phone numbers
├── controller/               # Core logic for handling chatbot workflows
│   ├── add_pt.py             # Handles the Add Patient flow
│   ├── book_presc.py         # Handles booking with prescriptions
│   ├── booking_details.py    # Handles booking details flow
│   ├── download_reports.py   # Handles downloading lab reports
│   ├── new_user_reg.py       # Manages user registration and onboarding
│   ├── user_address.py       # Manages adding and viewing user addresses
│   ├── view_pt_det.py        # Handles patient detail viewing
├── requirements.txt         # Project dependencies
└── README.md                # Setup and usage instructions
```

---

## Prerequisites

1. **Python 3.8+**: Ensure Python is installed on your system.
2. **Twilio Account**: Obtain your Twilio Account SID, Auth Token, and WhatsApp number.
3. **API Access**: Ensure external APIs required by the chatbot (e.g., booking, patient registration) are available.

---

## Setup Instructions

### Step 1: Clone the Repository
```bash
git clone https://github.com/ayush-sukraa/SukraaServiceBookingAIAgent.git
cd whatsAppBot
```

### Step 2: Create a Virtual Environment
Create a Python virtual environment to manage dependencies:
```bash
python3 -m venv myenv
.\myenv\Scripts\activate
```

### Step 3: Install Dependencies
Install all required libraries:
```bash
pip install -r requirements.txt
```

### Step 4: Configure the Application
1. **Open `config.ini`**:
   - Add your **Twilio credentials**:
     ```python
     account_sid = "<your-account-sid>"
     auth_token = "<your-auth-token>"
     phone_number = "<your-twilio-whatsapp-number>"
     ```
   - Update all external API URLs:
     ```python
     user_registration = "<API-URL-for-adding-patient>"
     user_view = "<API-URL-for-view-registered-user>"
     fetch_pt_list = "<API-URL-for-fetch-patient>"
     add_patient = "<API-URL-for-adding-patient>"
     user_address_api = "<API-URL-for-user-address-add>"
     show_address_api = "<API-URL-for-show-address>"
     new_booking_presc ="<API-URL-for-new-booking-with-presc>"
     booking_slot = "<API-URL-for-view-slots>"
     booking_details = "<API-URL-for-booking-details>"
     branch_details = "<API-URL-for-branch-details>"
     ```

2. **Ensure all necessary APIs are functional**:
   - APIs for patient registration, booking, branch details, etc., must return valid responses.

---

## Running the Application

### Step 1: Start the Application Locally
To run the chatbot on `localhost`:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Expose the Local Server 
To test the chatbot with Twilio, expose your local server using **ngrok**:
```bash
ngrok http 8000
```
Copy the generated `https://<ngrok-url>` for webhook setup.

---

## Configuring Twilio Webhook

1. Log in to your [Twilio Console](https://console.twilio.com/).
2. Go to **Messaging** > **Try it out** > **Send a WhatsApp Message** > **Sandbox settings**
3. Set the **Webhook URL**:
   ```
   https://<your-server-domain>/chatbot
   ```
   Replace `<your-server-domain>` with your `ngrok` URL or live server URL.

---

## Testing the Application

### Sending Messages
- **WhatsApp Number**: Use your Twilio WhatsApp number for interactions.
- **Sandbox settings**: To join in the sandbox, copy the sandbox code and send to twilio WhatsApp number 
- **Sample Commands**:
  - Send `hi` to view the main menu.
  - Select options (e.g., `1` for Add Patient, `2` for View Patient Details).


---


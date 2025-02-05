# app.py

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from main import process_message
from utils.logger import app_logger as logger

app = FastAPI()

@app.post("/chatbot")
async def chatbot_flow(request: Request):
    """
    Chatbot endpoint to handle incoming messages with optional media upload.
    """
    try:
        # Parse incoming request data
        body = await request.form()
        from_number = body.get("From", "")
        message_body = body.get("Body", "")
        media_url = body.get("MediaUrl0", "")  # URL for uploaded media

        # Prepare request_data for the message processor
        request_data = {"MediaUrl0": media_url}

        # Log received message and media
        logger.info(f"Received message from: {from_number}, Body: {message_body}, Media URL: {media_url}")

        # Process the messagec
        response = process_message(from_number, message_body, request_data)

        # Log and return the response
        logger.info(f"Response generated successfully for {from_number}")
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error occurred while processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

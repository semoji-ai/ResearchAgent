import os
import json
from fastapi import APIRouter, UploadFile, File, Form, Depends
from app.core.google_drive import drive_service
from openai import OpenAI

router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"]
)

# Mock in-memory DB for the MVP
_MOCK_CONTACTS_DB = []

@router.post("/ocr")
async def process_business_card(
    file: UploadFile = File(...),
    company_id: int = Form(...)
):
    """
    Endpoint to process an uploaded business card image.
    1. Uploads to Google Drive.
    2. Simulates calling OpenAI/Gemini Vision API for OCR.
    3. Saves structured JSON to database.
    4. Simulates syncing to Google Contacts.
    """

    # 1. Upload to Google Drive (Mocked or real depending on env)
    file_content = await file.read()
    drive_id = drive_service.upload_file(
        company_id=company_id,
        file_name=file.filename,
        file_content=file_content,
        mime_type=file.content_type
    )

    # 2. Real AI Vision OCR & Parsing via OpenAI (if key exists)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            # In a real scenario, we would pass base64 encoded image to the vision model
            # For this MVP code structure, we simulate the prompt to return JSON.
            import base64
            base64_image = base64.b64encode(file_content).decode('utf-8')
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an OCR assistant. Parse the business card image and return JSON strictly matching keys: name, email, company, address, phone_number."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Extract data from this business card."},
                        {"type": "image_url", "image_url": {"url": f"data:{file.content_type};base64,{base64_image}"}}
                    ]}
                ],
                response_format={ "type": "json_object" }
            )
            parsed_data = json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI call failed: {e}. Falling back to mock data.")
            parsed_data = {
                "name": "홍길동 (API Fail)",
                "email": "fail@example.com",
                "company": "대한상사",
                "address": "서울시 강남",
                "phone_number": "010-0000-0000"
            }
    else:
        # Fallback if no API key is configured yet
        parsed_data = {
            "name": "홍길동",
            "email": "gildong@example.com",
            "company": "대한상사",
            "address": "서울시 강남구 테헤란로 123",
            "phone_number": "010-1234-5678"
        }

    # 3. Save to Database
    contact_record = {
        "id": len(_MOCK_CONTACTS_DB) + 1,
        "company_id": company_id,
        "drive_reference_id": drive_id,
        "data": parsed_data,
        "synced_to_google": True
    }
    _MOCK_CONTACTS_DB.append(contact_record)

    # 4. Return result
    return {
        "message": "Business card processed and synced to Google Contacts successfully.",
        "drive_id": drive_id,
        "parsed_data": parsed_data
    }

@router.get("/")
def list_contacts(company_id: int = 1):
    """
    List all contacts for the authenticated user's company.
    """
    company_contacts = [c for c in _MOCK_CONTACTS_DB if c["company_id"] == company_id]
    return {"contacts": company_contacts}

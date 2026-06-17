import os
import json
from fastapi import APIRouter, UploadFile, File, Form
from app.core.google_drive import drive_service
from openai import OpenAI
import datetime

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"]
)

_MOCK_MEETINGS_DB = []

@router.post("/")
async def create_meeting_record(
    file: UploadFile = File(...),
    company_id: int = Form(...)
):
    """
    Endpoint to receive audio/text meeting data.
    1. Uploads to Drive.
    2. Simulates LLM Parsing for context extraction.
    3. Saves record.
    """

    file_content = await file.read()
    drive_id = drive_service.upload_file(
        company_id=company_id,
        file_name=file.filename,
        file_content=file_content,
        mime_type=file.content_type
    )

    # Real LLM Parsing via OpenAI (if key exists)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            text_content = file_content.decode('utf-8', errors='ignore')
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a meeting assistant. Summarize the meeting audio transcript and return JSON with keys: client_name, project_id, summary, action_items (list of strings)."},
                    {"role": "user", "content": f"Extract data from this meeting transcript:\n\n{text_content}"}
                ],
                response_format={ "type": "json_object" }
            )
            parsed_summary = json.loads(completion.choices[0].message.content)
        except Exception as e:
            print(f"OpenAI call failed: {e}. Falling back to mock data.")
            parsed_summary = {
                "client_name": "ABC Corp (API Fail)",
                "project_id": "PRJ-FAIL",
                "summary": "Failed to call OpenAI.",
                "action_items": ["Check API Key"]
            }
    else:
        # Fallback if no API key is configured yet
        parsed_summary = {
            "client_name": "ABC Corp",
            "project_id": "PRJ-2023-01",
            "summary": "Discussed the new ERP rollout schedule. Client requested faster delivery by Q3.",
            "action_items": ["Send revised quote", "Schedule follow-up on Friday"]
        }

    meeting_record = {
        "id": len(_MOCK_MEETINGS_DB) + 1,
        "company_id": company_id,
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "drive_reference_id": drive_id,
        "data": parsed_summary
    }
    _MOCK_MEETINGS_DB.append(meeting_record)

    return {
        "message": "Meeting audio processed and summarized.",
        "meeting": meeting_record
    }

@router.get("/")
def list_meetings(company_id: int = 1):
    company_meetings = [m for m in _MOCK_MEETINGS_DB if m["company_id"] == company_id]
    return {"meetings": company_meetings}

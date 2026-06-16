from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"]
)

@router.post("/")
def create_meeting_record():
    """
    Webhook endpoint to receive parsed meeting data (e.g., from Pliaud / Zapier).
    """
    return {"message": "Meeting record successfully received and queued for parsing."}

@router.get("/")
def list_meetings():
    """
    List all recorded meetings for the authenticated user's company.
    """
    return {"meetings": []}

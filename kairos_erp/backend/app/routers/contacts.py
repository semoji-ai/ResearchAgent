from fastapi import APIRouter

router = APIRouter(
    prefix="/contacts",
    tags=["Contacts"]
)

@router.post("/ocr")
def process_business_card():
    """
    Endpoint to process an uploaded business card image, perform OCR,
    and optionally sync to Google Contacts.
    """
    return {"message": "Business card processed successfully."}

@router.get("/")
def list_contacts():
    """
    List all contacts for the authenticated user's company.
    """
    return {"contacts": []}

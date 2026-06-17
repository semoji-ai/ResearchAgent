from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(
    prefix="/finance",
    tags=["Finance"]
)

_MOCK_SALES_DB = [
    {"id": 1, "company_id": 1, "client_name": "ABC Corp", "amount": 1000000, "status": "pending", "date": "2023-10-25"},
    {"id": 2, "company_id": 1, "client_name": "XYZ Inc", "amount": 500000, "status": "pending", "date": "2023-10-26"}
]

class BankPushNotification(BaseModel):
    company_id: int
    text: str # e.g., "[신한은행] 입금 1,000,000원 ABC Corp"

@router.post("/deposit")
def record_deposit(notification: BankPushNotification):
    """
    Webhook endpoint to receive bank deposit push notifications and match with pending sales.
    """
    # 1. Parse text using LLM or Regex to get amount and sender name
    # Simulating parsed output for MVP
    parsed_amount = 1000000
    parsed_sender = "ABC Corp"

    # 2. Match with pending sales
    matched_sale = None
    for sale in _MOCK_SALES_DB:
        if sale["company_id"] == notification.company_id and sale["status"] == "pending":
            if sale["amount"] == parsed_amount and sale["client_name"] == parsed_sender:
                sale["status"] = "completed"
                matched_sale = sale
                break

    if matched_sale:
        return {"message": "Deposit recorded and perfectly matched with sale.", "matched_sale_id": matched_sale["id"]}
    else:
        return {"message": "Deposit recorded as unmatched.", "parsed": {"amount": parsed_amount, "sender": parsed_sender}}

@router.get("/sales")
def list_sales(company_id: int = 1):
    """
    List sales and their payment status.
    """
    company_sales = [s for s in _MOCK_SALES_DB if s["company_id"] == company_id]
    return {"sales": company_sales}

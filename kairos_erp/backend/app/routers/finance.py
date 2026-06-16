from fastapi import APIRouter

router = APIRouter(
    prefix="/finance",
    tags=["Finance"]
)

@router.post("/deposit")
def record_deposit():
    """
    Webhook endpoint to receive bank deposit push notifications and match with pending sales.
    """
    return {"message": "Deposit recorded and matched."}

@router.get("/sales")
def list_sales():
    """
    List sales and their payment status.
    """
    return {"sales": []}

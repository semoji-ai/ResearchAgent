from fastapi import APIRouter

router = APIRouter(
    prefix="/tax",
    tags=["Tax"]
)

@router.post("/invoice")
def issue_tax_invoice():
    """
    Endpoint to request tax invoice issuance via Popbill/Hometax integration.
    """
    return {"message": "Tax invoice issuance requested successfully."}

@router.get("/invoices")
def list_tax_invoices():
    """
    List issued tax invoices.
    """
    return {"invoices": []}

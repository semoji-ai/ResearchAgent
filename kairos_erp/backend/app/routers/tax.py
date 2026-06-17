from fastapi import APIRouter
from pydantic import BaseModel
import datetime

router = APIRouter(
    prefix="/tax",
    tags=["Tax"]
)

_MOCK_INVOICES_DB = []

class InvoiceRequest(BaseModel):
    company_id: int
    sale_id: int
    client_name: str
    client_business_number: str
    amount: int

@router.post("/invoice")
def issue_tax_invoice(req: InvoiceRequest):
    """
    Endpoint to request tax invoice issuance via Popbill/Hometax integration.
    """
    # 1. Look up company info (Supplier)
    # 2. Look up client info (Buyer) using req.client_business_number
    # 3. Call Popbill API
    # 4. Save record

    invoice_record = {
        "id": len(_MOCK_INVOICES_DB) + 1,
        "company_id": req.company_id,
        "sale_id": req.sale_id,
        "client_name": req.client_name,
        "amount": req.amount,
        "hometax_status": "issued",
        "issued_date": datetime.datetime.now().strftime("%Y-%m-%d")
    }
    _MOCK_INVOICES_DB.append(invoice_record)

    return {"message": "Tax invoice issuance requested successfully to Popbill.", "invoice": invoice_record}

@router.get("/invoices")
def list_tax_invoices(company_id: int = 1):
    """
    List issued tax invoices.
    """
    company_invoices = [i for i in _MOCK_INVOICES_DB if i["company_id"] == company_id]
    return {"invoices": company_invoices}

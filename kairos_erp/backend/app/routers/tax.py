from fastapi import APIRouter
from pydantic import BaseModel
import os
import datetime
from popbill import TaxinvoiceService, Taxinvoice, TaxinvoiceDetail, Contact

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
    popbill_link_id = os.getenv("POPBILL_LINK_ID")
    popbill_secret = os.getenv("POPBILL_SECRET")
    corp_num = os.getenv("COMPANY_BUSINESS_NUMBER", "1234567890")

    hometax_status = "issued_mock"
    if popbill_link_id and popbill_secret:
        try:
            taxinvoiceService = TaxinvoiceService(popbill_link_id, popbill_secret)
            taxinvoiceService.IsTest = True # Sandbox mode for safety

            taxinvoice = Taxinvoice(
                writeDate = datetime.datetime.now().strftime("%Y%m%d"),
                issueType = '정발행',
                chargeDirection = '청구',
                purposeType = '영수',
                taxType = '과세',
                issueTiming = '직접발행',

                # Supplier Info (ERP Company)
                invoicerCorpNum = corp_num,
                invoicerCorpName = 'Kairos ERP Inc.',
                invoicerCEOName = 'CEO Name',

                # Buyer Info
                invoiceeCorpNum = req.client_business_number.replace('-', ''),
                invoiceeCorpName = req.client_name,

                supplyCostTotal = str(int(req.amount * 0.9)),
                taxTotal = str(int(req.amount * 0.1)),
                totalAmount = str(req.amount)
            )

            response = taxinvoiceService.registIssue(corp_num, taxinvoice)
            hometax_status = "issued_live"
        except Exception as e:
            print(f"Popbill API error: {e}")
            hometax_status = "error_api"

    invoice_record = {
        "id": len(_MOCK_INVOICES_DB) + 1,
        "company_id": req.company_id,
        "sale_id": req.sale_id,
        "client_name": req.client_name,
        "amount": req.amount,
        "hometax_status": hometax_status,
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

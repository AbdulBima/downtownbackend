from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from routes.user_routes import create_invoice_pdf, create_pdf
from serializers.user_serlizer import InvoiceData, ReceiptData

# ------------------------
# Pydantic Serializers
# ------------------------

class CustomerSerializer(BaseModel):
    id: str
    name: str
    contact: str
    address: str

class InvoiceSerializer(BaseModel):
    id: Optional[str] = Field(None, description="Invoice ID")
    customer: CustomerSerializer
    productType: str  # "pp" or "injection"
    processType: List[str]  # list of "R", "C", "B"
    kgIn: float
    kgOut: Optional[float] = 0
    amount: float = 0
    status: str = "in progress"
    recycler: Optional[str] = None  # "a" or "b"
    date: str  # "YYYY-MM-DD"

class PaginatedInvoices(BaseModel):
    total: int
    invoices: List[InvoiceSerializer]

# ------------------------
# Database Connection
# ------------------------
from config.database import db  # e.g., db = AsyncIOMotorClient(MONGO_URI).mydatabase
invoices_collection = db.downtown_invoices  # Adjust collection name as needed

# ------------------------
# Helper Function: Convert MongoDB Document
# ------------------------
def invoice_helper(invoice) -> dict:
    return {
        "id": str(invoice["_id"]),
        "customer": invoice["customer"],
        "productType": invoice["productType"],
        "processType": invoice["processType"],
        "kgIn": invoice["kgIn"],
        "kgOut": invoice.get("kgOut", 0),
        "amount": invoice.get("amount", 0),
        "status": invoice.get("status", "in progress"),
        "recycler": invoice.get("recycler"),
        "date": invoice["date"],
    }

# ------------------------
# Invoice Endpoints
# ------------------------
router = APIRouter()

@router.get("/get-invoices", response_model=PaginatedInvoices)
async def get_invoices(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve a list of invoices with pagination.
    """
    total = await invoices_collection.count_documents({})
    cursor = invoices_collection.find().skip(skip).limit(limit)
    invoices = [invoice_helper(inv) async for inv in cursor]
    return {"total": total, "invoices": invoices}

@router.get("/get-invoices/open", response_model=PaginatedInvoices)
async def get_open_invoices(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve a list of invoices with status 'in progress' or 'stopped' with pagination,
    sorted with the latest documents first.
    """
    query = {"status": {"$in": ["in progress", "stopped"]}}
    total = await invoices_collection.count_documents(query)
    cursor = invoices_collection.find(query).sort("date", -1).skip(skip).limit(limit)
    invoices = [invoice_helper(inv) async for inv in cursor]
    return {"total": total, "invoices": invoices}


@router.get("/get-invoices/completed", response_model=PaginatedInvoices)
async def get_completed_invoices(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve a list of invoices with status 'completed' with pagination,
    sorted with the latest documents first.
    """
    query = {"status": "completed"}
    total = await invoices_collection.count_documents(query)
    cursor = invoices_collection.find(query).sort("date", -1).skip(skip).limit(limit)
    invoices = [invoice_helper(inv) async for inv in cursor]
    return {"total": total, "invoices": invoices}


@router.post("/create-invoices", response_model=InvoiceSerializer)
async def create_invoice(invoice: InvoiceSerializer):
    """
    Create a new invoice.
    The invoice status is always set to "in progress".
    """
    # Override status regardless of client input
    invoice.status = "in progress"
    invoice_data = invoice.model_dump(exclude={"id"})
    result = await invoices_collection.insert_one(invoice_data)
    if result.inserted_id:
        new_invoice = await invoices_collection.find_one({"_id": result.inserted_id})
        return invoice_helper(new_invoice)
    raise HTTPException(status_code=500, detail="Failed to create invoice")

@router.put("/update/{invoice_id}", response_model=InvoiceSerializer)
async def update_invoice(invoice_id: str, invoice: InvoiceSerializer):
    """
    Update an existing invoice.
    """
    update_data = invoice.model_dump(exclude_unset=True, exclude={"id"})
    result = await invoices_collection.update_one(
        {"_id": ObjectId(invoice_id)}, {"$set": update_data}
    )
    if result.modified_count == 1:
        updated_invoice = await invoices_collection.find_one({"_id": ObjectId(invoice_id)})
        return invoice_helper(updated_invoice)
    raise HTTPException(status_code=404, detail="Invoice not found")

@router.delete("/del/{invoice_id}", response_model=dict)
async def delete_invoice(invoice_id: str):
    """
    Delete an invoice by its ID.
    """
    try:
        result = await invoices_collection.delete_one({"_id": ObjectId(invoice_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")
    if result.deleted_count == 1:
        return {"message": "Invoice deleted successfully", "id": invoice_id}
    raise HTTPException(status_code=404, detail="Invoice not found")


# POST endpoint that receives receipt data and returns a PDF file
@router.post("/generate-receipt", response_class=StreamingResponse)
async def generate_receipt_pdf(receipt: ReceiptData):
    pdf_buffer = create_pdf(receipt)
    headers = {"Content-Disposition": "attachment; filename=receipt.pdf"}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.post("/generate-invoice", response_class=StreamingResponse)
async def generate_invoice_pdf(invoice: InvoiceData):
    pdf_buffer = create_invoice_pdf(invoice)
    headers = {"Content-Disposition": "attachment; filename=invoice.pdf"}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.get("/get-invoice/{invoice_id}", response_model=InvoiceSerializer)
async def get_invoice(invoice_id: str):
    invoice = await invoices_collection.find_one({"_id": ObjectId(invoice_id)})
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice_helper(invoice)

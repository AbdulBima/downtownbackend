from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from config.database import db
from serializers.purchases_serializer import PurchaseSerializer
from serializers.user_serlizer import CustomerSerializer  # Your existing customer serializer

# For PDF generation
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

router = APIRouter()

# Utility function to convert a MongoDB purchase document into a dict
def purchase_helper(purchase) -> dict:
    return {
        "id": str(purchase["_id"]),
        "date": purchase["date"],
        "customer": purchase.get("customer"),  # Stored as a dict matching CustomerSerializer
        "productType": purchase["productType"],
        "kg": purchase["kg"],
        "amount": purchase["amount"],
    }



# Define the MongoDB collection for purchases.
purchases_collection = db.downtown_purchases

# ---------------------------------
# GET: Retrieve Purchases with Pagination
# ---------------------------------
@router.get("/get/purchases", response_model=dict)
async def get_purchases(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve a paginated list of purchases.
    Returns the total count and a list of purchase objects.
    """
    purchases_cursor = purchases_collection.find().skip(skip).limit(limit)
    purchases_list = [purchase_helper(purchase) async for purchase in purchases_cursor]
    total_count = await purchases_collection.count_documents({})
    return {"total": total_count, "count": len(purchases_list), "purchases": purchases_list}

# ---------------------------------
# POST: Create a New Purchase
# ---------------------------------
@router.post("/create/purchases", response_model=dict)
async def create_purchase(purchase: PurchaseSerializer):
    """
    Create a new purchase.
    The request must include customer details.
    """
    if not purchase.customer:
        raise HTTPException(status_code=400, detail="Customer details are required")
    purchase_data = purchase.dict(exclude={"id"})
    result = await purchases_collection.insert_one(purchase_data)
    if result.inserted_id:
        return {"message": "Purchase created successfully", "id": str(result.inserted_id)}
    raise HTTPException(status_code=500, detail="Failed to create purchase")

# ---------------------------------
# PUT: Update an Existing Purchase
# ---------------------------------
@router.put("/update/{purchase_id}", response_model=dict)
async def update_purchase(purchase_id: str, purchase: PurchaseSerializer):
    """
    Update an existing purchase.
    Only the provided fields will be updated.
    """
    try:
        obj_id = ObjectId(purchase_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid purchase ID format")
    
    updated_data = purchase.dict(exclude_unset=True, exclude={"id"})
    if updated_data:
        result = await purchases_collection.update_one({"_id": obj_id}, {"$set": updated_data})
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Purchase not found or no changes made")
    return {"message": "Purchase updated successfully", "id": purchase_id}

# ---------------------------------
# DELETE: Delete a Purchase
# ---------------------------------
@router.delete("/{purchase_id}", response_model=dict)
async def delete_purchase(purchase_id: str):
    """
    Delete a purchase by its ID.
    """
    try:
        obj_id = ObjectId(purchase_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid purchase ID format")
    
    result = await purchases_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return {"message": "Purchase deleted successfully", "id": purchase_id}

# ---------------------------------
# PDF Generation: Create Purchase PDF
# ---------------------------------
def create_purchase_pdf(purchase: PurchaseSerializer) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    page_width, page_height = landscape(letter)

    # Header Section
    pdf.setFillColorRGB(0.2, 0.4, 0.8)
    pdf.rect(0, page_height - 100, page_width, 100, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(page_width / 2, page_height - 60, "PURCHASE RECEIPT")
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(page_width / 2, page_height - 80, "Downtown Plastic & Recycling LTD")

    # Build Table Data
    data = [
        ["Field", "Detail"],
        ["Purchase ID", purchase.id or "N/A"],
        ["Date", purchase.date],
        ["Customer", purchase.customer.name if purchase.customer else "N/A"],
        ["Contact", purchase.customer.contact if purchase.customer else "N/A"],
        ["Address", purchase.customer.address if purchase.customer else "N/A"],
        ["Product Type", purchase.productType],
        ["Kg", str(purchase.kg)],
        ["Amount", f"N{purchase.amount:,}"],
    ]
    table = Table(data, colWidths=[150, page_width - 200])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
    ])
    table.setStyle(style)

    table_width, table_height = table.wrap(0, 0)
    table_x = (page_width - table_width) / 2
    table_y = page_height - 150 - table_height
    table.drawOn(pdf, table_x, table_y)

    # Footer Message
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Oblique", 14)
    pdf.drawCentredString(page_width / 2, table_y - 30, "Thank you for your business!")
    
    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

@router.post("/generate-pdf", response_class=StreamingResponse)
async def generate_purchase_pdf(purchase: PurchaseSerializer):
    """
    Generate a PDF receipt for the provided purchase record.
    """
    pdf_buffer = create_purchase_pdf(purchase)
    headers = {"Content-Disposition": f"attachment; filename=Purchase-{purchase.id or 'new'}.pdf"}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

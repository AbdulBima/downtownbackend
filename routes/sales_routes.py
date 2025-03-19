from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import uuid
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

from fastapi.responses import StreamingResponse

from config.database import db
from serializers.sales_serializer import SaleCreateSerializer, SaleSerializer

router = APIRouter()
sales_collection = db.downtown_sales  # Ensure this collection exists in your MongoDB


# ------------------------
# Helper Functions
# ------------------------
def sale_helper(sale) -> dict:
    """Convert a MongoDB sale document to a dict."""
    return {
        "id": str(sale["_id"]),
        "date": sale.get("date", ""),
        "customer": sale.get("customer", {}),
        "productType": sale.get("productType", ""),
        "kg": sale.get("kg", 0),
        "amount": sale.get("amount", 0),
        "created_at": sale.get("created_at"),
    }

def create_sale_pdf(sale: SaleSerializer) -> BytesIO:
    """
    Generate a PDF receipt for a sale using ReportLab.
    Expects a complete sale object.
    """
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    page_width, page_height = landscape(letter)

    # Header Section (Green Background)
    pdf.setFillColorRGB(0.2, 0.6, 0.2)
    pdf.rect(0, page_height - 100, page_width, 100, fill=1, stroke=0)
    
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(page_width / 2, page_height - 60, "SALES RECEIPT")
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(page_width / 2, page_height - 80, "Downtown Plastic & Recycling LTD")
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 95,
        "Contact: 08065566537, 08088877795 | No 2, Shasan, Small Scale Industry, Kano"
    )

    data = [
        ["Field", "Detail"],
        ["Sale ID", sale.id],
        ["Date", sale.date],
        ["Customer", sale.customer.get("name", "")],
        ["Contact", sale.customer.get("contact", "")],
        ["Address", sale.customer.get("address", "")],
        ["Product", sale.productType],
        ["Kg", str(sale.kg)],
        ["Amount", f"N{sale.amount:,.2f}"],
    ]

    table = Table(data, colWidths=[150, page_width - 200])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ])
    table.setStyle(style)

    table_width, table_height = table.wrap(0, 0)
    table_x = (page_width - table_width) / 2
    table_y = page_height - 150 - table_height
    table.drawOn(pdf, table_x, table_y)

    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Oblique", 14)
    pdf.drawCentredString(page_width / 2, table_y - 30, "Thank you for your business!")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

# ------------------------
# Sales Endpoints
# ------------------------

@router.get("/get-sales", response_model=dict)
async def get_sales(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve sales with pagination.
    Returns a dict with total count, count of returned sales, and a list of sales.
    """
    sales_cursor = sales_collection.find().skip(skip).limit(limit)
    sales_list = [sale_helper(sale) async for sale in sales_cursor]
    total_count = await sales_collection.count_documents({})
    return {
        "total": total_count,
        "count": len(sales_list),
        "sales": sales_list
    }

@router.post("/create-sale", response_model=dict)
async def create_sale(sale: SaleCreateSerializer):
    """
    Create a new sale.
    Expects a sale object (without 'id' or 'created_at') and returns the created sale.
    """
    sale_data = sale.model_dump()
    sale_data["created_at"] = datetime.now(timezone.utc)
    # Generate a unique sale id using uuid (stored in MongoDB as _id)
    sale_data["_id"] = uuid.uuid4().hex
    result = await sales_collection.insert_one(sale_data)
    if result.inserted_id:
        created_sale = await sales_collection.find_one({"_id": sale_data["_id"]})
        return sale_helper(created_sale)
    raise HTTPException(status_code=500, detail="Failed to create sale")

@router.delete("/del/{sale_id}", response_model=dict)
async def delete_sale(sale_id: str):
    """
    Delete a sale by sale_id.
    """
    result = await sales_collection.delete_one({"_id": sale_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sale not found")
    return {"message": "Sale deleted successfully", "sale_id": sale_id}

@router.post("/generate-pdf", response_class=StreamingResponse)
async def generate_sale_pdf(sale: SaleSerializer):
    """
    Generate a PDF receipt for a given sale.
    """
    pdf_buffer = create_sale_pdf(sale)
    headers = {"Content-Disposition": f"attachment; filename=Sale-{sale.id}.pdf"}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

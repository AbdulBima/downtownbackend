from datetime import datetime, timedelta, timezone


import os
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional, List
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape

import jwt
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel, EmailStr
from config.database import db  # MongoDB connection
from passlib.context import CryptContext


from serializers.user_serlizer import CustomerSerializer, InvoiceData, LoginRequest, ReceiptData, SaleData

router = APIRouter()
users_collection =  db.downtown_users
downtown_customers_collection = db.downtown_customers


# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User model
class UserSerializer(BaseModel):
    name: str
    email: EmailStr
    password: str


def create_pdf(receipt: ReceiptData) -> BytesIO:
    buffer = BytesIO()
    # Set up the canvas in landscape mode
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    page_width, page_height = landscape(letter)

    # ---------------------------
    # Header Section
    # ---------------------------
    pdf.setFillColorRGB(0.1, 0.4, 0.8)  # Blue header background
    pdf.rect(0, page_height - 100, page_width, 100, fill=1, stroke=0)
    
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawCentredString(page_width / 2, page_height - 60, "Downtown Plastic & Recycling LTD")
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 80,
        "Contact: 08065566537, 08088877795 | No 2, Shasan, Small Scale Industry, Kano"
    )

    # ---------------------------
    # Build Table Data (Item - Value)
    # ---------------------------
    data = [
        ["Item", "Value"],
        ["Receipt ID", receipt.id],
        ["Date", receipt.date],
        ["Customer", receipt.customer.name],
        ["Contact", receipt.customer.contact],
        ["Address", receipt.customer.address],
        ["Product Type", receipt.productType],
        ["Process Type", ", ".join(receipt.processType)],
        ["Kg In", str(receipt.kgIn)],
        ["Kg Out", str(receipt.kgOut)],
        ["Status", receipt.status],
    ]
    if receipt.amount is not None:
        data.append(["Total Amount", f"N{receipt.amount:,}"])

    # ---------------------------
    # Create and Style the Table
    # ---------------------------
    table = Table(data)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E78')),  # Header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
    ])
    table.setStyle(style)

    # ---------------------------
    # Center the Table on the Page
    # ---------------------------
    table_width, table_height = table.wrap(0, 0)
    table_x = (page_width - table_width) / 2
    # Position the table below the header with some margin
    table_y = page_height - 150 - table_height  
    table.drawOn(pdf, table_x, table_y)

    # ---------------------------
    # Thank You Message Immediately After the Table
    # ---------------------------
    # Draw the message 20 units below the bottom of the table
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Oblique", 14)
    pdf.drawCentredString(page_width / 2, table_y - 20, "Thank you for your business!")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer
    
def create_invoice_pdf(invoice: InvoiceData) -> BytesIO:
    buffer = BytesIO()
    # Use landscape mode for the page
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    page_width, page_height = landscape(letter)

    # ---------------------------
    # Header Section with Business Details
    # ---------------------------
    pdf.setFillColorRGB(0.8, 0, 0)  # Red background tone
    pdf.rect(0, page_height - 100, page_width, 100, fill=1, stroke=0)
    
    # Invoice Title
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawCentredString(page_width / 2, page_height - 40, "INVOICE")
    
    # Business Name
    pdf.setFont("Helvetica", 14)
    pdf.drawCentredString(page_width / 2, page_height - 70, "Downtown Plastic & Recycling LTD")
    
    # Business Contact Details
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(
        page_width / 2,
        page_height - 90,
        "Contact: 08065566537, 08088877795 | No 2, Shasan, Small Scale Industry, Kano"
    )

    # ---------------------------
    # Build Table Data (Field - Detail)
    # ---------------------------
    data = [
        ["Field", "Detail"],
        ["Invoice ID", str(invoice.id)],
        ["Date", invoice.date],
        ["Customer", invoice.customer.name],
        ["Contact", invoice.customer.contact],
        ["Address", invoice.customer.address],
        ["Product Type", invoice.productType],
        ["Process Type", ", ".join(invoice.processType)],
        ["Kg In", str(invoice.kgIn)],
        ["Kg Out", str(invoice.kgOut)],
        ["Status", invoice.status],
        ["Total Amount", f"N{invoice.amount:,}"],
    ]

    # ---------------------------
    # Create and Style the Table
    # ---------------------------
    table = Table(data, colWidths=[200, page_width - 250])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header row background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 16),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
    ])
    table.setStyle(style)

    # Center the table on the page
    table_width, table_height = table.wrap(0, 0)
    table_x = (page_width - table_width) / 2
    # Position the table below the header (with some vertical margin)
    table_y = page_height - 150 - table_height  
    table.drawOn(pdf, table_x, table_y)

    # ---------------------------
    # Footer Message (Immediately After the Table)
    # ---------------------------
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Oblique", 14)
    pdf.drawCentredString(page_width / 2, table_y - 30, "Thank you.")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer
    
    
def create_sale_pdf(sale: SaleData) -> BytesIO:
    buffer = BytesIO()
    # Create a canvas in landscape mode
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))
    page_width, page_height = landscape(letter)

    # ---------------------------
    # Header Section (Green Background)
    # ---------------------------
    pdf.setFillColorRGB(0.2, 0.6, 0.2)  # A green tone for sales
    pdf.rect(0, page_height - 100, page_width, 100, fill=1, stroke=0)
    
    # Header texts
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

    # ---------------------------
    # Build Table Data (Field - Detail)
    # ---------------------------
    data = [
        ["Field", "Detail"],
        ["Sale ID", sale.id],
        ["Date", sale.date],
        ["Customer", sale.customer.name],
        ["Contact", sale.customer.contact],
        ["Address", sale.customer.address],
        ["Product", sale.productType],
        ["Kg", str(sale.kg)],
        ["Amount", f"N{sale.amount:,}"],
    ]

    # ---------------------------
    # Create and Style the Table
    # ---------------------------
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

    # Center the table on the page
    table_width, table_height = table.wrap(0, 0)
    table_x = (page_width - table_width) / 2
    table_y = page_height - 150 - table_height  # position below the header
    table.drawOn(pdf, table_x, table_y)

    # ---------------------------
    # Footer Message Immediately After the Table
    # ---------------------------
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont("Helvetica-Oblique", 14)
    pdf.drawCentredString(page_width / 2, table_y - 30, "Thank you for your business!")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer

   
# ✅ MongoDB Helper Function to Convert ObjectId
def customer_helper(customer) -> dict:
    return {
        "id": str(customer["_id"]),
        "name": customer["name"],
        "contact": customer["contact"],
        "created_at": customer["created_at"]
    }
    
# Helper function to hash password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Security Config (Load values from .env)
SECRET_KEY = os.getenv("SECRET_KEY", "mistaemonma")  # Default to "mistaemonma" if SECRET_KEY is not set in .env
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # Default to "HS256" if ALGORITHM is not set in .env
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # Default to 30 minutes if not set

# Initialize OAuth2PasswordBearer for token extraction from request header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Function to create JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire =  datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
def verify_jwt_token(token: str) -> dict:
    try:
        # Decode the JWT token and verify it
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # You can also check for expiration time here
        if payload["exp"] < datetime.now(timezone.utc).timestamp():
            raise HTTPException(status_code=401, detail="Token has expired")
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Endpoint to verify the token and return True if valid
@router.get("/verify-token", response_model=dict)
async def verify_token(token: str = Depends(oauth2_scheme)):
    is_valid = verify_jwt_token(token)
    if is_valid:
        return {"valid": True}
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
# POST - Create User
@router.post("/users/create")
async def create_user(user: UserSerializer):
    # Check if email already exists
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = hash_password(user.password)
    
    # Create user document
    user_data = {
        "email": user.email,
        "password": hashed_password,
        "created_at": datetime.now(timezone.utc)


    }

    # Insert into MongoDB
    result = await users_collection.insert_one(user_data)
    
    if result.inserted_id:
        return {"message": "User created successfully", "id": str(result.inserted_id)}
    
    raise HTTPException(status_code=500, detail="Failed to create user")


# POST - Login User
@router.post("/users/login")
async def login_user(login_request: LoginRequest):
    # Check if user exists
    user = await users_collection.find_one({"email": login_request.email})  
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Verify password
    if not verify_password(login_request.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Create JWT token
    access_token = create_access_token(data={"sub": user["email"]})

    return {"access_token": access_token, "token_type": "bearer"}

# 🚀 **Create Customer**
@router.post("/create/customers", response_model=dict)
async def create_customer(customer: CustomerSerializer):
    customer_data = customer.model_dump()
    customer_data["created_at"] = datetime.utcnow()

    result = await downtown_customers_collection.insert_one(customer_data)
    if result.inserted_id:
        return {"message": "Customer created successfully", "id": str(result.inserted_id)}
    
    raise HTTPException(status_code=500, detail="Failed to create customer")

# 🔍 **Get Customers with Pagination**
@router.get("/get/customers", response_model=dict)
async def get_customers(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    customers_cursor = downtown_customers_collection.find().skip(skip).limit(limit)
    customers_list = [customer_helper(customer) async for customer in customers_cursor]
    
    total_count = await downtown_customers_collection.count_documents({})
    
    return {
        "total": total_count,
        "count": len(customers_list),
        "customers": customers_list
    }

# 🔄 **Update Customer**
@router.put("/customers/update/{customer_id}", response_model=dict)
async def update_customer(customer_id: str, customer_update: CustomerSerializer):
    try:
        customer_obj_id = ObjectId(customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    updated_data = customer_update.model_dump(exclude_unset=True)  # Only update provided fields
    updated_data["updated_at"] = datetime.timezone.utc()

    result = await downtown_customers_collection.update_one(
        {"_id": customer_obj_id},
        {"$set": updated_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found or no changes made")

    return {"message": "Customer updated successfully", "id": customer_id}


@router.get("/customers/get/{customer_id}", response_model=dict)
async def get_customer_by_id(customer_id: str):
    try:
        # Try converting the customer_id to ObjectId
        customer_obj_id = ObjectId(customer_id)
    except Exception:
        # If it fails, raise an error for invalid ObjectId format
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    # Find the customer by ID in the MongoDB collection
    customer = await downtown_customers_collection.find_one({"_id": customer_obj_id})

    # If no customer is found, raise a 404 error
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Return the customer data
    return customer_helper(customer)


# ❌ **Delete Customer**
@router.delete("/customers/{customer_id}", response_model=dict)
async def delete_customer(customer_id: str):
    try:
        customer_obj_id = ObjectId(customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    result = await downtown_customers_collection.delete_one({"_id": customer_obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"message": "Customer deleted successfully", "id": customer_id}


# POST endpoint that receives receipt data and returns a PDF file
@router.post("/receipts/generate-pdf", response_class=StreamingResponse)
async def generate_receipt_pdf(receipt: ReceiptData):
    pdf_buffer = create_pdf(receipt)
    headers = {"Content-Disposition": "attachment; filename=receipt.pdf"}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)

@router.post("/invoices/generate-pdf", response_class=StreamingResponse)
async def generate_invoice_pdf(invoice: InvoiceData):
    pdf_buffer = create_invoice_pdf(invoice)
    headers = {"Content-Disposition": "attachment; filename=invoice.pdf"}
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers=headers)
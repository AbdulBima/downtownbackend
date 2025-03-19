from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime

# Pydantic Model for User
class UserSerializer(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=6, description="User's password (min 6 characters)")



# ✅ Customer Serializer (Address Removed)
class CustomerSerializer(BaseModel):
    name: str = Field(..., description="Full name of the customer")
    contact: str = Field(..., description="Customer's contact number")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Date of record creation")


class LoginRequest(BaseModel):
    email: str
    password: str
    
    
class ReceiptCustomerData(BaseModel):
    name: str
    contact: str
    address: str

    
class ReceiptData(BaseModel):
    id: str
    date: str  # e.g. "YYYY-MM-DD"
    customer: ReceiptCustomerData
    productType: str  # e.g. "pp" or "injection"
    processType: List[str]  # e.g. ["R", "B"]
    kgIn: float
    kgOut: float
    status: str
    recycler: Optional[str] = None
    amount: Optional[int] = None


class CustomerData(BaseModel):
    name: str
    contact: str
    address: str

class InvoiceData(BaseModel):
    id: str
    date: str  # e.g., "YYYY-MM-DD"
    customer: CustomerData
    productType: str
    processType: List[str]
    kgIn: float
    kgOut: Optional[float] = 0.0
    status: str
    amount: float
    
    
class SaleData(BaseModel):
    id: str
    date: str  # "YYYY-MM-DD"
    customer: CustomerData
    productType: str
    kg: float
    amount: float
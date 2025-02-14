from pydantic import BaseModel, Field, EmailStr
from typing import List
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
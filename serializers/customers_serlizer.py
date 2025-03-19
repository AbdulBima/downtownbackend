from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CustomerSerializer(BaseModel):
    id: Optional[str] = Field(None, description="MongoDB ObjectId of the customer")
    customer_id: Optional[str] = Field(None, description="Short customer ID (6 alphanumeric characters)")
    name: str = Field(..., description="Full name of the customer")
    contact: str = Field(..., description="Customer's contact number")
    address: str = Field(..., description="Customer's address")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Creation timestamp")

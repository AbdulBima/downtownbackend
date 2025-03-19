from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional

# ------------------------
# Pydantic Models / Schemas
# ------------------------
class SaleCreateSerializer(BaseModel):
    date: str = Field(..., description="Sale date (YYYY-MM-DD)")
    customer: dict = Field(..., description="Customer data (including id, customer_id, name, etc.)")
    productType: str = Field(..., description="Product type")
    kg: float = Field(..., description="Weight in Kg")
    amount: float = Field(..., description="Sale amount")

class SaleSerializer(SaleCreateSerializer):
    id: str = Field(..., description="Sale ID")
    created_at: Optional[datetime] = None

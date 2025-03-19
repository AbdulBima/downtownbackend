
from pydantic import BaseModel, Field
from typing import Optional

from config.database import db
from serializers.customers_serlizer import CustomerSerializer  # Existing customer serializer


# Updated Purchase Serializer
class PurchaseSerializer(BaseModel):
    id: Optional[str] = Field(None, description="Purchase ID")
    date: str = Field(..., description="Purchase date in format YYYY-MM-DD")
    customer: Optional[CustomerSerializer] = Field(
        None, description="Customer details (pass this field if available)"
    )
    productType: str = Field(..., description="Product type")
    kg: float = Field(..., description="Weight in Kg")
    amount: float = Field(..., description="Purchase amount")


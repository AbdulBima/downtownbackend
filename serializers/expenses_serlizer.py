from pydantic import BaseModel, Field
from typing import  Optional
from enum import Enum


# ------------------------
# Define an Enum for Expense Categories
# ------------------------
class ExpenseCategory(str, Enum):
    UTILITIES = "Utilities"
    MAINTENANCE = "Maintenance"
    LABOUR = "Labour"
    OTHERS = "Others"


# ------------------------
# Pydantic Expense Serializer with Enum for Category
# ------------------------
class ExpenseSerializer(BaseModel):
    id: Optional[str] = Field(None, description="Expense ID")
    date: str = Field(..., description="Expense date in format YYYY-MM-DD")
    category: ExpenseCategory = Field(..., description="Expense category")
    description: str = Field(..., description="Expense description")
    amount: float = Field(..., description="Expense amount")
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from serializers.expenses_serlizer import ExpenseSerializer

router = APIRouter()

from config.database import db

# ------------------------
# Helper Function
# ------------------------
def expense_helper(expense) -> dict:
    """Convert a MongoDB expense document to a dict matching our serializer."""
    return {
        "id": str(expense["_id"]),
        "date": expense["date"],
        "category": expense["category"],
        "description": expense["description"],
        "amount": expense["amount"],
    }


# ------------------------
# MongoDB Connection Setup
# ------------------------

expenses_collection = db.downtown_expenses  # Collection for expenses

class PaginatedExpenses(BaseModel):
    total: int
    expenses: List[ExpenseSerializer]

@router.get("/get-expenses", response_model=PaginatedExpenses)
async def get_expenses(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve a list of expenses with pagination.
    """
    total = await expenses_collection.count_documents({})
    expenses_cursor = expenses_collection.find().skip(skip).limit(limit)
    expenses = [expense_helper(expense) async for expense in expenses_cursor]
    return {"total": total, "expenses": expenses}

# ------------------------
# POST Endpoint: Create Expense
# ------------------------
@router.post("/create-expenses", response_model=ExpenseSerializer)
async def create_expense(expense: ExpenseSerializer):
    """
    Create a new expense.
    """
    expense_data = expense.dict(exclude={"id"})
    result = await expenses_collection.insert_one(expense_data)
    if result.inserted_id:
        new_expense = await expenses_collection.find_one({"_id": result.inserted_id})
        return expense_helper(new_expense)
    raise HTTPException(status_code=500, detail="Failed to create expense")

# ------------------------
# DELETE Endpoint: Delete Expense
# ------------------------
@router.delete("/del/{expense_id}", response_model=dict)
async def delete_expense(expense_id: str):
    """
    Delete an expense by its ID.
    """
    try:
        obj_id = ObjectId(expense_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid expense ID format")
    
    result = await expenses_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"message": "Expense deleted successfully", "id": expense_id}

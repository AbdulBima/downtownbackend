from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

import string, secrets
from bson import ObjectId

from config.database import db
from serializers.customers_serlizer import CustomerSerializer

router = APIRouter()

def generate_customer_id(length: int = 6) -> str:
    """Generate a secure random 6-character alphanumeric customer ID."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Utility function to convert a MongoDB document to a dict for our serializer.
def customer_helper(customer) -> dict:
    return {
        "id": str(customer["_id"]),
        "customer_id": customer.get("customer_id", ""),
        "name": customer.get("name", ""),
        "contact": customer.get("contact", ""),
        "address": customer.get("address", ""),
        "created_at": customer.get("created_at"),
    }

customers_collection = db.downtown_customers


@router.get("/get-customers", response_model=dict)
async def get_customers(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve customers with pagination.
    The endpoint returns the total count and a list of customers.
    """
    customers_cursor = customers_collection.find().skip(skip).limit(limit)
    customers_list = [customer_helper(customer) async for customer in customers_cursor]
    total_count = await customers_collection.count_documents({})
    return {
        "total": total_count,
        "count": len(customers_list),
        "customers": customers_list
    }

@router.post("/create-customers", response_model=dict)
async def create_customer(customer: CustomerSerializer):
    """
    Create a new customer.
    The endpoint expects a customer object (without an id or customer_id)
    and returns both the MongoDB id and the new customer_id.
    """
    customer_data = customer.model_dump(exclude={"id", "created_at", "customer_id"})
    print("Serialized customer_data:", customer_data)  # Debug log
    customer_data["created_at"] = datetime.now(timezone.utc)


    # Try to generate a unique customer_id.
    max_attempts = 5
    for _ in range(max_attempts):
        candidate = generate_customer_id()
        # Check if the candidate exists.
        existing = await customers_collection.find_one({"customer_id": candidate})
        if not existing:
            customer_data["customer_id"] = candidate
            break
    else:
        raise HTTPException(status_code=500, detail="Failed to generate unique customer_id")
        
    result = await customers_collection.insert_one(customer_data)
    if result.inserted_id:
        return {
            "message": "Customer created successfully",
            "id": str(result.inserted_id),
            "customer_id": customer_data["customer_id"]
        }
    raise HTTPException(status_code=500, detail="Failed to create customer")

@router.put("/update/{customer_id}", response_model=dict)
async def update_customer(customer_id: str, customer: CustomerSerializer):
    """
    Update an existing customer by customer_id.
    Only provided fields will be updated.
    """
    updated_data = customer.model_dump(exclude_unset=True, exclude={"id", "created_at", "customer_id"})
    if updated_data:
        result = await customers_collection.update_one({"customer_id": customer_id}, {"$set": updated_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer updated successfully", "customer_id": customer_id}

@router.delete("/del/{customer_id}", response_model=dict)
async def delete_customer(customer_id: str):
    """
    Delete a customer by customer_id.
    """
    result = await customers_collection.delete_one({"customer_id": customer_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully", "customer_id": customer_id}

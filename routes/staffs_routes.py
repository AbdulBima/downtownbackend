from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import random
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

from serializers.staff_serializer import StaffSerializer, UpdateStaffSerializer

router = APIRouter()

# ------------------------
# Helper Function: Convert MongoDB Document
# ------------------------
def staff_helper(staff) -> dict:
    """Convert a MongoDB staff document to a dict matching our serializer."""
    return {
        "id": str(staff["_id"]),
        "staff_id": staff["staff_id"],
        "name": staff["name"],
        "phone": staff["phone"],
        "dateAdded": staff["dateAdded"],
    }

from config.database import db  # MongoDB connection
staffs_collection = db.downtown_staffs  # Collection for staff records

# ------------------------
# Helper Function: Generate Unique Staff ID
# ------------------------
async def generate_unique_staff_id(max_attempts: int = 5) -> int:
    """
    Generate a unique 6-digit staff_id that does not exist in the database.
    Raises HTTPException if unable to generate a unique ID after max_attempts.
    """
    for _ in range(max_attempts):
        new_staff_id = random.randint(100000, 999999)
        existing_staff = await staffs_collection.find_one({"staff_id": new_staff_id})
        if not existing_staff:
            return new_staff_id
    raise HTTPException(status_code=500, detail="Failed to generate a unique staff ID")

# ------------------------
# GET Endpoint: Retrieve Staff
# ------------------------
@router.get("/get-staffs", response_model=List[StaffSerializer])
async def get_staffs(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve a list of staff members with pagination.
    """
    staffs_cursor = staffs_collection.find().skip(skip).limit(limit)
    staffs = [staff_helper(staff) async for staff in staffs_cursor]
    return staffs

# ------------------------
# POST Endpoint: Create Staff
# ------------------------
@router.post("/create-staff", response_model=StaffSerializer)
async def create_staff(staff: StaffSerializer):
    """
    Create a new staff member.
    The `id` and `staff_id` fields are excluded because they are auto-generated.
    """
    # Exclude fields that are auto-generated
    staff_data = staff.model_dump(exclude={"id", "staff_id"})
    # Generate a unique 6-digit staff_id
    staff_data["staff_id"] = await generate_unique_staff_id()
    result = await staffs_collection.insert_one(staff_data)
    if result.inserted_id:
        new_staff = await staffs_collection.find_one({"_id": result.inserted_id})
        return staff_helper(new_staff)
    raise HTTPException(status_code=500, detail="Failed to create staff")


@router.put("/update/{staff_id}", response_model=dict)
async def update_staff(staff_id: int, staff: UpdateStaffSerializer):
    """
    Update an existing staff member by staff_id.
    Only provided fields will be updated.
    """
    updated_data = staff.model_dump(exclude_unset=True)
    if updated_data:
        result = await staffs_collection.update_one(
            {"staff_id": staff_id}, {"$set": updated_data}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Staff not found")
        return {"message": "Staff updated successfully", "staff_id": staff_id}
    raise HTTPException(status_code=400, detail="No valid fields provided for update")



# ------------------------
# DELETE Endpoint: Delete Staff
# ------------------------
@router.delete("/del/{staff_id}", response_model=dict)
async def delete_staff(staff_id: str):
    """
    Delete a staff member by their MongoDB ID.
    """
    try:
        obj_id = ObjectId(staff_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid staff ID format")
    
    result = await staffs_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Staff not found")
    return {"message": "Staff deleted successfully", "id": staff_id}


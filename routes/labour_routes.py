import calendar
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
import calendar

# Import serializers as needed
from serializers.prices_serilizer import LabourPrices
from serializers.staff_serializer import StaffSerializer

router = APIRouter()

# ------------------------
# Pydantic Models / Serializers
# ------------------------

class StaffLabourSummary(BaseModel):
    id: str = Field(..., description="Staff ID")
    name: str = Field(..., description="Staff name")
    totalKg: float = Field(..., description="Total Kg processed")
    amountRecycling: float = Field(..., description="Amount due for Labour Recycling")
    amountBlending: float = Field(..., description="Amount due for Labour Crushing")
    amountCrushingWaste: float = Field(..., description="Amount due for Labour Crushing Waste")
    amountCrushingSack: float = Field(..., description="Amount due for Labour Crushing Sack")
    totalAmountDue: float = Field(..., description="Total amount due")

class PaginatedStaffLabourSummary(BaseModel):
    total: int = Field(..., description="Total number of staff records")
    staff: List[StaffLabourSummary]

class LabourRecordSerializer(BaseModel):
    id: Optional[str] = Field(None, description="Unique Labour Record ID")
    staffs: List[StaffSerializer] = Field(..., description="List of staff involved")
    kg: float = Field(..., description="Weight in kg")
    date: str = Field(..., description="Date in format YYYY-MM-DD")
    time: str = Field(..., description="Shift time: 'morning' or 'night'")
    labourType: str = Field(
        ...,
        description="Type of labour: 'labour crushing waste', 'labour crushing', 'labour recycling'",
    )
    amount: Optional[float] = Field(0.0, description="Computed total amount for labour")
    memberShare: Optional[float] = Field(0.0, description="Computed share per member")


class PaginatedLabourRecords(BaseModel):
    total: int
    records: List[LabourRecordSerializer]

class StaffWageSummary(BaseModel):
    id: str = Field(..., description="Staff ID")
    name: str = Field(..., description="Staff name")
    totalWage: float = Field(..., description="Total wage amount")
    breakdown: Dict[str, float] = Field(
        ..., description="Wage breakdown by labour type (e.g., 'labour recycling', 'labour crushing', etc.)"
    )

# ------------------------
# Database Connection
# ------------------------
from config.database import db  # Example: db = AsyncIOMotorClient(MONGO_URI).mydatabase

# Define collections (remove duplicates)
staff_collection = db.downtown_staffs
labour_records_collection = db.downtown_labour_records
price_settings_collection = db.price_settings_collection

# ------------------------
# Endpoints
# ------------------------

@router.get("/get-labours", response_model=PaginatedLabourRecords)
async def get_labour_records(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    """
    Retrieve a list of labour records for the current month with pagination,
    ordered with the latest document first.
    """
    # Determine first and last day of the current month
    now = datetime.now()
    first_day = datetime(now.year, now.month, 1)
    last_day = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
    first_day_str = first_day.strftime("%Y-%m-%d")
    last_day_str = last_day.strftime("%Y-%m-%d")
    
    # Filter labour records for current month
    query = {"date": {"$gte": first_day_str, "$lte": last_day_str}}
    total = await labour_records_collection.count_documents(query)
    
    # Sort descending by date (latest first), then apply pagination
    records_cursor = (
    labour_records_collection.find(query)
    .sort("_id", -1)  # Sort by _id descending to get the newest first
    .skip(skip)
    .limit(limit)
)

    
    labour_records = []
    async for record in records_cursor:
        record["id"] = str(record["_id"])
        record.pop("_id", None)
        labour_records.append(LabourRecordSerializer(**record))
        
    return {"total": total, "records": labour_records}


@router.post("/create-labours", response_model=LabourRecordSerializer)
async def create_labour_record(record: LabourRecordSerializer):
    record_dict = record.model_dump(exclude_unset=True)
    
    # If amount or memberShare are not provided, compute them
    if "amount" not in record_dict or "memberShare" not in record_dict:
        price_doc = await price_settings_collection.find_one({})
        if not price_doc:
            raise HTTPException(status_code=404, detail="Labour prices not found")
        labour_prices = price_doc.get("labour_prices", {})
        
        kg = record_dict.get("kg", 0)
        labour_type_str = record_dict.get("labourType", "").lower()
        pricePerKg = 0
        if "recycling" in labour_type_str:
            pricePerKg = labour_prices.get("recycling", 0)
        elif "blending" in labour_type_str:
            pricePerKg = labour_prices.get("blending", 0)
        elif "crushing waste" in labour_type_str:
            pricePerKg = labour_prices.get("crushingWaste", 0)
        elif "crushing sack" in labour_type_str:
            pricePerKg = labour_prices.get("crushingSack", 0)
        
        # Compute the total amount based on kg and price per kg
        amount = pricePerKg * kg
        
        # Calculate member share as the total amount divided by the number of attached staffs
        staffs = record_dict.get("staffs", [])
        num_staff = len(staffs)
        memberShare = amount / num_staff if num_staff > 0 else 0
        
        record_dict["amount"] = amount
        record_dict["memberShare"] = memberShare

    result = await labour_records_collection.insert_one(record_dict)
    if result.inserted_id:
        new_record = await labour_records_collection.find_one({"_id": result.inserted_id})
        new_record["id"] = str(new_record["_id"])
        new_record.pop("_id", None)
        return LabourRecordSerializer(**new_record)
    raise HTTPException(status_code=500, detail="Failed to create labour record")

@router.delete("/del/{labour_id}", response_model=dict)
async def delete_labour_record(labour_id: str):
    """
    Delete a labour record by its ID.
    """
    try:
        result = await labour_records_collection.delete_one({"_id": ObjectId(labour_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid labour ID format")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Labour record not found")
    return {"message": "Labour record deleted", "id": labour_id}


@router.get("/monthly-wages", response_model=List[StaffWageSummary])
async def get_monthly_wages():
    """
    Retrieve each staff member's total amount due (wage) for the current month,
    using only labour records and the staff collection.
    """
    # Calculate the first and last day of the current month.
    now = datetime.now()
    first_day = datetime(now.year, now.month, 1)
    last_day = datetime(now.year, now.month, calendar.monthrange(now.year, now.month)[1])
    first_day_str = first_day.strftime("%Y-%m-%d")
    last_day_str = last_day.strftime("%Y-%m-%d")
    
    # Query labour records for the current month.
    labour_cursor = labour_records_collection.find({
        "date": {"$gte": first_day_str, "$lte": last_day_str}
    })
    
    # Aggregate wages by staff with breakdown by labour type.
    staff_wages: Dict[str, Dict[str, Any]] = {}
    async for record in labour_cursor:
        member_share = record.get("memberShare", 0)
        labour_type = record.get("labourType", "").strip().lower()
        for staff in record.get("staffs", []):
            staff_id = staff.get("id") or staff.get("_id")
            if not staff_id:
                continue
            staff_id = str(staff_id)
            if staff_id not in staff_wages:
                staff_wages[staff_id] = {"totalWage": 0.0, "breakdown": {}}
            staff_wages[staff_id]["totalWage"] += member_share
            current = staff_wages[staff_id]["breakdown"].get(labour_type, 0.0)
            staff_wages[staff_id]["breakdown"][labour_type] = current + member_share
    
    # Fetch all staff details from the staff collection.
    staff_docs = await staff_collection.find().to_list(length=None)
    
    # Build the response by merging staff details with the computed wages.
    result = []
    for staff in staff_docs:
        staff_id = staff.get("id") or staff.get("_id")
        if not staff_id:
            continue
        staff_id = str(staff_id)
        wage_data = staff_wages.get(staff_id, {"totalWage": 0.0, "breakdown": {}})
        result.append({
            "id": staff_id,
            "name": staff.get("name", ""),
            "totalWage": wage_data["totalWage"],   # now a float
            "breakdown": wage_data["breakdown"]      # breakdown as a dict
        })
    
    return result







@router.get("/wages", response_model=List[StaffLabourSummary])
async def get_wages():
    """
    Calculate wages per staff by:
      - Dividing each labour record's kg equally among its staff,
      - Multiplying that perstaff kg by the appropriate labour price,
      - And accumulating the total kg processed per staff.
      
    Labour type mapping:
      - "labour recycling" → uses labour_prices["recycling"] → field: amountRecycling
      - "labour crushing waste" → uses labour_prices["crushingWaste"] → field: amountCrushingWaste
      - "labour crushing sack" → uses labour_prices["crushingSack"] → field: amountCrushingSack
      - "labour crushing" → uses labour_prices["blending"] → field: amountBlending
    """
    # Fetch current labour prices
    price_doc = await price_settings_collection.find_one({})
    if not price_doc:
        raise HTTPException(status_code=404, detail="Labour prices not found")
    labour_prices = price_doc.get("labour_prices", {})

    # Initialize aggregator for each staff
    staff_summary: Dict[str, Dict[str, Any]] = {}

    # Iterate through all labour records
    labour_cursor = labour_records_collection.find({})
    async for record in labour_cursor:
        kg = record.get("kg", 0)
        staffs_in_record = record.get("staffs", [])
        num_staff = len(staffs_in_record)
        if num_staff == 0:
            continue  # Skip if no staff attached

        # Calculate kg allocated per staff for this record
        kg_per_staff = kg / num_staff

        # Standardize the labour type string
        labour_type_str = record.get("labourType", "").strip().lower()

        # Determine the labour price and the corresponding field key
        if "recycling" in labour_type_str:
            labour_price = labour_prices.get("recycling", 0)
            labour_field = "amountRecycling"
        elif "crushing waste" in labour_type_str:
            labour_price = labour_prices.get("crushingWaste", 0)
            labour_field = "amountCrushingWaste"
        elif "crushing sack" in labour_type_str:
            labour_price = labour_prices.get("crushingSack", 0)
            labour_field = "amountCrushingSack"
        elif "blending" in labour_type_str:
            labour_price = labour_prices.get("blending", 0)
            labour_field = "amountBlending"
        else:
            labour_price = 0
            labour_field = None

        # Calculate the amount due for this labour record per staff
        amount = kg_per_staff * labour_price

        # For each staff attached to the record, update their accumulations
        for staff in staffs_in_record:
            # Staff data may be stored as a dict with "id" or "_id" and "name"
            staff_id = staff.get("id") or staff.get("_id")
            if not staff_id:
                continue
            staff_id = str(staff_id)
            if staff_id not in staff_summary:
                staff_summary[staff_id] = {
                    "id": staff_id,
                    "name": staff.get("name", ""),
                    "totalKg": 0.0,
                    "amountRecycling": 0.0,
                    "amountBlending": 0.0,
                    "amountCrushingWaste": 0.0,
                    "amountCrushingSack": 0.0,
                }
            # Accumulate the kg processed by the staff
            staff_summary[staff_id]["totalKg"] += kg_per_staff
            # Accumulate the amount for the corresponding labour type
            if labour_field:
                staff_summary[staff_id][labour_field] += amount

    # Calculate the total amount due for each staff and build the final list
    result = []
    for s in staff_summary.values():
        s["totalAmountDue"] = (
            s["amountRecycling"]
            + s["amountBlending"]
            + s["amountCrushingWaste"]
            + s["amountCrushingSack"]
        )
        result.append(s)

    return result
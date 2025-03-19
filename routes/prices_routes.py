from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

from config.database import db
from serializers.prices_serilizer import CompanyPrices, LabourPrices, PriceSettingsSerializer  # MongoDB connection

router = APIRouter()


collection = db.price_settings_collection  # Collection to store the price settings


@router.get("/getprices", response_model=PriceSettingsSerializer)
async def get_price_settings():
    """
    Fetch the current price settings.
    If no settings exist, initialize with default values.
    """
    settings_doc = await collection.find_one({})
    
    return settings_doc

@router.put("/putprices", response_model=PriceSettingsSerializer)
async def update_price_settings(settings: PriceSettingsSerializer):
    """
    Update the price settings in the database.
    """
    result = await collection.update_one({}, {"$set": settings.model_dump()}, upsert=True)
    if result.modified_count == 0 and not result.upserted_id:
        raise HTTPException(status_code=500, detail="Failed to update price settings")
    return settings

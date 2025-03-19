from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient

from config.database import db
from serializers.prices_serilizer import CompanyPrices, LabourPrices, PriceSettingsSerializer  # MongoDB connection

router = APIRouter()


collection = db.price_settings_collection  # Collection to store the price settings


@router.get("/getprices", response_model=PriceSettingsSerializer)
async def get_price_settings():
    settings_doc = await collection.find_one({})

    if not settings_doc:
        # Return default values
        settings_doc = {
            "company_prices": {
                "recyclingKg": 0.0,
                "blendingKg": 0.0,
                "crushingKg": 0.0
            },
            "labour_prices": {
                "recycling": 0.0,
                "blending": 0.0,
                "crushingWaste": 0.0,
                "crushingSack": 0.0
            }
        }
    else:
        # Remove MongoDB _id if present
        settings_doc.pop("_id", None)

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

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

# Define Pydantic models for price settings
class CompanyPrices(BaseModel):
    recyclingKg: float = Field(..., description="Price per Kg for Recycling")
    blendingKg: float = Field(..., description="Price per Kg for Blending")
    crushingKg: float = Field(..., description="Price per Kg for Crushing")

class LabourPrices(BaseModel):
    recycling: float = Field(..., description="Labour price for Recycling")
    blending: float = Field(..., description="Labour price for Blending")
    crushingWaste: float = Field(..., description="Labour price for Crushing Waste")
    crushingSack: float = Field(..., description="Labour price for Crushing Sack")

class PriceSettingsSerializer(BaseModel):
    company_prices: CompanyPrices
    labour_prices: LabourPrices
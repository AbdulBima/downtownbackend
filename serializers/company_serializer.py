from enum import Enum
from typing import List
from pydantic import BaseModel, Field, EmailStr, FieldValidationInfo, field_validator


# Enums for Country and State
class CountryEnum(str, Enum):
    NIGERIA = "NG"
    GHANA = "GH"
    SOUTH_AFRICA = "ZA"
    KENYA = "KE"


class StateEnum(str, Enum):
    LAGOS = "Lagos"
    ABUJA = "Abuja"
    KADUNA = "Kaduna"
    KANO = "Kano"
    GREATER_ACCRA = "Greater Accra"
    ASHANTI = "Ashanti"
    WESTERN = "Western"
    WESTERN_CAPE = "Western Cape"
    KWAZULU_NATAL = "KwaZulu-Natal"
    GAUTENG = "Gauteng"
    NAIROBI = "Nairobi"
    MOMBASA = "Mombasa"
    KISUMU = "Kisumu"


# Serializer with Field Validator
class CompanyCreateRequest(BaseModel):
    companyName: str = Field(..., description="Name of the company")
    companyEmail: EmailStr = Field(..., description="Company email address")
    companyPassword: str = Field(..., description="Company password")
    answer1: str = Field(..., description="Answer to the first security question")
    answer2: str = Field(..., description="Answer to the second security question")
    contactPerson: str = Field(..., description="Name of the contact person")
    cac: str = Field(..., description="CAC Registration Number")
    phone: str = Field(..., description="Phone number for contact")
    country: CountryEnum = Field(..., description="Country where the company operates (ISO Code)")
    state: StateEnum = Field(..., description="State/region within the country")

    # Field validator for state
    @field_validator("state")
    def validate_state(cls, state: str, info: FieldValidationInfo) -> str:
        """Ensure the state belongs to the selected country."""
        country = info.data.get("country")
        country_states = {
            "NG": ["Lagos", "Abuja", "Kaduna", "Kano"],
            "GH": ["Greater Accra", "Ashanti", "Western"],
            "ZA": ["Western Cape", "KwaZulu-Natal", "Gauteng"],
            "KE": ["Nairobi", "Mombasa", "Kisumu"],
        }

        if country and state not in country_states.get(country.value, []):
            raise ValueError(f"Invalid state '{state}' for country '{country}'")
        return state

class CompanySerializer(BaseModel):
    companyName: str = Field(..., description="Name of the company")
    companyEmail: str = Field(..., description="Company email address")
    companyPassword: str = Field(..., description="Password for company login")
    authKeys: List[str] = Field(..., description="Authentication keys for the company")
    # Each answer is now a separate field
    answer1: str = Field(..., description="Answer to the first security question")
    answer2: str = Field(..., description="Answer to the second security question")
    agencyName: str = Field(..., description="Name of the government agency")
    contactPerson: str = Field(..., description="Name of the contact person")
    cac: str = Field(..., description="CAC Registration Number")
    phone: str = Field(..., description="Phone number for contact") 

class CompanyResponseSerializer(BaseModel):
    companyId: str = Field(..., description="Unique ID for the company")
    companyName: str = Field(..., description="Name of the company")
    companyEmail: str = Field(..., description="Company email address")
    active: bool = Field(..., description="Indicates if the company is active")
   
# Define the response model for returning the company API key
class CompanyAPIKeyResponse(BaseModel):
    apiKey: str
      
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class PasswordChangeRequest(BaseModel):
    currentPassword: str
    newPassword: str

  
class CompanyUpdateRequest(BaseModel):
    companyName: str = Field(..., description="Updated name of the company")
    companyEmail: EmailStr = Field(..., description="Updated email address of the company")
    contactPerson: str = Field(..., description="Updated name of the contact person")
    phone: str = Field(..., description="Updated phone number for contact")
    class Config:
        # This allows the model to ignore missing fields and set them as optional
        str_strip_whitespace = True

class CompanyDetailResponse(BaseModel):
    companyId: str = Field(..., description="Unique ID for the company")
    companyName: str = Field(..., description="Name of the company")
    companyEmail: EmailStr = Field(..., description="Email address of the company")
    contactPerson: str = Field(..., description="Name of the contact person")
    cac: str = Field(..., description="CAC Registration Number")
    phone: str = Field(..., description="Phone number of the company")
    country: str = Field(..., description="Country where the company is located (ISO code)")
    state: str = Field(..., description="State/region within the country")
    active: bool = Field(..., description="Indicates if the company is active")
    dateCreated: str = Field(..., description="Date the company was created")

    class Config:
        str_strip_whitespace = True
        
class UpdateStatusRequest(BaseModel):
    active: bool = Field(..., description="Indicates if the company should be active or inactive")


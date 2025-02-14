
from pydantic import BaseModel, Field
from datetime import datetime

class Admission(BaseModel):
    clinicId: str = Field(..., description="Clinic ID (foreign key)")
    time: datetime = Field(..., description="Admission timestamp")
    gender: str = Field(..., description="Gender of the patient", pattern="^(Male|Female)$")
    ageGroup: str = Field(..., description="Age group", pattern="^(Adult|Child)$")
    reason: str = Field(..., description="Reason for admission")
    submitterID: str = Field(..., description="Submitter's user ID")
    companyId: str = Field(..., description="ID of the company")
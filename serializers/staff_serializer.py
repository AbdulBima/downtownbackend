from pydantic import BaseModel, Field
from typing import Optional

# ------------------------
# Pydantic Staff Serializer
# ------------------------
class StaffSerializer(BaseModel):
    id: Optional[str] = Field(None, description="MongoDB generated staff ID")
    staff_id: Optional[int] = Field(None, description="6-digit staff identifier")
    name: str = Field(..., description="Staff name")
    phone: str = Field(..., description="Staff phone number")
    dateAdded: str = Field(
        ..., description="Date the staff was added in format YYYY-MM-DD"
    )

class UpdateStaffSerializer(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
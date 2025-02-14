from pydantic import BaseModel, Field
from typing import Optional, List

class Company(BaseModel):
    companyId: str = Field(..., description="Unique ID for the company")
    companyEmail: str = Field(..., description="Email address of the company")
    companyPassword: str = Field(..., description="Password for the company account")
    companyAuthKeys: Optional[List[str]] = Field(default=[], description="Authentication keys for the company")
    securityQandS: Optional[List[dict]] = Field(default=[], description="Security questions and answers")

from fastapi import Depends, HTTPException, Request
from config.database import db

async def api_key_dependency(request: Request):
    api_key = request.headers.get("X-API-KEY")
    if not api_key:
        raise HTTPException(status_code=403, detail="API key is missing")

    # Check if the API key belongs to a company
    company = await db["companies"].find_one({"companyAuthKeys": api_key})
    if company:
        request.state.companyId = company["companyId"]
        request.state.userType = "company"
        return  # Valid API key for company

    # Check if the API key belongs to a staff
    staff = await db["staff"].find_one({"staffApiKey": api_key})
    if staff:
        request.state.staffId = staff["staffId"]
        request.state.companyId = staff["companyId"]
        request.state.userType = "staff"
        return  # Valid API key for staff

    raise HTTPException(status_code=403, detail="Invalid API key")

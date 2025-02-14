
from datetime import datetime, timedelta, timezone


import os
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

import jwt
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel, EmailStr
from config.database import db  # MongoDB connection
from passlib.context import CryptContext


from serializers.user_serlizer import CustomerSerializer, LoginRequest

router = APIRouter()
users_collection =  db.downtown_users
downtown_customers_collection = db.downtown_customers


# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User model
class UserSerializer(BaseModel):
    name: str
    email: EmailStr
    password: str

# ✅ MongoDB Helper Function to Convert ObjectId
def customer_helper(customer) -> dict:
    return {
        "id": str(customer["_id"]),
        "name": customer["name"],
        "contact": customer["contact"],
        "created_at": customer["created_at"]
    }
    
# Helper function to hash password
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Security Config (Load values from .env)
SECRET_KEY = os.getenv("SECRET_KEY", "mistaemonma")  # Default to "mistaemonma" if SECRET_KEY is not set in .env
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # Default to "HS256" if ALGORITHM is not set in .env
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))  # Default to 30 minutes if not set

# Initialize OAuth2PasswordBearer for token extraction from request header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Function to verify password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Function to create JWT token
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire =  datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
def verify_jwt_token(token: str) -> dict:
    try:
        # Decode the JWT token and verify it
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # You can also check for expiration time here
        if payload["exp"] < datetime.now(timezone.utc).timestamp():
            raise HTTPException(status_code=401, detail="Token has expired")
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Endpoint to verify the token and return True if valid
@router.get("/verify-token", response_model=dict)
async def verify_token(token: str = Depends(oauth2_scheme)):
    is_valid = verify_jwt_token(token)
    if is_valid:
        return {"valid": True}
    else:
        raise HTTPException(status_code=401, detail="Invalid token")
# POST - Create User
@router.post("/users/create")
async def create_user(user: UserSerializer):
    # Check if email already exists
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    hashed_password = hash_password(user.password)
    
    # Create user document
    user_data = {
        "email": user.email,
        "password": hashed_password,
        "created_at": datetime.now(timezone.utc)


    }

    # Insert into MongoDB
    result = await users_collection.insert_one(user_data)
    
    if result.inserted_id:
        return {"message": "User created successfully", "id": str(result.inserted_id)}
    
    raise HTTPException(status_code=500, detail="Failed to create user")


# POST - Login User
@router.post("/users/login")
async def login_user(login_request: LoginRequest):
    # Check if user exists
    user = await users_collection.find_one({"email": login_request.email})  
    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Verify password
    if not verify_password(login_request.password, user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    # Create JWT token
    access_token = create_access_token(data={"sub": user["email"]})

    return {"access_token": access_token, "token_type": "bearer"}

# 🚀 **Create Customer**
@router.post("/create/customers", response_model=dict)
async def create_customer(customer: CustomerSerializer):
    customer_data = customer.model_dump()
    customer_data["created_at"] = datetime.utcnow()

    result = await downtown_customers_collection.insert_one(customer_data)
    if result.inserted_id:
        return {"message": "Customer created successfully", "id": str(result.inserted_id)}
    
    raise HTTPException(status_code=500, detail="Failed to create customer")

# 🔍 **Get Customers with Pagination**
@router.get("/get/customers", response_model=dict)
async def get_customers(skip: int = Query(0, ge=0), limit: int = Query(10, le=100)):
    customers_cursor = downtown_customers_collection.find().skip(skip).limit(limit)
    customers_list = [customer_helper(customer) async for customer in customers_cursor]
    
    total_count = await downtown_customers_collection.count_documents({})
    
    return {
        "total": total_count,
        "count": len(customers_list),
        "customers": customers_list
    }

# 🔄 **Update Customer**
@router.put("/customers/update/{customer_id}", response_model=dict)
async def update_customer(customer_id: str, customer_update: CustomerSerializer):
    try:
        customer_obj_id = ObjectId(customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    updated_data = customer_update.model_dump(exclude_unset=True)  # Only update provided fields
    updated_data["updated_at"] = datetime.timezone.utc()

    result = await downtown_customers_collection.update_one(
        {"_id": customer_obj_id},
        {"$set": updated_data}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found or no changes made")

    return {"message": "Customer updated successfully", "id": customer_id}


@router.get("/customers/get/{customer_id}", response_model=dict)
async def get_customer_by_id(customer_id: str):
    try:
        # Try converting the customer_id to ObjectId
        customer_obj_id = ObjectId(customer_id)
    except Exception:
        # If it fails, raise an error for invalid ObjectId format
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    # Find the customer by ID in the MongoDB collection
    customer = await downtown_customers_collection.find_one({"_id": customer_obj_id})

    # If no customer is found, raise a 404 error
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Return the customer data
    return customer_helper(customer)


# ❌ **Delete Customer**
@router.delete("/customers/{customer_id}", response_model=dict)
async def delete_customer(customer_id: str):
    try:
        customer_obj_id = ObjectId(customer_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    result = await downtown_customers_collection.delete_one({"_id": customer_obj_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")

    return {"message": "Customer deleted successfully", "id": customer_id}
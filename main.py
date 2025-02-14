# Your imports
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
from starlette.middleware.trustedhost import TrustedHostMiddleware
# from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse 
from routes.user_routes import router as users_router
from dependencies import api_key_dependency
from starlette.middleware.base import BaseHTTPMiddleware

# Initialize FastAPI app
app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Allow these methods
    allow_headers=["*"],  # Allow all headers
)

app.add_middleware(GZipMiddleware) 
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Adjust as needed
# app.add_middleware(SessionMiddleware, secret_key="your_secret_key")


# app.add_middleware(AuthMiddleware)  

# Register all routers
app.include_router(users_router, prefix="/api/uscu", tags=["USCU"])

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to the FastAPI MongoDB application!"}

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}")
    return JSONResponse(status_code=500, content={"message": "An internal error occurred. Please try again later."})

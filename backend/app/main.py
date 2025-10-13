from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.auth import router as auth_router
from app.api.location import router as location_router
from app.api.satellites import router as satellites_router
from app.config import settings
from app.middleware.auth_middleware import AuthenticationMiddleware, RateLimitMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Satellite Tracker API",
    description="API for tracking satellites and managing user favorites",
    version="1.0.0"
)

# Add authentication middleware (order matters - add before CORS)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=10, window_seconds=300)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(location_router, prefix=settings.api_v1_prefix)
app.include_router(satellites_router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root():
    return {"message": "Satellite Tracker API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
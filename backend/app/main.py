from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.config import settings

app = FastAPI(
    title="Satellite Tracker API",
    description="API for tracking satellites and managing user favorites",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)

@app.get("/")
async def root():
    return {"message": "Satellite Tracker API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
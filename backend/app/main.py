# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Video Automation API",
    description="Backend API for Video Automation System",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.api import topics, scripts, projects, materials, video, llm
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(scripts.router, prefix="/api/scripts", tags=["scripts"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(materials.router, prefix="/api/materials", tags=["materials"])
app.include_router(video.router, prefix="/api/video", tags=["video"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])

# TODO: Include routers when ready
# from app.api import tasks
# app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Video Automation API",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "redis": "not_checked"
    }

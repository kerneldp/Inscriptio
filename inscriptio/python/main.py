from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from settings import settings
import models

# Create all tables on startup
Base.metadata.create_all(bind=engine)

# Import routers after table creation (avoids circular-import issues)
from auth import router as auth_router
from dashboard import router as dashboard_router
from progress import router as progress_router
from history import router as history_router
from report import router as report_router

app = FastAPI(
    title=settings.api_title,
    description="Backend for AIKONIC — AI Dysgraphia Screening System",
    version=settings.api_version,
)

# Allow the HTML/JS frontend (served from the filesystem) to call this API.
# In production, replace allow_origins=["*"] with your actual frontend URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type", "*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(progress_router)
app.include_router(history_router)
app.include_router(report_router)


@app.get("/")
def root():
    return {"message": "Inscriptio API is running.", "version": "1.0.0"}

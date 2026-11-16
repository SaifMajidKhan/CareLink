from fastapi import FastAPI, HTTPException
from app.api.auth import router as auth_router
from app.api.medications import router as medications_router
from app.api.schedules import router as schedules_router
from app.api.adherence import router as adherence_router

from app.database import check_database_connection

app = FastAPI(
    title="CareLink API",
    description=(
        "Backend API for medication adherence "
        "and chronic-care coordination."
    ),
    version="0.2.0",
)
app.include_router(auth_router)
app.include_router(medications_router)
app.include_router(schedules_router)
app.include_router(adherence_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to CareLink API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "CareLink Backend",
    }


@app.get("/health/db")
def database_health_check():
    try:
        check_database_connection()

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )
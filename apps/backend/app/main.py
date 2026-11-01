from fastapi import FastAPI

app = FastAPI(
    title="CareLink API",
    description="Backend API for medication adherence and chronic-care coordination.",
    version="0.1.0",
)


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
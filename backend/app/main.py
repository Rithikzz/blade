from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.api import datasets, analyze

app = FastAPI(
    title="VERITAS Backend",
    description="Backend for VERITAS — Proof-Carrying Autonomous Data Analyst",
    version="0.1.0"
)

# Configure CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(datasets.router)
app.include_router(analyze.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to VERITAS Backend API"}

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "veritas-backend"
    }

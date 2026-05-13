from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.lifespan import lifespan
from app.api.v1.api import api_router

# FastAPI Uygulamasını Tanımla
app = FastAPI(
    title="Tyler MLB Predictor API",
    description="MLB Maç Analizi ve Değerli Bahis (Edge) Takip Sistemi",
    version="2.0.0",
    lifespan=lifespan
)

# 🌐 CORS: Allowed origins are read from CORS_ORIGINS env variable.
# Local dev default: "*"  |  Production: set to your Vercel URL on Render.
# Trailing slashes are stripped automatically (browsers never send them).
_raw_origins = os.getenv("CORS_ORIGINS", "*")
allowed_origins = [o.strip().rstrip("/") for o in _raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router'ını Uygulamaya Dahil Et
app.include_router(api_router, prefix="/api/v1")

# --- ENDPOINTS ---

@app.get("/")
async def root():
    return {
        "status": "online",
        "message": "MLB Predictor Engine is running. Visit /docs for API documentation.",
        "version": "2.0.0"
    }


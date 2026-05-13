from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.lifespan import lifespan
from app.api.v1.api import api_router

# FastAPI Uygulamasını Tanımla
app = FastAPI(
    title="Tyler MLB Predictor API",
    description="MLB Maç Analizi ve Değerli Bahis (Edge) Takip Sistemi",
    version="2.0.0",
    lifespan=lifespan
)

# 🌐 CORS: Frontend (React/Vite) bağlantısı için güvenlik izinleri
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Geliştirme aşamasında her yerden gelen isteğe izin veriyoruz
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


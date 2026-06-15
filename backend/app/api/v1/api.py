from fastapi import APIRouter
from app.api.v1.mlb import mlb_router
from app.api.v1.tennis import tennis_router

api_router = APIRouter()

# MLB Endpoints:
# Faz 4'e kadar API uyumluluğunu korumak için önek (prefix) olmadan ekliyoruz.
# Faz 4'te prefix="/mlb" olarak güncellenecektir.
api_router.include_router(mlb_router)

# Tennis Endpoints:
api_router.include_router(tennis_router)

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool
import os
import json
import asyncio
import time
from datetime import datetime

from app.services.prediction_runner import PredictionRunner

api_router = APIRouter()

# Global Yollar
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
PREDICTIONS_FILE = os.path.join(DATA_DIR, 'todays_predictions.json')
CACHE_EXPIRY_SECONDS = 3600  # 1 Saat

# Yarış Durumu (Race Condition) Kilidi
_update_lock = asyncio.Lock()

def _get_file_modified_time(filepath):
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    return "Bulunamadı"

@api_router.get("/predictions")
async def get_predictions():
    """Ana Dashboard Verisi. Güvenli Cache ve ThreadPool mantığı ile çalışır."""
    need_refresh = True
    
    if os.path.exists(PREDICTIONS_FILE):
        file_age = time.time() - os.path.getmtime(PREDICTIONS_FILE)
        if file_age < CACHE_EXPIRY_SECONDS:
            need_refresh = False

    if need_refresh:
        # Kilit mekanizması: Aynı anda sadece bir istek yenileme yapabilir
        async with _update_lock:
            # Double-check locking: Kilit beklerken başka biri veriyi güncellemiş olabilir
            if os.path.exists(PREDICTIONS_FILE) and (time.time() - os.path.getmtime(PREDICTIONS_FILE)) < CACHE_EXPIRY_SECONDS:
                need_refresh = False
            else:
                print("🔄 Veriler bayatlamış (veya yok), motor izole havuzda (threadpool) çalıştırılıyor...")
                runner = PredictionRunner()
                # Event Loop'u kilitlememek için ağır işlemi thread pool'a atıyoruz
                await run_in_threadpool(runner.run_daily_predictions)

    if not os.path.exists(PREDICTIONS_FILE):
        raise HTTPException(status_code=500, detail="Tahmin dosyası oluşturulamadı.")

    with open(PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return {
        "status": "success", 
        "cached": not need_refresh, 
        "data": data
    }

@api_router.get("/system-status")
async def get_system_status():
    """Sistemdeki verilerin ne zaman güncellendiğini gösterir."""
    return {
        "status": "success",
        "is_updating_now": _update_lock.locked(),
        "last_updates": {
            "predictions": _get_file_modified_time(PREDICTIONS_FILE),
            "live_stats": _get_file_modified_time(os.path.join(DATA_DIR, 'live_stats.json')),
            "pitcher_stats": _get_file_modified_time(os.path.join(DATA_DIR, 'pitcher_stats.json')),
            "live_odds": _get_file_modified_time(os.path.join(DATA_DIR, 'live_odds.json'))
        }
    }

@api_router.post("/refresh-data")
async def refresh_data():
    """Manuel Tetikleyici (Zorla Güncelle - ThreadPool Korumalı)."""
    # Zaten bir güncelleme çalışıyorsa reddet veya bekle
    if _update_lock.locked():
        raise HTTPException(status_code=429, detail="Sistem şu anda zaten güncelleniyor. Lütfen bekleyin.")
        
    try:
        async with _update_lock:
            runner = PredictionRunner()
            await run_in_threadpool(runner.run_daily_predictions)
        return {"status": "success", "message": "Tüm sistem verileri başarıyla zorla güncellendi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manuel güncelleme hatası: {str(e)}")
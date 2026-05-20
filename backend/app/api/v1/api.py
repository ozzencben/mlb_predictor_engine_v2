"""
API v1 Router

ÖNEMLİ MİMARİ KARAR:
  - /predictions endpoint'i ASLA veri kazıması (scraping) tetiklemez.
  - Veri kazıması sadece iki yoldan gerçekleşir:
      1. Otomatik: Her gün 00:00 ve 12:00 ET'de zamanlayıcı (scheduler.py) tarafından
      2. Manuel:   POST /refresh-data endpoint'i çağrıldığında

  Bu sayede kaç kullanıcı sayfayı kaç kez yenilerse yenilesin,
  hiçbir API kotası (The Odds API, Gemini vb.) harcamasına yol açılmaz.
"""

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool
import os
import json
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.services.prediction_runner import PredictionRunner

api_router = APIRouter()

# Global Yollar
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
PREDICTIONS_FILE = os.path.join(DATA_DIR, "todays_predictions.json")

# Manuel yenileme kilidi (Race condition önleyici)
_update_lock = asyncio.Lock()

ET_ZONE = ZoneInfo("America/New_York")
SCHEDULED_HOURS_ET = {0, 12}


def _get_file_modified_time(filepath: str) -> str:
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    return "Bulunamadı"


# ─────────────────────────────────────────────────────────────────────────────
# GET /predictions
# Sadece mevcut todays_predictions.json dosyasını okur ve döndürür.
# Asla kazıma (scraping) tetiklemez.
# ─────────────────────────────────────────────────────────────────────────────
@api_router.get("/predictions")
async def get_predictions():
    """
    Ana Dashboard Verisi.

    Davranış:
    - Dosya varsa → okur, döndürür. (Her zaman anlık, hiç gecikme yok)
    - Dosya yoksa → 503 döndürür (zamanlayıcı henüz çalışmamış demektir).

    ASLA veri kazıması başlatmaz. Sonsuz kullanıcı yenilemesi güvenlidir.
    """
    if not os.path.exists(PREDICTIONS_FILE):
        raise HTTPException(
            status_code=503,
            detail=(
                "Tahmin verisi henüz hazır değil. Sistem her gün 00:00 ve 12:00 ET'de "
                "otomatik olarak verileri günceller. Manuel güncelleme için "
                "POST /api/v1/refresh-data kullanabilirsiniz."
            ),
        )

    with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    last_modified = _get_file_modified_time(PREDICTIONS_FILE)
    return {
        "status": "success",
        "cached": True,
        "last_updated": last_modified,
        "data": data,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /system-status
# ─────────────────────────────────────────────────────────────────────────────
@api_router.get("/system-status")
async def get_system_status():
    """Sistemdeki verilerin ne zaman güncellendiğini gösterir."""
    return {
        "status": "success",
        "is_updating_now": _update_lock.locked(),
        "last_updates": {
            "predictions": _get_file_modified_time(PREDICTIONS_FILE),
            "live_stats": _get_file_modified_time(
                os.path.join(DATA_DIR, "live_stats.json")
            ),
            "pitcher_stats": _get_file_modified_time(
                os.path.join(DATA_DIR, "pitcher_stats.json")
            ),
            "live_odds": _get_file_modified_time(
                os.path.join(DATA_DIR, "live_odds.json")
            ),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /refresh-data
# Sadece yetkili manuel tetikleyici. Tüm pipeline'ı yeniden çalıştırır.
# ─────────────────────────────────────────────────────────────────────────────
@api_router.post("/refresh-data")
async def refresh_data():
    """
    Manuel Tetikleyici — Zorla Güncelle.

    Kullanım: Cron dışında acil güncelleme gerektiğinde kullanılır.
    Kilit mekanizması ile aynı anda birden fazla güncelleme başlamaz.
    """
    if _update_lock.locked():
        raise HTTPException(
            status_code=429,
            detail="Sistem şu anda zaten güncelleniyor. Lütfen bekleyin.",
        )

    try:
        async with _update_lock:
            runner = PredictionRunner()
            await run_in_threadpool(runner.run_daily_predictions)
        return {
            "status": "success",
            "message": "Tüm sistem verileri başarıyla güncellendi.",
            "updated_at": _get_file_modified_time(PREDICTIONS_FILE),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Manuel güncelleme hatası: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GET /scheduler-status
# Zamanlayıcı bilgisi: bir sonraki çalışma zamanı ve güncel durum
# ─────────────────────────────────────────────────────────────────────────────
@api_router.get("/scheduler-status")
async def get_scheduler_status():
    """Zamanlayıcı hakkında bilgi döndürür."""
    now_et = datetime.now(ET_ZONE)
    
    # Bugünün ve yarının hedefleri için olası datetime adayları üretiyoruz
    candidates = []
    for day_offset in [0, 1]:
        base_date = now_et + timedelta(days=day_offset)
        for hour in SCHEDULED_HOURS_ET:
            candidate = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            candidates.append(candidate)
            
    # Sadece kesinlikle gelecekteki hedefleri seçiyoruz
    future_candidates = [c for c in candidates if c > now_et]
    
    # En yakın gelecek hedefini buluyoruz
    next_run = min(future_candidates)
    
    seconds_until_next = int(max((next_run - now_et).total_seconds(), 0))
    hours_until = seconds_until_next // 3600
    minutes_until = (seconds_until_next % 3600) // 60
    
    return {
        "status": "success",
        "current_time_et": now_et.strftime("%Y-%m-%d %H:%M:%S ET"),
        "scheduled_run_hours_et": sorted(SCHEDULED_HOURS_ET),
        "next_run_in": f"{hours_until}h {minutes_until}m",
        "next_run_at_et": next_run.strftime("%H:%M ET"),
        "is_scraping_now": _update_lock.locked(),
        "predictions_last_updated": _get_file_modified_time(PREDICTIONS_FILE),
        "scraping_policy": "Automatic: 00:00 & 12:00 ET daily. Manual: POST /refresh-data",
    }

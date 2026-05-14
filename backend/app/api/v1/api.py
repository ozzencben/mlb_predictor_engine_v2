from fastapi import APIRouter, HTTPException, Depends, Security, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

# Vercel Cron Güvenliği (Authorization: Bearer <TOKEN> formatında gelir)
security = HTTPBearer()
CRON_SECRET = os.getenv("CRON_SECRET", "gizli-cron-sifresi")

# Yarış Durumu (Race Condition) Kilidi
_update_lock = asyncio.Lock()

def verify_cron_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Vercel Cron veya Manuel İsteklerin Yetkisini Doğrular."""
    if credentials.credentials != CRON_SECRET:
        raise HTTPException(status_code=403, detail="Geçersiz Yetki. Bearer token hatalı.")
    return credentials.credentials

def _get_file_modified_time(filepath):
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    return "Bulunamadı"

async def _background_prediction_task():
    """
    Arka planda çalışacak asıl ağır iş yükü.
    Kilit mekanizmasını burada işletiyoruz ki API anında yanıt dönebilsin.
    """
    if _update_lock.locked():
        print("⏳ Güncelleme işlemi halihazırda devam ediyor. Bu tetikleme yoksayıldı.")
        return

    async with _update_lock:
        try:
            print("⚙️ Arka plan tahmin motoru başlatıldı...")
            runner = PredictionRunner()
            # Ağır (I/O ve CPU bound) işlemleri Event Loop'u kitlemeden çalıştır
            await run_in_threadpool(runner.run_daily_predictions)
            print("✅ Arka plan işlemi başarıyla tamamlandı.")
        except Exception as e:
            print(f"❌ Arka plan görev hatası: {e}")

@api_router.get("/predictions")
async def get_predictions():
    """
    SADECE OKUMA YAPAR. Ortalama yanıt süresi <10ms.
    Frontend (Next.js) burayı çağırır.
    """
    if not os.path.exists(PREDICTIONS_FILE):
        raise HTTPException(status_code=503, detail="Veriler henüz hazır değil. Lütfen biraz sonra tekrar deneyin.")

    with open(PREDICTIONS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return {
        "status": "success", 
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

# Vercel Cron varsayılan olarak GET isteği atar, bu yüzden GET yaptık.
# Manuel tetikleme (Postman vs.) için de kullanılabilir.
@api_router.get("/cron/refresh")
async def cron_refresh_data(
    background_tasks: BackgroundTasks, 
    _ = Depends(verify_cron_key)
):
    """
    Vercel Cron Hedefi. 
    İşlemi BackgroundTask'a atar ve Timeout yememek için anında '202 Accepted' döner.
    """
    if _update_lock.locked():
        return {"status": "ignored", "message": "Sistem zaten şu anda güncelleniyor."}

    # Görevi arka plana ekle
    background_tasks.add_task(_background_prediction_task)
    
    return {
        "status": "accepted", 
        "message": "Güncelleme komutu alındı, işlem arka planda başlatıldı."
    }
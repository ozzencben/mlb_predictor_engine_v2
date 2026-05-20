"""
FastAPI Lifespan Event Handler

Uygulama başlarken:
  1. Veri klasörünü hazırlar.
  2. Eğer todays_predictions.json yoksa veya 12 saatten eskiyse tek seferlik
     başlangıç kazıması başlatır (kullanıcıların ilk açılışta boş ekran görmemesi için).
  3. 00:00 & 12:00 ET otomatik zamanlayıcı görevini arka planda başlatır.

Uygulama kapanırken:
  - Arka plan görevi güvenli şekilde iptal edilir.
"""

import asyncio
import logging
import os
import time

from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

# Veri klasörünün yolu
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
PREDICTIONS_FILE = os.path.join(DATA_DIR, "todays_predictions.json")

# Başlangıç kazıması için maksimum dosya yaşı (12 saat = 43200 saniye)
STARTUP_MAX_AGE_SECONDS = 43200


def _predictions_file_is_stale() -> bool:
    """
    todays_predictions.json dosyası yoksa veya 12 saatten eskiyse True döner.
    Bu sadece startup kontrolü içindir.
    """
    if not os.path.exists(PREDICTIONS_FILE):
        return True
    age = time.time() - os.path.getmtime(PREDICTIONS_FILE)
    return age > STARTUP_MAX_AGE_SECONDS


async def _startup_scrape():
    """
    Uygulama başlarken veri yoksa veya çok eskiyse tek seferlik kazıma yapar.
    Arka planda asyncio görevi olarak çalışır; API başlangıcını bloklamaz.
    """
    from app.services.prediction_runner import PredictionRunner

    logger.info("🔄 Başlangıç: Mevcut tahmin dosyası yok veya çok eski — ilk kazıma başlatılıyor...")
    try:
        runner = PredictionRunner()
        await run_in_threadpool(runner.run_daily_predictions)
        logger.info("✅ Başlangıç kazıması tamamlandı.")
    except Exception as e:
        logger.error(f"❌ Başlangıç kazıma hatası: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── BAŞLANGIÇ ───────────────────────────────────────────────────────────
    logger.info("------------------------------------------")
    logger.info("🔥 Legends Sports MLB Predictor API Başlatılıyor...")

    # 1. Veri klasörünü hazırla
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info(f"✅ Veri klasörü hazır: {DATA_DIR}")

    # 2. Gerekirse başlangıç kazımasını arka planda başlat
    startup_task = None
    if _predictions_file_is_stale():
        startup_task = asyncio.create_task(_startup_scrape())
    else:
        logger.info("✅ Tahmin dosyası güncel, başlangıç kazıması atlandı.")

    # 3. Günlük zamanlayıcıyı başlat (00:00 & 12:00 ET)
    from app.core.scheduler import scheduled_scraping_loop
    scheduler_task = asyncio.create_task(scheduled_scraping_loop())
    logger.info("🗓️  Günlük zamanlayıcı arka planda başlatıldı (00:00 & 12:00 ET).")
    logger.info("------------------------------------------")

    yield  # ─── UYGULAMA ÇALIŞIYOR ──────────────────────────────────────────

    # ─── KAPANIŞ ─────────────────────────────────────────────────────────────
    logger.info("🛑 API Kapatılıyor...")

    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    if startup_task and not startup_task.done():
        startup_task.cancel()
        try:
            await startup_task
        except asyncio.CancelledError:
            pass

    logger.info("✅ Tüm arka plan görevleri durduruldu.")
    logger.info("------------------------------------------")
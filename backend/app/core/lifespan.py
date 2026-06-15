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
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

# Veri klasörünün yolu
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sports", "mlb", "data"))
PREDICTIONS_FILE = os.path.join(DATA_DIR, "todays_predictions.json")

TENNIS_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sports", "tennis", "data"))
TENNIS_PREDICTIONS_FILE = os.path.join(TENNIS_DATA_DIR, "today_predictions.json")

# Başlangıç kazıması için maksimum dosya yaşı (12 saat = 43200 saniye)
STARTUP_MAX_AGE_SECONDS = 43200


def _predictions_file_is_stale() -> bool:
    """
    todays_predictions.json dosyası yoksa, bugünün takvim tarihini taşımıyorsa veya 
    12 saatten eskiyse True döner (akıllı takvim günü kontrolü ile API kota koruması).
    """
    if not os.path.exists(PREDICTIONS_FILE):
        return True

    try:
        # Önbellek dosyasını oku ve bugünün takvim tarihiyle karşılaştır
        with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        file_date = data.get("date")
        et_today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

        # Eğer dosyadaki tahmin tarihi bugüne aitse, KESİNLİKLE internet kazıması yapma (Bypass)
        if file_date == et_today:
            logger.info(f"⚡ Akıllı Kota Koruması: Önbellekteki tahminler bugünün takvim gününe ({et_today}) ait. Sıfırdan kazıma bypass edildi.")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Önbellek tarihi okunamadı, standart yaş kontrole dönülüyor: {e}")

    age = time.time() - os.path.getmtime(PREDICTIONS_FILE)
    return age > STARTUP_MAX_AGE_SECONDS


async def _startup_scrape():
    """
    Uygulama başlarken veri yoksa veya çok eskiyse tek seferlik kazıma yapar.
    Arka planda asyncio görevi olarak çalışır; API başlangıcını bloklamaz.
    """
    from app.sports.mlb.runner import PredictionRunner

    logger.info("🔄 Başlangıç: Mevcut tahmin dosyası yok veya çok eski — ilk kazıma başlatılıyor...")
    try:
        runner = PredictionRunner()
        await run_in_threadpool(runner.run_daily_predictions)
        logger.info("✅ Başlangıç kazıması tamamlandı.")
    except Exception as e:
        logger.error(f"❌ Başlangıç kazıma hatası: {e}", exc_info=True)


def _tennis_predictions_file_is_stale() -> bool:
    """
    today_predictions.json dosyası yoksa, bugünün takvim tarihini taşımıyorsa veya 
    12 saatten eskiyse True döner (akıllı takvim günü kontrolü ile API kota koruması).
    """
    if not os.path.exists(TENNIS_PREDICTIONS_FILE):
        return True

    try:
        with open(TENNIS_PREDICTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        file_date = data.get("date")
        et_today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

        if file_date == et_today:
            logger.info(f"⚡ Tennis Akıllı Kota Koruması: Önbellekteki tahminler bugünün takvim gününe ({et_today}) ait. Sıfırdan kazıma bypass edildi.")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Tennis önbellek tarihi okunamadı, standart yaş kontrole dönülüyor: {e}")

    age = time.time() - os.path.getmtime(TENNIS_PREDICTIONS_FILE)
    return age > STARTUP_MAX_AGE_SECONDS


async def _tennis_startup_scrape():
    """
    Uygulama başlarken veri yoksa veya çok eskiyse tek seferlik tenis kazıması yapar.
    Arka planda asyncio görevi olarak çalışır; API başlangıcını bloklamaz.
    """
    from app.sports.tennis.pipeline_runner import TennisPipelineRunner

    logger.info("🔄 Başlangıç: Mevcut tenis tahmin dosyası yok veya çok eski — ilk tenis kazıması başlatılıyor...")
    try:
        runner = TennisPipelineRunner()
        await run_in_threadpool(runner.run_pipeline)
        logger.info("✅ Başlangıç tenis kazıması tamamlandı.")
    except Exception as e:
        logger.error(f"❌ Başlangıç tenis kazıma hatası: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── BAŞLANGIÇ ───────────────────────────────────────────────────────────
    logger.info("------------------------------------------")
    logger.info("🔥 Legends Sports MLB & Tennis Predictor API Başlatılıyor...")

    # 1. Veri klasörlerini hazırla
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TENNIS_DATA_DIR, exist_ok=True)
    logger.info(f"✅ MLB Veri klasörü hazır: {DATA_DIR}")
    logger.info(f"✅ Tenis Veri klasörü hazır: {TENNIS_DATA_DIR}")

    # 2. Gerekirse başlangıç kazımalarını arka planda başlat
    startup_task = None
    if _predictions_file_is_stale():
        startup_task = asyncio.create_task(_startup_scrape())
    else:
        logger.info("✅ MLB Tahmin dosyası güncel, başlangıç kazıması atlandı.")

    tennis_startup_task = None
    if _tennis_predictions_file_is_stale():
        tennis_startup_task = asyncio.create_task(_tennis_startup_scrape())
    else:
        logger.info("✅ Tenis tahmin dosyası güncel, başlangıç kazıması atlandı.")

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

    # Cancel MLB startup scrape
    if startup_task and not startup_task.done():
        startup_task.cancel()
        try:
            await startup_task
        except asyncio.CancelledError:
            pass

    # Cancel Tennis startup scrape
    if tennis_startup_task and not tennis_startup_task.done():
        tennis_startup_task.cancel()
        try:
            await tennis_startup_task
        except asyncio.CancelledError:
            pass

    logger.info("✅ Tüm arka plan görevleri durduruldu.")
    logger.info("------------------------------------------")
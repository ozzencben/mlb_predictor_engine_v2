"""
Legends Sports - Otomatik Zamanlayıcı (Scheduler)

Bu modül FastAPI'nin lifespan event'i içinde bir asyncio arka plan görevi
olarak başlatılır. Her gün saat 00:00 ve 12:00 ET'de otomatik olarak
tüm scraper + AI pipeline'ı çalıştırır.

Sayfa açılışları veya yenilemeleri ASLA kazıma tetiklemez.
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Eastern Time (ET) zaman dilimi
ET_ZONE = ZoneInfo("America/New_York")

# Hedef saatler: 00:00 ve 12:00 ET
SCHEDULED_HOURS_ET = {0, 12}

# Scraping tamamlandı mı? (Double-run engelleyici)
_scrape_lock = asyncio.Lock()


def _seconds_until_next_run() -> float:
    """
    Şu anki ET saatine göre bir sonraki hedef saate (00:00 veya 12:00)
    kaç saniye kaldığını hesaplar.
    """
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
    
    total_seconds = (next_run - now_et).total_seconds()
    return max(total_seconds, 1.0)


async def _run_scraping_pipeline():
    """Güvenli şekilde tam scraping + AI pipeline'ı çalıştırır."""
    from starlette.concurrency import run_in_threadpool
    from app.services.prediction_runner import PredictionRunner

    if _scrape_lock.locked():
        logger.warning("⏸️  Zamanlayıcı: Önceki kazıma henüz devam ediyor, bu tur atlanıyor.")
        return

    async with _scrape_lock:
        now_et = datetime.now(ET_ZONE)
        logger.info(f"⏰ Zamanlı Kazıma Başlıyor — ET: {now_et.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            runner = PredictionRunner()
            await run_in_threadpool(runner.run_daily_predictions)
            logger.info("✅ Zamanlı Kazıma Tamamlandı.")
        except Exception as e:
            logger.error(f"❌ Zamanlı Kazıma Hatası: {e}", exc_info=True)


async def scheduled_scraping_loop():
    """
    Ana zamanlayıcı döngüsü. FastAPI lifespan içinde çalışır.
    Her döngüde:
      1. Bir sonraki hedef saate kadar bekler.
      2. Hedef saat geldiğinde kazımayı çalıştırır.
      3. Aynı dakikada tekrar tetiklememek için 65 saniye uyur.
    """
    logger.info("🗓️  Legends Sports Zamanlayıcısı Başlatıldı (00:00 & 12:00 ET hedef).")

    while True:
        wait_seconds = _seconds_until_next_run()
        next_run_et = datetime.now(ET_ZONE)
        logger.info(
            f"⏳ Zamanlayıcı: Bir sonraki çalışmaya {wait_seconds:.0f}s kaldı "
            f"(ET şu an: {next_run_et.strftime('%H:%M:%S')})"
        )

        await asyncio.sleep(wait_seconds)

        # Asıl çalışma zamanı
        await _run_scraping_pipeline()

        # Aynı dakika içinde tekrar tetiklenmesin (60+5 saniye tampon)
        await asyncio.sleep(65)

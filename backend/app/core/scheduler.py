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

# Hedef saatler: 00:00 ve 12:00 ET (tam pipeline — MLB + Tennis + WNBA)
SCHEDULED_HOURS_ET = {0, 12}

# Tenis hafif yenileme: her 4 saatte bir (rolling 24h penceresi)
TENNIS_REFRESH_HOURS_ET = {0, 4, 8, 12, 16, 20}

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
    from app.sports.mlb.runner import PredictionRunner
    from app.sports.tennis.pipeline_runner import TennisPipelineRunner

    if _scrape_lock.locked():
        logger.warning("⏸️  Zamanlayıcı: Önceki kazıma henüz devam ediyor, bu tur atlanıyor.")
        return

    async with _scrape_lock:
        now_et = datetime.now(ET_ZONE)
        logger.info(f"⏰ Zamanlı Kazıma Başlıyor — ET: {now_et.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. MLB Pipeline
        try:
            runner = PredictionRunner()
            await run_in_threadpool(runner.run_daily_predictions)
            logger.info("✅ MLB Zamanlı Kazıma Tamamlandı.")
        except Exception as e:
            logger.error(f"❌ MLB Zamanlı Kazıma Hatası: {e}", exc_info=True)

        # 2. Tennis Pipeline
        try:
            from app.core.runtime_env import is_low_memory_host
            tennis_runner = TennisPipelineRunner()
            await run_in_threadpool(tennis_runner.run_pipeline, not is_low_memory_host())
            logger.info("✅ Tenis Zamanlı Kazıma Tamamlandı.")
        except Exception as e:
            logger.error(f"❌ Tenis Zamanlı Kazıma Hatası: {e}", exc_info=True)

        # 3. WNBA Pipeline
        try:
            from app.sports.wnba.pipeline_runner import run_pipeline as run_wnba_pipeline
            await run_in_threadpool(run_wnba_pipeline)
            logger.info("✅ WNBA Zamanlı Kazıma Tamamlandı.")
        except Exception as e:
            logger.error(f"❌ WNBA Zamanlı Kazıma Hatası: {e}", exc_info=True)


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


async def _run_tennis_refresh_pipeline():
    """Tenis rolling 24h penceresi icin hafif yenileme."""
    from starlette.concurrency import run_in_threadpool
    from app.sports.tennis.pipeline_runner import TennisPipelineRunner

    if _scrape_lock.locked():
        logger.info("⏸️  Tenis refresh: tam pipeline calisiyor, bu tur atlaniyor.")
        return

    async with _scrape_lock:
        now_et = datetime.now(ET_ZONE)
        logger.info(f"🎾 Tenis rolling-window refresh — ET: {now_et.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            runner = TennisPipelineRunner()
            await run_in_threadpool(runner.run_pipeline, False)
            logger.info("✅ Tenis rolling-window refresh tamamlandi.")
        except Exception as e:
            logger.error(f"❌ Tenis rolling-window refresh hatasi: {e}", exc_info=True)


def _seconds_until_next_tennis_refresh() -> float:
    """Bir sonraki TENNIS_REFRESH_HOURS_ET saatine kalan saniye."""
    now_et = datetime.now(ET_ZONE)
    candidates = []
    for day_offset in [0, 1]:
        base_date = now_et + timedelta(days=day_offset)
        for hour in TENNIS_REFRESH_HOURS_ET:
            candidate = base_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            candidates.append(candidate)

    future_candidates = [c for c in candidates if c > now_et]
    next_run = min(future_candidates)
    return max((next_run - now_et).total_seconds(), 1.0)


async def scheduled_tennis_refresh_loop():
    """Tenis icin 4 saatte bir hafif fixture+predict refresh."""
    logger.info("🎾 Tenis rolling-window zamanlayicisi baslatildi (her 4 saat ET).")

    while True:
        wait_seconds = _seconds_until_next_tennis_refresh()
        logger.info(
            f"⏳ Tenis refresh: sonraki calismaya {wait_seconds:.0f}s "
            f"(ET simdi: {datetime.now(ET_ZONE).strftime('%H:%M:%S')})"
        )
        await asyncio.sleep(wait_seconds)

        now_et = datetime.now(ET_ZONE)
        # Tam pipeline saatinde cift calismayi onle (0 ve 12'de full pipeline zaten tenisi calistirir)
        if now_et.hour in SCHEDULED_HOURS_ET and now_et.minute < 2:
            logger.info("⏭️  Tenis refresh atlandi — tam gunluk pipeline bu saatte calisacak.")
        else:
            await _run_tennis_refresh_pipeline()

        await asyncio.sleep(65)

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

WNBA_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sports", "wnba", "data"))
WNBA_PREDICTIONS_FILE = os.path.join(WNBA_DATA_DIR, "today_predictions.json")
WNBA_MATCHES_FILE = os.path.join(WNBA_DATA_DIR, "today_matches.json")

# Başlangıç kazıması için maksimum dosya yaşı (12 saat = 43200 saniye)
STARTUP_MAX_AGE_SECONDS = 43200


def _predictions_file_is_stale() -> bool:
    """
    todays_predictions.json dosyası yoksa, bugünün takvim tarihini taşımıyorsa veya 
    12 saatten eskiyse True döner. daily_matchups.json tarihi de kontrol edilir —
    sadece predictions tarihine güvenmek yanlış bypass'a yol açabilir.
    """
    MATCHUPS_FILE = os.path.join(DATA_DIR, "daily_matchups.json")

    if not os.path.exists(PREDICTIONS_FILE):
        return True

    et_today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")

    try:
        with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        file_date = data.get("date")
        if file_date != et_today:
            return True

        # daily_matchups.json da güncel mi?
        if os.path.exists(MATCHUPS_FILE):
            with open(MATCHUPS_FILE, "r", encoding="utf-8") as f:
                matchups = json.load(f)
            matchups_date = matchups.get("date")
            if matchups_date and matchups_date < et_today:
                logger.warning(
                    f"⚠️ MLB Matchup Staleness: daily_matchups.json tarihi={matchups_date}, "
                    f"bugün={et_today}. Pipeline yeniden başlatılıyor."
                )
                return True

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
    Rolling 24h penceresi: predictions dosyasi yoksa, fixture yoksa veya
    predictions_are_stale() True donerse yenileme gerekir.
    """
    from app.sports.tennis.services.window_utils import predictions_are_stale

    TENNIS_MATCHES_FILE = os.path.join(TENNIS_DATA_DIR, "today_matches.json")

    if not os.path.exists(TENNIS_PREDICTIONS_FILE):
        return True
    if not os.path.exists(TENNIS_MATCHES_FILE):
        return True

    try:
        with open(TENNIS_PREDICTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if predictions_are_stale(data):
            logger.info("⚠️ Tennis rolling-window tahminleri eski — yenileme gerekli.")
            return True
    except Exception as e:
        logger.warning(f"⚠️ Tennis predictions okunamadi: {e}")
        return True

    try:
        with open(TENNIS_MATCHES_FILE, "r", encoding="utf-8") as f:
            matches = json.load(f)
        if not matches:
            return True
    except Exception as e:
        logger.warning(f"⚠️ Tennis matches okunamadi: {e}")
        return True

    logger.info("⚡ Tennis rolling-window verisi guncel — baslangic kazimasi atlandi.")
    return False


async def _tennis_startup_scrape():
    """
    Uygulama başlarken veri yoksa veya çok eskiyse tek seferlik tenis kazıması yapar.
    Arka planda asyncio görevi olarak çalışır; API başlangıcını bloklamaz.
    """
    from app.sports.tennis.pipeline_runner import TennisPipelineRunner
    from app.core.runtime_env import is_low_memory_host

    logger.info("🔄 Başlangıç: Mevcut tenis tahmin dosyası yok veya çok eski — tenis yenilemesi başlatılıyor...")
    try:
        runner = TennisPipelineRunner()
        # Render 512MB: tam pipeline (Playwright x200) OOM yapar — hafif mod
        if is_low_memory_host():
            await run_in_threadpool(runner.run_pipeline, False)
        else:
            full = not os.path.exists(TENNIS_PREDICTIONS_FILE)
            await run_in_threadpool(runner.run_pipeline, full)
        logger.info("✅ Başlangıç tenis kazıması tamamlandı.")
    except Exception as e:
        logger.error(f"❌ Başlangıç tenis kazıma hatası: {e}", exc_info=True)


async def _wnba_startup_scrape():
    from app.sports.wnba.pipeline_runner import run_pipeline

    logger.info("🔄 Baslangic: WNBA tahmin dosyasi yok veya eski — pipeline baslatiliyor...")
    try:
        await run_in_threadpool(run_pipeline)
        logger.info("✅ Baslangic WNBA kazimasi tamamlandi.")
    except Exception as e:
        logger.error(f"❌ Baslangic WNBA kazima hatasi: {e}", exc_info=True)


async def _sequential_low_memory_startup():
    """Render 512MB: pipeline'ları paralel değil sırayla çalıştır (OOM önleme)."""
    import gc
    from app.core.runtime_env import is_low_memory_host

    if not is_low_memory_host():
        return

    logger.info("📉 Render düşük bellek modu: 30s bekleniyor, sonra yalnızca tenis startup...")
    await asyncio.sleep(30)

    if _tennis_predictions_file_is_stale():
        await _tennis_startup_scrape()
        gc.collect()

    logger.info("⏭️  Render: MLB/WNBA startup atlandı (bellek koruması — scheduler halleder).")


async def _delayed_scheduler_loop():
    """Render'da startup bitene kadar zamanlayıcıları geciktir."""
    from app.core.runtime_env import is_low_memory_host
    from app.core.scheduler import scheduled_scraping_loop, scheduled_tennis_refresh_loop

    if is_low_memory_host():
        logger.info("⏳ Render: zamanlayıcılar 8 dakika geciktirildi (startup bellek koruması).")
        await asyncio.sleep(480)

    await asyncio.gather(
        scheduled_scraping_loop(),
        scheduled_tennis_refresh_loop(),
    )


def _wnba_predictions_file_is_stale() -> bool:
    if not os.path.exists(WNBA_PREDICTIONS_FILE):
        return True
    if not os.path.exists(WNBA_MATCHES_FILE):
        return True

    et_today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    try:
        with open(WNBA_PREDICTIONS_FILE, "r", encoding="utf-8") as f:
            pred_date = json.load(f).get("date")
        if pred_date != et_today:
            return True
        with open(WNBA_MATCHES_FILE, "r", encoding="utf-8") as f:
            match_date = json.load(f).get("date")
        if match_date != et_today:
            return True
        logger.info(f"⚡ WNBA onbellek guncel ({et_today}). Baslangic pipeline atlandi.")
        return False
    except Exception:
        return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ─── BAŞLANGIÇ ───────────────────────────────────────────────────────────
    logger.info("------------------------------------------")
    logger.info("🔥 Legends Sports MLB, Tennis & WNBA Predictor API Baslatiliyor...")

    # 1. Veri klasörlerini hazırla
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TENNIS_DATA_DIR, exist_ok=True)
    os.makedirs(WNBA_DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(WNBA_DATA_DIR, "archive"), exist_ok=True)
    logger.info(f"✅ MLB Veri klasörü hazır: {DATA_DIR}")
    logger.info(f"✅ Tenis Veri klasörü hazır: {TENNIS_DATA_DIR}")
    logger.info(f"✅ WNBA Veri klasörü hazır: {WNBA_DATA_DIR}")

    # 2. Gerekirse başlangıç kazımalarını arka planda başlat
    from app.core.runtime_env import is_low_memory_host

    startup_task = None
    tennis_startup_task = None
    wnba_startup_task = None

    if is_low_memory_host():
        startup_task = asyncio.create_task(_sequential_low_memory_startup())
    else:
        if _predictions_file_is_stale():
            startup_task = asyncio.create_task(_startup_scrape())
        else:
            logger.info("✅ MLB Tahmin dosyası güncel, başlangıç kazıması atlandı.")

        if _tennis_predictions_file_is_stale():
            tennis_startup_task = asyncio.create_task(_tennis_startup_scrape())
        else:
            logger.info("✅ Tenis tahmin dosyası güncel, başlangıç kazıması atlandı.")

        if _wnba_predictions_file_is_stale():
            wnba_startup_task = asyncio.create_task(_wnba_startup_scrape())
        else:
            logger.info("✅ WNBA tahmin dosyasi guncel, baslangic kazimasi atlandi.")

    # 3. Günlük zamanlayıcıyı başlat (Render'da gecikmeli)
    scheduler_task = asyncio.create_task(_delayed_scheduler_loop())
    if is_low_memory_host():
        logger.info("🗓️  Zamanlayıcılar gecikmeli başlatılacak (Render bellek koruması).")
    else:
        logger.info("🗓️  Günlük zamanlayıcı arka planda başlatıldı (00:00 & 12:00 ET).")
        logger.info("🎾 Tenis rolling-window zamanlayıcı başlatıldı (her 4 saat ET).")
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

    if wnba_startup_task and not wnba_startup_task.done():
        wnba_startup_task.cancel()
        try:
            await wnba_startup_task
        except asyncio.CancelledError:
            pass

    logger.info("✅ Tüm arka plan görevleri durduruldu.")
    logger.info("------------------------------------------")
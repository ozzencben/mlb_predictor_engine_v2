"""
Legends Sports — Günlük Pipeline Çalıştırıcı
=============================================
Bu script FastAPI'den bağımsız olarak MLB ve Tennis pipeline'larını çalıştırır.
Windows Task Scheduler veya manuel olarak tetiklenebilir.

Çalışma Zamanları (ET):  00:00  ve  12:00
Türkiye Karşılığı (UTC+3): 07:00 ve 19:00

Kullanım:
  cd backend
  uv run python run_daily_pipelines.py
  uv run python run_daily_pipelines.py --mlb-only
  uv run python run_daily_pipelines.py --tennis-only
"""

import sys
import os
import logging
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Encoding fix for Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Proje kök dizinini path'e ekle
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# Log dosyası kurulumu
LOG_DIR = ROOT_DIR / "app" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "pipeline_scheduler.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pipeline_runner")


def run_mlb_pipeline() -> bool:
    logger.info("=" * 60)
    logger.info("MLB Pipeline baslatiliyor...")
    logger.info("=" * 60)
    try:
        from app.sports.mlb.runner import PredictionRunner
        runner = PredictionRunner()
        runner.run_daily_predictions()
        logger.info("MLB Pipeline basariyla tamamlandi.")
        return True
    except Exception as e:
        logger.error(f"MLB Pipeline HATASI: {e}", exc_info=True)
        return False


def run_tennis_pipeline() -> bool:
    logger.info("=" * 60)
    logger.info("Tennis Pipeline baslatiliyor...")
    logger.info("=" * 60)
    try:
        from app.sports.tennis.pipeline_runner import TennisPipelineRunner
        runner = TennisPipelineRunner()
        runner.run_pipeline()
        logger.info("Tennis Pipeline basariyla tamamlandi.")
        return True
    except Exception as e:
        logger.error(f"Tennis Pipeline HATASI: {e}", exc_info=True)
        return False


def run_wnba_pipeline() -> bool:
    logger.info("=" * 60)
    logger.info("WNBA Pipeline baslatiliyor...")
    logger.info("=" * 60)
    try:
        from app.sports.wnba.pipeline_runner import run_pipeline
        run_pipeline()
        logger.info("WNBA Pipeline basariyla tamamlandi.")
        return True
    except Exception as e:
        logger.error(f"WNBA Pipeline HATASI: {e}", exc_info=True)
        return False


def main():
    parser = argparse.ArgumentParser(description="Legends Sports Gunluk Pipeline")
    parser.add_argument("--mlb-only", action="store_true", help="Sadece MLB pipeline'i calistir")
    parser.add_argument("--tennis-only", action="store_true", help="Sadece Tennis pipeline'i calistir")
    parser.add_argument("--wnba-only", action="store_true", help="Sadece WNBA pipeline'i calistir")
    args = parser.parse_args()

    et_now = datetime.now(ZoneInfo("America/New_York"))
    logger.info(f"Pipeline baslatildi — ET: {et_now.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    if not args.tennis_only and not args.wnba_only:
        results["mlb"] = run_mlb_pipeline()

    if not args.mlb_only and not args.wnba_only:
        results["tennis"] = run_tennis_pipeline()

    if not args.mlb_only and not args.tennis_only:
        results["wnba"] = run_wnba_pipeline()

    logger.info("=" * 60)
    for sport, success in results.items():
        status = "BASARILI" if success else "BASARISIZ"
        logger.info(f"  {sport.upper()}: {status}")
    logger.info("Tum pipeline'lar tamamlandi.")
    logger.info("=" * 60)

    # Herhangi bir pipeline basarisiz olduysa exit code 1
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()

import asyncio
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from starlette.concurrency import run_in_threadpool

wnba_router = APIRouter(prefix="/wnba", tags=["WNBA"])

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sports", "wnba", "data"))
PREDICTIONS_FILE = os.path.join(DATA_DIR, "today_predictions.json")
RESULTS_FILE = os.path.join(DATA_DIR, "today_accuracy_results.json")
MATCHES_FILE = os.path.join(DATA_DIR, "today_matches.json")
INJURIES_FILE = os.path.join(DATA_DIR, "today_injuries.json")
ELO_FILE = os.path.join(DATA_DIR, "processed", "team_elo_history.json")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")

_update_lock = asyncio.Lock()


def _get_file_modified_time(filepath: str) -> str:
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    return "Bulunamadi"


def _today_et() -> str:
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")


def _resolve_dated_file(base_today: str, archive_prefix: str, date: str | None) -> tuple[str, bool]:
    today_str = _today_et()
    if not date or date == today_str:
        return base_today, date is None or date == today_str
    return os.path.join(ARCHIVE_DIR, f"{archive_prefix}_{date}.json"), False


@wnba_router.get("/health")
async def get_health():
    from app.sports.wnba.services.beta_ops import BETA_VERSION, load_model_meta

    return {
        "status": "ok",
        "sport": "wnba",
        "beta": True,
        "beta_version": BETA_VERSION,
        "predictions_ready": os.path.exists(PREDICTIONS_FILE),
        "model_meta": load_model_meta(),
    }


@wnba_router.get("/predictions")
async def get_predictions(date: str | None = None):
    """Bugunun veya arsivdeki belirli bir tarihin WNBA tahminlerini dondurur."""
    today_str = _today_et()
    target_file, is_today = _resolve_dated_file(PREDICTIONS_FILE, "predictions", date)

    if not os.path.exists(target_file):
        if is_today:
            raise HTTPException(status_code=503, detail="Tahmin verisi henuz hazir degil.")
        raise HTTPException(
            status_code=404,
            detail=f"Belirtilen tarih ({date or today_str}) icin WNBA tahmin verisi bulunamadi.",
        )

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "status": "success",
            "cached": True,
            "last_updated": _get_file_modified_time(target_file),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tahmin dosyasi okunurken hata: {e}") from e


@wnba_router.get("/results")
async def get_results(date: str | None = None):
    """Gunluk model dogruluk sonuclarini dondurur."""
    today_str = _today_et()
    target_file, is_today = _resolve_dated_file(RESULTS_FILE, "results", date)

    if not os.path.exists(target_file):
        if is_today:
            return {
                "status": "success",
                "last_updated": None,
                "data": {
                    "date": today_str,
                    "active_results": [],
                    "low_confidence_results": [],
                    "alt_league_results": [],
                    "active_statistics": {"total_predicted": 0, "correct_predictions": 0, "accuracy_percentage": 0},
                },
            }
        raise HTTPException(
            status_code=404,
            detail=f"Belirtilen tarih ({date or today_str}) icin dogruluk sonucu bulunamadi.",
        )

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "status": "success",
            "last_updated": _get_file_modified_time(target_file),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sonuc dosyasi okunurken hata: {e}") from e


@wnba_router.get("/schedule")
async def get_schedule():
    """Bugunun WNBA fiksturunu dondurur."""
    if not os.path.exists(MATCHES_FILE):
        raise HTTPException(status_code=503, detail="Fikstur verisi henuz hazir degil.")

    with open(MATCHES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "status": "success",
        "last_updated": _get_file_modified_time(MATCHES_FILE),
        "data": data,
    }


@wnba_router.get("/standings")
async def get_standings():
    """ELO bazli takim siralamasi."""
    if not os.path.exists(ELO_FILE):
        raise HTTPException(status_code=503, detail="ELO verisi henuz hazir degil.")

    with open(ELO_FILE, "r", encoding="utf-8") as f:
        elo_data = json.load(f)

    team_names: dict[str, str] = {}
    teams_file = os.path.join(DATA_DIR, "teams.json")
    if os.path.exists(teams_file):
        with open(teams_file, "r", encoding="utf-8") as f:
            for team in json.load(f).get("teams", []):
                team_names[str(team["id"])] = team.get("abbreviation") or team.get("display_name")

    from app.sports.wnba.services.config import CORE_TEAM_IDS, HISTORICAL_TEAM_NAMES
    for tid, abbr in CORE_TEAM_IDS.items():
        team_names.setdefault(tid, abbr)
    for tid, name in HISTORICAL_TEAM_NAMES.items():
        team_names.setdefault(tid, name)

    current = elo_data.get("current") or {}
    standings = [
        {
            "team_id": tid,
            "team_abbr": team_names.get(tid, tid),
            "elo": round(float(rating), 1),
        }
        for tid, rating in current.items()
    ]
    standings.sort(key=lambda x: -x["elo"])

    return {
        "status": "success",
        "last_updated": _get_file_modified_time(ELO_FILE),
        "total_teams": len(standings),
        "standings": standings,
    }


@wnba_router.get("/injuries")
async def get_injuries():
    """ESPN injury feed ozeti."""
    if not os.path.exists(INJURIES_FILE):
        raise HTTPException(status_code=404, detail="Injury verisi bulunamadi.")

    with open(INJURIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "status": "success",
        "last_updated": _get_file_modified_time(INJURIES_FILE),
        "data": data,
    }


@wnba_router.get("/system-status")
async def get_system_status():
    from app.sports.wnba.services.beta_ops import BETA_VERSION, load_model_meta

    return {
        "status": "success",
        "beta_version": BETA_VERSION,
        "is_updating_now": _update_lock.locked(),
        "model_meta": load_model_meta(),
        "last_updates": {
            "predictions": _get_file_modified_time(PREDICTIONS_FILE),
            "matches": _get_file_modified_time(MATCHES_FILE),
            "injuries": _get_file_modified_time(INJURIES_FILE),
            "accuracy_results": _get_file_modified_time(RESULTS_FILE),
            "elo": _get_file_modified_time(ELO_FILE),
        },
    }


async def _run_wnba_refresh():
    try:
        from app.sports.wnba.pipeline_runner import run_pipeline
        await run_in_threadpool(run_pipeline)
    except Exception as e:
        print(f"WNBA refresh hatasi: {e}")
    finally:
        _update_lock.release()


@wnba_router.post("/refresh-data")
async def refresh_data(
    background_tasks: BackgroundTasks,
    x_cron_secret: str | None = Header(default=None),
):
    """Manuel WNBA pipeline tetikleyicisi."""
    cron_key = os.getenv("CRON_SECRET_KEY")
    if cron_key:
        if not x_cron_secret or x_cron_secret != cron_key:
            raise HTTPException(status_code=401, detail="Yetkisiz istek: gecersiz cron anahtari.")

    if _update_lock.locked():
        raise HTTPException(status_code=429, detail="WNBA pipeline zaten calisiyor.")

    await _update_lock.acquire()
    background_tasks.add_task(_run_wnba_refresh)
    return {
        "status": "success",
        "message": "WNBA pipeline arka planda baslatildi.",
    }

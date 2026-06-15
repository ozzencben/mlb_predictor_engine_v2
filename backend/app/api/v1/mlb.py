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
import httpx

from app.core.config import settings
from app.sports.mlb.runner import PredictionRunner, calculate_consensus_edges

mlb_router = APIRouter()

# Global Yollar
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sports", "mlb", "data"))
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


async def get_historical_predictions(date_str: str):
    now_et = datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    is_future = date_str > today_str

    # 1. Önbelleği kontrol et
    cached_file = os.path.join(DATA_DIR, f"predictions_{date_str}.json")
    if os.path.exists(cached_file):
        with open(cached_file, "r", encoding="utf-8") as f:
            return json.load(f)
            
    # 2. StatsAPI'den maç fikstürünü çek
    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=probablePitcher,decisions"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(schedule_url, timeout=10)
            r.raise_for_status()
            sched_data = r.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"MLB API schedule fetch failed: {str(e)}")
            
    # 3. Takım eşleme sözlüğünü yükle
    mapping_file = os.path.join(DATA_DIR, 'team_mappings.json')
    mlb_to_tr_map = {}
    if os.path.exists(mapping_file):
        with open(mapping_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
            mlb_to_tr_map = mappings.get("mlb_to_tr", {})

    # 4. İstatistik DB'lerini yükle
    team_db = {}
    team_db_file = os.path.join(DATA_DIR, "live_stats.json")
    if os.path.exists(team_db_file):
        with open(team_db_file, "r", encoding="utf-8") as f:
            team_db = json.load(f)

    pitcher_db = {}
    pitcher_db_file = os.path.join(DATA_DIR, "pitcher_stats.json")
    if os.path.exists(pitcher_db_file):
        with open(pitcher_db_file, "r", encoding="utf-8") as f:
            pitcher_db = json.load(f)

    ballpark_db = {}
    ballpark_db_file = os.path.join(DATA_DIR, "ballpark_stats.json")
    if os.path.exists(ballpark_db_file):
        with open(ballpark_db_file, "r", encoding="utf-8") as f:
            ballpark_db = json.load(f)

    trends_db = {}
    trends_db_file = os.path.join(DATA_DIR, "nrfi_trends.json")
    if os.path.exists(trends_db_file):
        with open(trends_db_file, "r", encoding="utf-8") as f:
            trends_db = json.load(f)
            
    # Lig durumlarını/kayıtlarını (standings) çek
    standings = {}
    standings_url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(standings_url, timeout=10)
            if r.status_code == 200:
                standings_data = r.json()
                for record in standings_data.get('records', []):
                    for team in record.get('teamRecords', []):
                        team_id = team['team']['id']
                        wins = team.get('wins', 0)
                        losses = team.get('losses', 0)
                        home_rec, away_rec, l10_rec = "0-0", "0-0", "0-0"
                        for split in team.get('records', {}).get('splitRecords', []):
                            rec_str = f"{split.get('wins', 0)}-{split.get('losses', 0)}"
                            if split['type'] == 'home': home_rec = rec_str
                            elif split['type'] == 'away': away_rec = rec_str
                            elif split['type'] == 'lastTen': l10_rec = rec_str
                        standings[team_id] = {
                            "record": f"{wins}-{losses}",
                            "home_record": home_rec,
                            "away_record": away_rec,
                            "l10": l10_rec
                        }
        except Exception:
            pass

    # Motoru başlat
    from app.sports.mlb.services.mlb_unified_engine import MLBUnifiedEngine, GameInputData
    from app.sports.mlb.models.schemas import NRFITrendSchema
    engine = MLBUnifiedEngine(team_db=team_db, pitcher_db=pitcher_db, ballpark_db=ballpark_db)

    predictions = []
    dates_list = sched_data.get('dates', [])
    if not dates_list:
        return {"date": date_str, "total_games": 0, "predictions": []}
        
    games = dates_list[0].get('games', [])
    
    async with httpx.AsyncClient() as client:
        for game in games:
            if game['status']['statusCode'] not in ['P', 'S', 'I', 'F', 'O', 'PW', 'W', 'D', 'DH', 'DR', 'A']:
                continue
                
            away_node = game['teams']['away']
            home_node = game['teams']['home']
            
            away_team_full = away_node['team']['name']
            home_team_full = home_node['team']['name']
            
            away_team = mlb_to_tr_map.get(away_team_full, away_team_full)
            home_team = mlb_to_tr_map.get(home_team_full, home_team_full)
            
            away_pitcher = away_node.get('probablePitcher', {}).get('fullName', 'TBD')
            home_pitcher = home_node.get('probablePitcher', {}).get('fullName', 'TBD')
            
            raw_date = game.get('gameDate')
            game_time = "TBD"
            if raw_date:
                try:
                    utc_dt = datetime.strptime(raw_date, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=ZoneInfo("UTC"))
                    et_dt = utc_dt.astimezone(ZoneInfo("America/New_York"))
                    game_time = et_dt.strftime('%I:%M %p ET').lstrip('0')
                except Exception:
                    game_time = raw_date
            
            away_stats = standings.get(away_node['team']['id'], {"record": "0-0", "home_record": "0-0", "away_record": "0-0", "l10": "0-0"})
            home_stats = standings.get(home_node['team']['id'], {"record": "0-0", "home_record": "0-0", "away_record": "0-0", "l10": "0-0"})
            
            game_dict = {
                "away_team": away_team,
                "home_team": home_team,
                "away_pitcher": away_pitcher,
                "home_pitcher": home_pitcher,
                "game_time": game_time,
                "away_stats": away_stats,
                "home_stats": home_stats,
                "status": game['status']['detailedState']
            }
            
            # Trend verisini bul (fuzzy matching)
            trend_data = None
            for key_str, val in trends_db.items():
                if away_team.lower() in key_str.lower() or home_team.lower() in key_str.lower():
                    trend_data = val
                    break
            
            if trend_data:
                trends_schema = NRFITrendSchema(**trend_data)
            else:
                trends_schema = NRFITrendSchema(is_scraper_fallback=True)
                
            # Varsayılan hava durumu
            weather_info = {
                "temp": 72,
                "humidity": 50,
                "wind_speed": 0,
                "wind_bearing": 0,
                "wind_direction": "calm",
                "condition": "Dome / Standard"
            }
            if is_future:
                weather_info["forecast_pending"] = True
            
            try:
                game_input = GameInputData(**game_dict)
                prediction = engine.predict_matchup(game_input, trends=trends_schema, weather=weather_info)
            except Exception as e:
                print(f"Prediction engine failed for historical matchup {away_team} vs {home_team}: {e}")
                continue
                
            prediction["Odds"] = {
                "best_away_odds": 1.91,
                "best_home_odds": 1.91,
                "over_under": 8.5,
                "away_edge_pct": 0,
                "home_edge_pct": 0,
                "away_book": "Bovada",
                "home_book": "Bovada",
                "f5_away_odds": 1.91,
                "f5_home_odds": 1.91,
                "f5_away_edge_pct": 0,
                "f5_home_edge_pct": 0,
                "nrfi_odds": 1.85,
                "yrfi_odds": 1.95,
                "nrfi_edge_pct": 0,
                "yrfi_edge_pct": 0,
                "bookmakers": []
            }
            
            prediction["History"] = {"away_l10": [], "home_l10": [], "h2h": []}
            prediction["Weather"] = weather_info
            
            if is_future:
                prediction["Details"] = {"ai_insight": "AI Insight is pending for upcoming games."}
            else:
                prediction["Details"] = {"ai_insight": "AI Analysis is closed for completed matches."}
            
            status_lower = game['status']['detailedState'].lower()
            is_completed = "final" in status_lower or "completed" in status_lower or "game over" in status_lower
            
            if is_completed and away_node.get('score') is not None and home_node.get('score') is not None:
                away_score = away_node['score']
                home_score = home_node['score']
                total_runs = away_score + home_score
                actual_winner = "away" if away_score > home_score else "home"
                
                is_nrfi_successful = True
                try:
                    linescore_url = f"https://statsapi.mlb.com/api/v1/game/{game['gamePk']}/linescore"
                    linescore_r = await client.get(linescore_url, timeout=5)
                    if linescore_r.status_code == 200:
                        ls_data = linescore_r.json()
                        innings = ls_data.get('innings', [])
                        if innings:
                            first_inning = innings[0]
                            away_first_runs = first_inning.get('away', {}).get('runs', 0)
                            home_first_runs = first_inning.get('home', {}).get('runs', 0)
                            if away_first_runs > 0 or home_first_runs > 0:
                                is_nrfi_successful = False
                except Exception as ex:
                    print(f"Error fetching linescore for game {game['gamePk']}: {ex}")
                    
                # Kazanan tahmini
                predicted_winner = "away" if prediction["Full_Game"]["full_away_win_prob"] > 0.50 else "home"
                ml_correct = predicted_winner == actual_winner
                
                # Toplam sayı tahmini
                predicted_total = prediction["Full_Game"]["full_total"]
                is_predicted_over = predicted_total > 8.5
                is_actual_over = total_runs > 8.5
                total_correct = is_predicted_over == is_actual_over
                
                # Spread
                mu = prediction["Full_Game"]["full_home_score"] - prediction["Full_Game"]["full_away_score"]
                import math
                def standard_normal_cdf(x: float) -> float:
                    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
                
                home_minus_prob = 1.0 - standard_normal_cdf((1.5 - mu) / 4.0)
                away_plus_prob = standard_normal_cdf((1.5 - mu) / 4.0)
                
                run_diff = home_score - away_score
                if home_minus_prob > away_plus_prob:
                    spread_correct = run_diff >= 2
                else:
                    spread_correct = run_diff <= 1
                    
                # NRFI tahmini
                predicted_nrfi = "NRFI" if prediction["NRFI"]["nrfi_score"] > prediction["NRFI"]["yrfi_score"] else "YRFI"
                actual_nrfi = "NRFI" if is_nrfi_successful else "YRFI"
                nrfi_correct = predicted_nrfi == actual_nrfi
                
                prediction["result"] = {
                    "status": game['status']['detailedState'],
                    "away_actual_score": away_score,
                    "home_actual_score": home_score,
                    "total_actual_runs": total_runs,
                    "winner_actual": actual_winner,
                    "is_nrfi_successful": is_nrfi_successful,
                    "ml_correct": ml_correct,
                    "total_correct": total_correct,
                    "spread_correct": spread_correct,
                    "nrfi_correct": nrfi_correct
                }
                
            predictions.append(prediction)
            
    consensus_edges = calculate_consensus_edges(predictions)

    payload = {
        "date": date_str,
        "total_games": len(predictions),
        "consensus_edges": consensus_edges,
        "predictions": predictions
    }
    
    try:
        # Atomic write
        dir_name = os.path.dirname(cached_file)
        import tempfile
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.json')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)
        os.replace(temp_path, cached_file)
    except Exception as ex:
        print(f"Error saving historical prediction cache for {date_str}: {ex}")
        
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# GET /predictions
# ─────────────────────────────────────────────────────────────────────────────
@mlb_router.get("/predictions")
async def get_predictions(date: str | None = None):
    """
    Ana Dashboard Verisi.

    Davranış:
    - Parametre yoksa veya bugünün tarihi ise → todays_predictions.json dosyasını döndürür.
    - Parametre verilirse ve geçmiş/gelecek tarih ise → get_historical_predictions çalıştırır.
    """
    now_et = datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    
    if not date or date == today_str:
        if not os.path.exists(PREDICTIONS_FILE):
            raise HTTPException(
                status_code=503,
                detail="Tahmin verisi henüz hazır değil.",
            )

        with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        # consensus_edges'i her zaman mevcut predictions'dan dinamik hesapla.
        # Dosyadaki consensus_edges eski oyun eşleşmelerini içerebileceğinden
        # (örn. oyun iptali/erteleme sonrası), bunu yeniden üretmek gerekiyor.
        predictions_list = data.get("predictions", [])
        data["consensus_edges"] = calculate_consensus_edges(predictions_list)

        last_modified = _get_file_modified_time(PREDICTIONS_FILE)
        return {
            "status": "success",
            "cached": True,
            "last_updated": last_modified,
            "data": data,
        }
    else:
        # Tarih formatı doğrulaması (YYYY-MM-DD)
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Geçersiz tarih formatı. YYYY-MM-DD olmalı.")
            
        data = await get_historical_predictions(date)
        return {
            "status": "success",
            "cached": True,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "data": data,
        }


# ─────────────────────────────────────────────────────────────────────────────
# GET /system-status
# ─────────────────────────────────────────────────────────────────────────────
@mlb_router.get("/system-status")
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
@mlb_router.post("/refresh-data")
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
@mlb_router.get("/scheduler-status")
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

import asyncio
import json
import os
import tempfile
import traceback
import math
from datetime import datetime, timedelta

import httpx
from pydantic import ValidationError

from app.models.schemas import NRFITrendSchema
from app.services.data_collector import DataCollector
from app.services.matchup_scraper import MatchupScraper
from app.services.mlb_unified_engine import GameInputData, MLBUnifiedEngine
from app.services.oddlyspecific_scraper import OddlySpecificScraper
from app.services.odds_provider import OddsProvider
from app.services.pitcher_scraper import PitcherScraper
from app.services.weather_scraper import WeatherScraper
from app.services.ai.factory import get_ai_predictor


class SeededRNG:
    def __init__(self, seed_str: str):
        hash_val = 0
        for char in seed_str:
            hash_val = (hash_val << 5) - hash_val + ord(char)
            hash_val = self._to_int32(hash_val)
        self.hash_val = hash_val

    def _to_int32(self, val):
        return (val & 0xFFFFFFFF) - 0x100000000 if val & 0x80000000 else val & 0xFFFFFFFF

    def next(self) -> float:
        x = math.sin(self.hash_val) * 10000
        self.hash_val = self._to_int32(self.hash_val + 1)
        return x - math.floor(x)


def get_team_abbr(team_name: str) -> str:
    if not team_name:
        return ""
    name = team_name.lower()
    if 'yankee' in name: return 'NYY'
    if 'mets' in name or 'met' in name or 'n.y. mets' in name: return 'NYM'
    if 'red sox' in name or 'boston' in name: return 'BOS'
    if 'blue jays' in name or 'toronto' in name: return 'TOR'
    if 'orioles' in name or 'baltimore' in name: return 'BAL'
    if 'tampa' in name or 'rays' in name: return 'TB'
    if 'twins' in name or 'minnesota' in name: return 'MIN'
    if 'guardians' in name or 'cleveland' in name: return 'CLE'
    if 'tigers' in name or 'detroit' in name: return 'DET'
    if 'white sox' in name or 'chicago s' in name or 'cws' in name or 'chi white sox' in name or 'chi. white sox' in name or 'chi. s' in name or 'chi s' in name or 'sox' in name: return 'CWS'
    if 'cubs' in name or 'chicago c' in name or 'chc' in name or 'chi cubs' in name or 'chi. cubs' in name or 'chi. c' in name or 'chi c' in name: return 'CHC'
    if 'royals' in name or 'kansas' in name: return 'KC'
    if 'astros' in name or 'houston' in name: return 'HOU'
    if 'mariners' in name or 'seattle' in name: return 'SEA'
    if 'rangers' in name or 'texas' in name: return 'TEX'
    if 'angels' in name or 'laa' in name: return 'LAA'
    if 'athletics' in name or 'oakland' in name or "a's" in name: return 'OAK'
    if 'braves' in name or 'atlanta' in name: return 'ATL'
    if 'phillies' in name or 'philadelphia' in name: return 'PHI'
    if 'marlins' in name or 'miami' in name: return 'MIA'
    if 'nationals' in name or 'washington' in name or 'wsh' in name or 'was' in name: return 'WSH'
    if 'brewers' in name or 'milwaukee' in name: return 'MIL'
    if 'cardinals' in name or 'st. l' in name or 'st l' in name or 'louis' in name: return 'STL'
    if 'pirates' in name or 'pittsburgh' in name: return 'PIT'
    if 'reds' in name or 'cincinnati' in name: return 'CIN'
    if 'dodgers' in name or 'los a' in name: return 'LAD'
    if 'giants' in name or 'san f' in name: return 'SF'
    if 'padres' in name or 'san d' in name: return 'SD'
    if 'diamondbacks' in name or 'arizona' in name: return 'ARI'
    if 'rockies' in name or 'colorado' in name: return 'COL'
    return team_name[:3].upper()


def resolve_team_id(team_name: str) -> int | None:
    if not team_name:
        return None
    name = team_name.lower()
    if "yankee" in name: return 147
    if "red sox" in name or "boston" in name: return 111
    if "blue jays" in name or "toronto" in name: return 141
    if "orioles" in name or "baltimore" in name: return 110
    if "tampa" in name or "rays" in name: return 139
    if "twins" in name or "minnesota" in name: return 142
    if "guardians" in name or "cleveland" in name: return 114
    if "tigers" in name or "detroit" in name: return 116
    if "white sox" in name or "chicago s" in name: return 145
    if "cubs" in name or "chicago c" in name: return 112
    if "royals" in name or "kansas" in name: return 118
    if "astros" in name or "houston" in name: return 117
    if "mariners" in name or "seattle" in name: return 136
    if "rangers" in name or "texas" in name: return 140
    if "angels" in name or "laa" in name: return 108
    if "athletics" in name or "oakland" in name or "a's" in name: return 133
    if "braves" in name or "atlanta" in name: return 144
    if "mets" in name or "met" in name: return 121
    if "phillies" in name or "philadelphia" in name: return 143
    if "marlins" in name or "miami" in name: return 146
    if "nationals" in name or "washington" in name: return 120
    if "brewers" in name or "milwaukee" in name: return 158
    if "cardinals" in name or "st. l" in name or "st l" in name or "louis" in name: return 138
    if "pirates" in name or "pittsburgh" in name: return 134
    if "reds" in name or "cincinnati" in name: return 113
    if "dodgers" in name or "los a" in name: return 119
    if "giants" in name or "san f" in name: return 137
    if "padres" in name or "san d" in name: return 135
    if "diamondbacks" in name or "arizona" in name: return 109
    if "rockies" in name or "colorado" in name: return 115
    return None


async def fetch_team_history_async(client: httpx.AsyncClient, team_id: int, opponent_id: int = None) -> list:
    current_year = datetime.now().year
    url = "https://statsapi.mlb.com/api/v1/schedule"
    
    # 1. Fetch current year schedule
    params = {
        "sportId": 1,
        "season": current_year,
        "teamId": team_id,
    }
    if opponent_id:
        params["opponentId"] = opponent_id
        
    try:
        games = []
        response = await client.get(url, params=params, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            for date_node in data.get("dates", []):
                for g in date_node.get("games", []):
                    if g.get('status', {}).get('statusCode') == 'F' and g.get('gameType') == 'R':
                        games.append(g)
                        
            # Sort by date descending
            games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
        else:
            print(f"⚠️ [statsapi] Error fetching current history for team {team_id} (status: {response.status_code})")
            
        # 2. If we have less than 10 games, fetch previous years' schedule as fallback
        # If opponent_id is provided (H2H), go back up to 10 years until we have 10 games
        max_years_to_check = 10 if opponent_id else 1
        year_offset = 1
        
        while len(games) < 10 and year_offset <= max_years_to_check:
            prev_year = current_year - year_offset
            prev_params = {
                "sportId": 1,
                "season": prev_year,
                "teamId": team_id,
            }
            if opponent_id:
                prev_params["opponentId"] = opponent_id
                
            response_prev = await client.get(url, params=prev_params, timeout=10.0)
            if response_prev.status_code == 200:
                data_prev = response_prev.json()
                prev_games = []
                for date_node in data_prev.get("dates", []):
                    for g in date_node.get("games", []):
                        if g.get('status', {}).get('statusCode') == 'F' and g.get('gameType') == 'R':
                            prev_games.append(g)
                            
                if prev_games:
                    # Sort previous games descending and extend
                    prev_games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
                    games.extend(prev_games)
                    
                    # Re-sort combined list descending
                    games.sort(key=lambda x: x.get('gameDate', ''), reverse=True)
            else:
                print(f"⚠️ [statsapi] Error fetching fallback history for team {team_id} for season {prev_year} (status: {response_prev.status_code})")
                break
                
            year_offset += 1
            
        return games
    except Exception as e:
        print(f"⚠️ [statsapi] Exception fetching history for team {team_id}: {e}")
        return []


def parse_history_game(g: dict, target_team_name: str, mlb_to_tr: dict) -> dict:
    game_id = g.get('gamePk', 0)
    game_date_raw = g.get('gameDate', '')
    date_str = ""
    if game_date_raw:
        try:
            dt = datetime.strptime(game_date_raw, "%Y-%m-%dT%H:%M:%SZ")
            date_str = f"{dt.month}/{dt.day}/{str(dt.year)[-2:]}"
        except Exception:
            date_str = game_date_raw
            
    away_team_full = g['teams']['away']['team']['name']
    home_team_full = g['teams']['home']['team']['name']
    away_score = g['teams']['away'].get('score', 0)
    home_score = g['teams']['home'].get('score', 0)
    
    away_team = mlb_to_tr.get(away_team_full, away_team_full)
    home_team = mlb_to_tr.get(home_team_full, home_team_full)
    
    is_away = (away_team == target_team_name)
    opponent = home_team if is_away else away_team
    
    winner = away_team if away_score > home_score else home_team
    outcome = 'W' if winner == target_team_name else 'L'
    
    run_winner = max(away_score, home_score)
    run_loser = min(away_score, home_score)
    
    score_text = f"{get_team_abbr(winner)} {run_winner}-{run_loser}"
    
    # Deterministic calculation using game_id as seed
    rng = SeededRNG(f"{game_id}-l10")
    
    # Spread Play Calculation
    home_team_name = opponent if is_away else target_team_name
    is_fav = rng.next() > 0.5
    spread_sign = '-1.5' if is_fav else '+1.5'
    spread_play = f"{get_team_abbr(home_team_name)} {spread_sign}"
    
    spread_covered = False
    if spread_sign == '-1.5':
        spread_covered = (winner == home_team_name) and (run_winner - run_loser >= 2)
    else:
        spread_covered = (winner == home_team_name) or (winner != home_team_name and (run_winner - run_loser == 1))
        
    # Total Calculation
    ou_lines = [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
    ou_line = ou_lines[int(rng.next() * len(ou_lines))]
    run_total = run_winner + run_loser
    is_over = run_total > ou_line
    is_push = run_total == ou_line
    
    return {
        "date": date_str,
        "opponent": opponent,
        "isAway": is_away,
        "outcome": outcome,
        "winner": winner,
        "runWinner": run_winner,
        "runLoser": run_loser,
        "score": score_text,
        "spreadPlay": spread_play,
        "spreadCovered": spread_covered,
        "ouLine": ou_line,
        "isOver": is_over,
        "isPush": is_push
    }


def parse_h2h_game(g: dict, away_team_name: str, home_team_name: str, mlb_to_tr: dict) -> dict:
    game_id = g.get('gamePk', 0)
    game_date_raw = g.get('gameDate', '')
    date_str = ""
    if game_date_raw:
        try:
            dt = datetime.strptime(game_date_raw, "%Y-%m-%dT%H:%M:%SZ")
            date_str = f"{dt.month}/{dt.day}/{str(dt.year)[-2:]}"
        except Exception:
            date_str = game_date_raw
            
    away_team_full = g['teams']['away']['team']['name']
    home_team_full = g['teams']['home']['team']['name']
    away_score = g['teams']['away'].get('score', 0)
    home_score = g['teams']['home'].get('score', 0)
    
    away_team = mlb_to_tr.get(away_team_full, away_team_full)
    home_team = mlb_to_tr.get(home_team_full, home_team_full)
    
    is_home = (home_team == home_team_name)
    
    winner = away_team if away_score > home_score else home_team
    run_winner = max(away_score, home_score)
    run_loser = min(away_score, home_score)
    
    score_text = f"{get_team_abbr(winner)} {run_winner}-{run_loser}"
    
    rng = SeededRNG(f"{game_id}-h2h")
    
    host_team = home_team_name if is_home else away_team_name
    guest_team = away_team_name if is_home else home_team_name
    
    # Spread sign calculation
    spread_sign = '-1.5' if get_team_abbr(host_team) == 'NYM' else ('-1.5' if rng.next() > 0.5 else '+1.5')
    spread_play = f"{get_team_abbr(host_team)} {spread_sign}"
    
    spread_covered = False
    if spread_sign == '-1.5':
        spread_covered = (winner == host_team) and (run_winner - run_loser >= 2)
    else:
        spread_covered = (winner == host_team) or (winner == guest_team and (run_winner - run_loser == 1))
        
    ou_lines = [6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0]
    ou_line = ou_lines[int(rng.next() * len(ou_lines))]
    run_total = run_winner + run_loser
    is_over = run_total > ou_line
    is_push = run_total == ou_line
    
    return {
        "date": date_str,
        "isHome": is_home,
        "winner": winner,
        "runWinner": run_winner,
        "runLoser": run_loser,
        "score": score_text,
        "spreadPlay": spread_play,
        "spreadCovered": spread_covered,
        "ouLine": ou_line,
        "isOver": is_over,
        "isPush": is_push
    }


class PredictionRunner:
    """
    Sistemin ana şalteri.
    Tüm scraper'ları sırayla çalıştırır, ardından MLBUnifiedEngine ile tahminleri üretir.
    """


    def __init__(self):
        self.data_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data")
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.odds_provider = OddsProvider()
        
        mapping_file = os.path.join(self.data_dir, "team_mappings.json")
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
                self.tr_to_mlb_map = {v: k for k, v in self.mlb_to_tr_map.items()}
        except FileNotFoundError:
            self.mlb_to_tr_map = {}
            self.tr_to_mlb_map = {}

    def _atomic_save(self, filepath: str, data: dict):
        """Nihai çıktının bozulmasını önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def _load_json(self, filename: str):
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Uyarı: {filename} bulunamadı!")
            return [] if filename == "live_odds.json" else {}

    def _find_trend_data(self, away_team: str, home_team: str, trends_db: dict) -> dict:
        """
        ESPN (Örn: 'Cleveland') ile OddlySpecificStats (Örn: 'Cleveland Guardians') 
        takım isimleri arasındaki uyumsuzluğu çözen akıllı eşleştirici.
        """
        a_team = away_team.lower()
        h_team = home_team.lower()
        full_away = self.tr_to_mlb_map.get(away_team, away_team).lower()
        full_home = self.tr_to_mlb_map.get(home_team, home_team).lower()
        
        # Tam eşleşme kontrolü
        direct_key = f"{full_away}-{full_home}"
        if direct_key in trends_db:
            return trends_db[direct_key]
            
        # Parçalı (Fuzzy) eşleşme kontrolü
        def is_match(short_name, full_name, db_side):
            if short_name in db_side or full_name in db_side:
                return True
            # Oakland -> "athletics" vs "oakland athletics"
            last_word = full_name.split()[-1]
            if last_word in db_side:
                return True
            return False

        for db_key, data in trends_db.items():
            parts = db_key.split('-')
            if len(parts) == 2:
                db_a, db_h = parts
                if is_match(a_team, full_away, db_a) and is_match(h_team, full_home, db_h):
                    return data
                
        return None

    async def _run_scrapers_async(self, client: httpx.AsyncClient) -> bool:
        """
        Tüm veri toplama adımlarını asenkron pipeline içinde çalıştırır.
        Kritik bir adımda hata olursa False döner ve süreci iptal eder.
        """
        loop = asyncio.get_running_loop()

        print("📡 [1/5] Takım istatistikleri çekiliyor (TeamRankings)...")
        try:
            await loop.run_in_executor(None, DataCollector().collect_all_stats)
        except Exception as e:
            print(f"❌ Kritik Hata: DataCollector başarısız oldu. ({e})")
            return False

        print("⚾ [2/5] Günün maçları ve form durumları çekiliyor (MLB API)...")
        try:
            matchups = await loop.run_in_executor(
                None, MatchupScraper().fetch_todays_matchups
            )
            if not matchups:
                print("ℹ️ Çekilecek maç bulunamadı veya API hatası. İşlem durduruluyor.")
                return False
        except Exception as e:
            print(f"❌ Kritik Hata: MatchupScraper başarısız oldu. ({e})")
            return False

        print("🎯 [3/5] Gelişmiş Atıcı istatistikleri çekiliyor (MLB API - Statcast)...")
        pitcher_task = asyncio.create_task(
            PitcherScraper().build_pitcher_library_async(client)
        )

        print("💰 [4/5] Canlı bahis oranları çekiliyor (The Odds API)...")
        odds_task = asyncio.create_task(
            self.odds_provider.fetch_live_odds_async(client)
        )

        print("☁️ [5/5] Stadyum Hava Durumları çekiliyor (Open-Meteo)...")
        weather_task = asyncio.create_task(
            WeatherScraper().fetch_todays_weather_async(client, matchups)
        )

        print("📈 [6/6] NRFI Trendleri çekiliyor (OddlySpecificStats)...")
        trends_task = asyncio.create_task(
            OddlySpecificScraper().fetch_all_trends_async(client)
        )

        results = await asyncio.gather(
            pitcher_task, odds_task, weather_task, trends_task, return_exceptions=True
        )

        if isinstance(results[0], Exception):
            print(f"⚠️ Uyarı: PitcherScraper hatası. Lig ortalamaları kullanılacak. ({results[0]})")
            
        if isinstance(results[1], Exception):
            print(f"⚠️ Uyarı: OddsProvider hatası. Oran karşılaştırması atlanacak. ({results[1]})")
            
        if isinstance(results[2], Exception):
            print(f"⚠️ Uyarı: WeatherScraper hatası. Standart hava atandı. ({results[2]})")
            
        if not isinstance(results[3], Exception):
            self._atomic_save(os.path.join(self.data_dir, "nrfi_trends.json"), results[3])
        else:
            print(f"⚠️ Uyarı: OddlySpecificScraper hatası. ({results[3]})")
            self._atomic_save(os.path.join(self.data_dir, "nrfi_trends.json"), {})

        return True

    async def run_daily_predictions_async(self):
        print("\n🚀 V8 Tahmin Motoru Başlatılıyor...")
        
        # 1. AI Servisini başlat
        ai_service = get_ai_predictor()

        async with httpx.AsyncClient() as client:
            if not await self._run_scrapers_async(client):
                print("🛑 Zincirleme hata tespit edildi. Tahmin motoru durduruldu.")
                return []

            # Perform parallel history fetching
            print("📡 MLB API'den takımların geçmiş performansları çekiliyor (Parallel History)...")
            matchups_data = self.data_dir
            matchups_data = self._load_json("daily_matchups.json")
            games = matchups_data.get("games", [])
            
            history_tasks = []
            history_keys = []
            for game_dict in games:
                away_name = game_dict.get("away_team")
                home_name = game_dict.get("home_team")
                away_id = game_dict.get("away_team_id") or resolve_team_id(away_name)
                home_id = game_dict.get("home_team_id") or resolve_team_id(home_name)
                
                if away_id and home_id:
                    history_tasks.append(fetch_team_history_async(client, away_id))
                    history_tasks.append(fetch_team_history_async(client, home_id))
                    history_tasks.append(fetch_team_history_async(client, away_id, home_id))
                    history_keys.append((away_name, home_name, away_id, home_id))
                else:
                    history_keys.append((away_name, home_name, None, None))
            
            history_results = await asyncio.gather(*history_tasks, return_exceptions=True)
            
            history_lookup = {}
            res_idx = 0
            for key in history_keys:
                away_name, home_name, away_id, home_id = key
                if away_id and home_id:
                    away_sched = history_results[res_idx]
                    home_sched = history_results[res_idx + 1]
                    h2h_sched = history_results[res_idx + 2]
                    res_idx += 3
                    
                    if isinstance(away_sched, Exception): away_sched = []
                    if isinstance(home_sched, Exception): home_sched = []
                    if isinstance(h2h_sched, Exception): h2h_sched = []
                    
                    away_l10 = []
                    for g in away_sched:
                        try:
                            parsed = parse_history_game(g, away_name, self.mlb_to_tr_map)
                            away_l10.append(parsed)
                            if len(away_l10) >= 10:
                                break
                        except Exception as ex:
                            print(f"Error parsing history game for {away_name}: {ex}")
                            
                    home_l10 = []
                    for g in home_sched:
                        try:
                            parsed = parse_history_game(g, home_name, self.mlb_to_tr_map)
                            home_l10.append(parsed)
                            if len(home_l10) >= 10:
                                break
                        except Exception as ex:
                            print(f"Error parsing history game for {home_name}: {ex}")
                            
                    h2h = []
                    for g in h2h_sched:
                        try:
                            parsed = parse_h2h_game(g, away_name, home_name, self.mlb_to_tr_map)
                            h2h.append(parsed)
                            if len(h2h) >= 10:
                                break
                        except Exception as ex:
                            print(f"Error parsing H2H game for {away_name} vs {home_name}: {ex}")
                            
                    history_lookup[(away_name, home_name)] = {
                        "away_l10": away_l10,
                        "home_l10": home_l10,
                        "h2h": h2h
                    }
                else:
                    history_lookup[(away_name, home_name)] = {
                        "away_l10": [],
                        "home_l10": [],
                        "h2h": []
                    }

        team_db = self._load_json("live_stats.json")
        pitcher_db = self._load_json("pitcher_stats.json")
        matchups_data = self._load_json("daily_matchups.json")
        ballpark_db = self._load_json("ballpark_stats.json")
        live_odds_data = self._load_json("live_odds.json")
        weather_db = self._load_json("live_weather.json")
        trends_db = self._load_json("nrfi_trends.json")

        if not team_db or not matchups_data:
            print("❌ Kritik veri dosyaları okunamadı.")
            return []

        engine = MLBUnifiedEngine(
            team_db=team_db, pitcher_db=pitcher_db, ballpark_db=ballpark_db
        )

        all_predictions = []
        games = matchups_data.get("games", [])

        print(f"\n⚾ Bugünün {len(games)} maçı için EDGE (Avantaj) analizleri yapılıyor...\n")
        print("=" * 75)

        for game_dict in games:
            try:
                try:
                    game_input = GameInputData(**game_dict)
                except ValidationError as ve:
                    print(f"❌ Veri Formatı Hatası ({game_dict.get('away_team')} vs {game_dict.get('home_team')}): {ve}")
                    continue

                # TAKIM İSMİ UYUMSUZLUĞU (FUZZY MATCH) ÇÖZÜMÜ
                trend_data = self._find_trend_data(game_input.away_team, game_input.home_team, trends_db)
                
                if trend_data:
                    trends_schema = NRFITrendSchema(**trend_data)
                else:
                    trends_schema = NRFITrendSchema(is_scraper_fallback=True)

                prediction = engine.predict_matchup(game_input, trends=trends_schema)

                away_team = game_input.away_team
                home_team = game_input.home_team

                best_odds = self.odds_provider.get_best_odds_for_game(
                    away_team, home_team, live_odds_data
                )

                away_prob = prediction["Full_Game"]["full_away_win_prob"]
                home_prob = prediction["Full_Game"]["full_home_win_prob"]

                f5_away_prob = prediction["F5"]["f5_away_win_prob"]
                f5_home_prob = prediction["F5"]["f5_home_win_prob"]

                nrfi_prob = prediction["NRFI"]["nrfi_score"]
                yrfi_prob = prediction["NRFI"]["yrfi_score"]

                away_edge = self.odds_provider.calculate_edge(away_prob, best_odds["away_odds"])
                home_edge = self.odds_provider.calculate_edge(home_prob, best_odds["home_odds"])

                f5_away_edge = self.odds_provider.calculate_edge(f5_away_prob, best_odds["f5_away_odds"])
                f5_home_edge = self.odds_provider.calculate_edge(f5_home_prob, best_odds["f5_home_odds"])

                nrfi_edge = self.odds_provider.calculate_edge(nrfi_prob, best_odds["nrfi_odds"])
                yrfi_edge = self.odds_provider.calculate_edge(yrfi_prob, best_odds["yrfi_odds"])

                prediction["Odds"] = {
                    "best_away_odds": best_odds["away_odds"],
                    "best_home_odds": best_odds["home_odds"],
                    "over_under": best_odds["over_under"],
                    "away_edge_pct": round(away_edge * 100, 1),
                    "home_edge_pct": round(home_edge * 100, 1),
                    "away_book": best_odds.get("away_book", ""),
                    "home_book": best_odds.get("home_book", ""),
                    
                    "f5_away_odds": best_odds["f5_away_odds"],
                    "f5_home_odds": best_odds["f5_home_odds"],
                    "f5_away_edge_pct": round(f5_away_edge * 100, 1),
                    "f5_home_edge_pct": round(f5_home_edge * 100, 1),
                    "f5_away_book": best_odds.get("f5_away_book", ""),
                    "f5_home_book": best_odds.get("f5_home_book", ""),
                    
                    "nrfi_odds": best_odds["nrfi_odds"],
                    "yrfi_odds": best_odds["yrfi_odds"],
                    "nrfi_edge_pct": round(nrfi_edge * 100, 1),
                    "yrfi_edge_pct": round(yrfi_edge * 100, 1),
                    "nrfi_book": best_odds.get("nrfi_book", ""),
                    "yrfi_book": best_odds.get("yrfi_book", ""),
                    "bookmakers": best_odds.get("bookmakers", []),
                }

                # Attach History
                history_data = history_lookup.get((away_team, home_team), {
                    "away_l10": [],
                    "home_l10": [],
                    "h2h": []
                })
                prediction["History"] = history_data

                weather_info = weather_db.get(home_team, {})
                prediction["Weather"] = weather_info
                
                # 2. AI asenkron döngüsünden önce None ataması yap
                if "Details" not in prediction:
                    prediction["Details"] = {}
                prediction["Details"]["ai_insight"] = None

                all_predictions.append(prediction)

            except Exception as e:
                print(f"❌ Hesaplama Hatası: {e}")
                traceback.print_exc()

        # 3 & 4. AI verilerini SIRALI (Sequential) çekme - Free Tier Koruması
        print("\n🤖 Maçlar için AI analizleri üretiliyor (Rate Limit Korumalı)...")
        
        skipped_count = 0
        for pred in all_predictions:
            away = pred['matchup']['away_team']
            home = pred['matchup']['home_team']

            # --- CIRCUIT BREAKER: Günlük veya kalıcı kota dolduysa kalan maçları direkt atla ---
            if getattr(ai_service, 'quota_exhausted', False):
                skipped_count += 1
                pred["Details"]["ai_insight"] = "AI analysis skipped: Daily token quota exhausted or rate limit tripped."
                continue

            print(f"   ➤ Processing AI for: {away} vs {home}")
            try:
                insight = await ai_service.generate_insight_async(pred)
                pred["Details"]["ai_insight"] = insight
            except Exception as e:
                print(f"❌ AI Insight Hatası ({away} @ {home}): {e}")
                pred["Details"]["ai_insight"] = "AI analysis is temporarily unavailable."
            finally:
                # Kota dolmadıysa istekler arası bekleme uygula
                # Circuit açıksa bekleme gereksiz — zaten atlanıyor
                if not getattr(ai_service, 'quota_exhausted', False):
                    # Gemini Free Tier (15 RPM) limiti için her maç arası kesin olarak 4.5 saniye bekle
                    # Bu sayede 1 dakika içinde atılan istek sayısı 13-14 civarında kalır, 429 yemez.
                    await asyncio.sleep(4.5)

        if skipped_count > 0:
            print(f"⚡ {skipped_count} maç için AI analizi atlandı (kota/sınır aşımı).")
        print("✅ Tüm AI analizleri tamamlandı.")

        output_path = os.path.join(self.data_dir, "todays_predictions.json")
        payload = {
            "date": matchups_data.get("date"),
            "total_games": len(all_predictions),
            "predictions": all_predictions,
        }

        self._atomic_save(output_path, payload)

        print(f"\n✅ EDGE Analizleri tamamlandı! {len(all_predictions)} maç verisi kaydedildi.")
        return all_predictions

    def run_daily_predictions(self):
        """Senkron tetikleyiciler için asenkron metodun sarmalayıcısı."""
        return asyncio.run(self.run_daily_predictions_async())
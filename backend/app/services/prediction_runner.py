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
from app.services.pitcher_props_engine import PitcherPropsEngine


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


def calculate_consensus_edges(predictions: list) -> dict:
    if not predictions:
        return {}

    # 1. Moneyline Edge
    top_ml_game = None
    top_ml_edge_val = -999.0
    top_ml_choice = ""
    top_ml_prob = 0.0

    # 2. Spread Edge (Probability)
    top_spread_game = None
    top_spread_prob_val = 0.0
    top_spread_choice = ""

    # 3. Total Edge
    top_total_game = None
    top_total_gap_val = -1.0
    top_total_choice = ""
    top_total_model_val = 0.0

    # 4. (Görev 10) - Most Confident ML Plays
    ml_plays = []

    # 5. (Görev 10) - Team Totals to Target
    team_totals = []

    for game in predictions:
        matchup = game.get("matchup")
        full_game = game.get("Full_Game")
        odds = game.get("Odds")
        if not matchup or not full_game or not odds:
            continue

        away_team = matchup.get("away_team")
        home_team = matchup.get("home_team")

        # --- 1. Moneyline Edge ---
        away_prob = float(full_game.get("full_away_win_prob", 0))
        home_prob = float(full_game.get("full_home_win_prob", 0))
        away_edge = float(odds.get("away_edge_pct", 0))
        home_edge = float(odds.get("home_edge_pct", 0))

        is_away_ml_better = away_edge >= home_edge
        max_ml_edge = away_edge if is_away_ml_better else home_edge
        ml_choice = f"{get_team_abbr(away_team)} ML" if is_away_ml_better else f"{get_team_abbr(home_team)} ML"
        ml_prob = away_prob if is_away_ml_better else home_prob

        if max_ml_edge > top_ml_edge_val:
            top_ml_edge_val = max_ml_edge
            top_ml_game = game
            top_ml_choice = ml_choice
            top_ml_prob = ml_prob

        # --- ML Plays List (for Most Confident ML) ---
        ml_plays.append({
            "away_team": away_team,
            "home_team": home_team,
            "team": away_team if away_prob >= home_prob else home_team,
            "choice": f"{get_team_abbr(away_team)} ML" if away_prob >= home_prob else f"{get_team_abbr(home_team)} ML",
            "prob": max(away_prob, home_prob),
            "edge": away_edge if away_prob >= home_prob else home_edge
        })

        # --- Team Totals to Target List ---
        away_projected = float(full_game.get("full_away_score", 0))
        home_projected = float(full_game.get("full_home_score", 0))
        
        if away_projected > 4.5:
            team_totals.append({
                "away_team": away_team,
                "home_team": home_team,
                "team": away_team,
                "projected_runs": away_projected,
                "confidence": away_prob
            })
        if home_projected > 4.5:
            team_totals.append({
                "away_team": away_team,
                "home_team": home_team,
                "team": home_team,
                "projected_runs": home_projected,
                "confidence": home_prob
            })

        # --- 2. Spread Edge ---
        away_score = float(full_game.get("full_away_score", 0))
        home_score = float(full_game.get("full_home_score", 0))
        mu = home_score - away_score
        sigma = 4.0

        def standard_normal_cdf(x: float) -> float:
            return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

        def away_cover_prob(S: float) -> float:
            return standard_normal_cdf((S - mu) / sigma)

        def home_cover_prob(S: float) -> float:
            return 1.0 - standard_normal_cdf((-S - mu) / sigma)

        model_winner = away_team if away_score > home_score else home_team
        book_away_spread = odds.get("away_spread") if odds.get("away_spread") is not None else (-1.5 if away_score > home_score else 1.5)

        if model_winner == away_team:
            spread_val = book_away_spread
            spread_choice = f"{get_team_abbr(away_team)} {spread_val:+.1f}"
            spread_prob = away_cover_prob(spread_val)
        else:
            spread_val = -book_away_spread
            spread_choice = f"{get_team_abbr(home_team)} {spread_val:+.1f}"
            spread_prob = home_cover_prob(spread_val)

        if spread_prob > top_spread_prob_val:
            top_spread_prob_val = spread_prob
            top_spread_game = game
            top_spread_choice = spread_choice

        # --- 3. Total Edge ---
        book_total = odds.get("over_under") if odds.get("over_under") is not None and odds.get("over_under") > 0 else 8.5
        model_total = float(full_game.get("full_total", 0))
        total_gap = abs(model_total - book_total)
        total_choice = f"OVER {book_total}" if model_total >= book_total else f"UNDER {book_total}"

        if total_gap > top_total_gap_val:
            top_total_gap_val = total_gap
            top_total_game = game
            top_total_choice = total_choice
            top_total_model_val = model_total

    # Sort & Filter
    ml_plays.sort(key=lambda x: x["prob"], reverse=True)
    top_2_ml = ml_plays[:2] if len(ml_plays) >= 2 else ml_plays

    team_totals.sort(key=lambda x: x["projected_runs"], reverse=True)
    top_2_totals = team_totals[:2] if len(team_totals) >= 2 else team_totals

    return {
        "ml": {
            "away_team": top_ml_game["matchup"]["away_team"],
            "home_team": top_ml_game["matchup"]["home_team"],
            "choice": top_ml_choice,
            "edge": top_ml_edge_val,
            "prob": top_ml_prob
        } if top_ml_game else None,
        "spread": {
            "away_team": top_spread_game["matchup"]["away_team"],
            "home_team": top_spread_game["matchup"]["home_team"],
            "choice": top_spread_choice,
            "prob": top_spread_prob_val
        } if top_spread_game else None,
        "total": {
            "away_team": top_total_game["matchup"]["away_team"],
            "home_team": top_total_game["matchup"]["home_team"],
            "choice": top_total_choice,
            "gap": top_total_gap_val,
            "modelTotal": top_total_model_val
        } if top_total_game else None,
        "most_confident_ml": [
            {
                "away_team": play["away_team"],
                "home_team": play["home_team"],
                "team": play["team"],
                "choice": play["choice"],
                "prob": play["prob"],
                "edge": play["edge"]
            } for play in top_2_ml
        ],
        "team_totals": [
            {
                "away_team": total["away_team"],
                "home_team": total["home_team"],
                "team": total["team"],
                "projected_runs": total["projected_runs"],
                "confidence": total["confidence"]
            } for total in top_2_totals
        ]
    }


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

        # Load lineups and player stats cache
        self.lineups_cache_path = os.path.join(self.data_dir, "lineups_cache.json")
        self.player_stats_cache_path = os.path.join(self.data_dir, "player_stats_cache.json")
        
        try:
            with open(self.lineups_cache_path, "r", encoding="utf-8") as f:
                self.lineups_cache = json.load(f)
        except Exception:
            self.lineups_cache = {}
            
        try:
            with open(self.player_stats_cache_path, "r", encoding="utf-8") as f:
                self.player_stats_cache = json.load(f)
        except Exception:
            self.player_stats_cache = {}

    def _save_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving {path}: {e}")

    async def fetch_last_completed_game_pk(self, client: httpx.AsyncClient, team_id: int) -> int | None:
        current_year = datetime.now().year
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={current_year}&teamId={team_id}"
        try:
            r = await client.get(url, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                dates = data.get("dates", [])
                for date_node in reversed(dates):
                    for g in reversed(date_node.get("games", [])):
                        if g["status"]["statusCode"] in ["F", "O"]:
                            return g["gamePk"]
        except Exception as e:
            print(f"Error fetching last completed game for team {team_id}: {e}")
        return None

    async def get_lineup_for_game(self, client: httpx.AsyncClient, game_pk: int, away_id: int, home_id: int) -> tuple[list, list]:
        today_str = datetime.now().strftime('%Y-%m-%d')
        cache_key = str(game_pk)
        
        if cache_key in self.lineups_cache:
            cached = self.lineups_cache[cache_key]
            if cached.get("date") == today_str and cached.get("is_official", False):
                return cached["away_lineup"], cached["home_lineup"]
                
        url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
        away_lineup = []
        home_lineup = []
        is_official = False
        
        try:
            r = await client.get(url, timeout=10.0)
            if r.status_code == 200:
                data = r.json()
                temp_away = []
                temp_home = []
                for side, lineup in [("away", temp_away), ("home", temp_home)]:
                    team_data = data.get("teams", {}).get(side, {})
                    batting_order = team_data.get("battingOrder", [])
                    players = team_data.get("players", {})
                    
                    for pid in batting_order[:9]:
                        p_info = players.get(f"ID{pid}", {})
                        p_name = p_info.get("person", {}).get("fullName", "Unknown")
                        p_pos = p_info.get("position", {}).get("abbreviation", "N/A")
                        lineup.append({"id": pid, "name": p_name, "position": p_pos})
                
                if len(temp_away) >= 9 and len(temp_home) >= 9:
                    away_lineup = temp_away
                    home_lineup = temp_home
                    is_official = True
                    print(f"[Official Lineups Found] {game_pk} icin resmi kadrolar StatsAPI'den cekildi.")
        except Exception as e:
            print(f"Error fetching boxscore for game {game_pk}: {e}")
            
        if not is_official:
            # 2. Resmi kadro yoksa ve önbellekte bugünün fallback verisi varsa doğrudan onu kullan
            if cache_key in self.lineups_cache:
                cached = self.lineups_cache[cache_key]
                if cached.get("date") == today_str:
                    print(f"[Cached Fallback Lineups Used] {game_pk} icin resmi kadro henuz aciklanmamis. Onbellekteki yedek kadrolar kullaniliyor.")
                    return cached["away_lineup"], cached["home_lineup"]
            
            # 3. Önbellekte bugüne ait veri yoksa ilk kez fallback oluştur
            print(f"[Generating Fallback Lineups] {game_pk} icin resmi kadrolar aciklanmamis, StatsAPI uzerinden fallback kadrolari olusturuluyor...")
            if away_id:
                last_pk = await self.fetch_last_completed_game_pk(client, away_id)
                if last_pk:
                    fallback_url = f"https://statsapi.mlb.com/api/v1/game/{last_pk}/boxscore"
                    try:
                        fb_r = await client.get(fallback_url, timeout=10.0)
                        if fb_r.status_code == 200:
                            fb_data = fb_r.json()
                            team_data = fb_data.get("teams", {}).get("away", {})
                            batting_order = team_data.get("battingOrder", [])
                            players = team_data.get("players", {})
                            for pid in batting_order[:9]:
                                p_info = players.get(f"ID{pid}", {})
                                p_name = p_info.get("person", {}).get("fullName", "Unknown")
                                p_pos = p_info.get("position", {}).get("abbreviation", "N/A")
                                away_lineup.append({"id": pid, "name": p_name, "position": p_pos})
                    except Exception as e:
                        print(f"Error fetching fallback away lineup: {e}")
                        
            if home_id:
                last_pk = await self.fetch_last_completed_game_pk(client, home_id)
                if last_pk:
                    fallback_url = f"https://statsapi.mlb.com/api/v1/game/{last_pk}/boxscore"
                    try:
                        fb_r = await client.get(fallback_url, timeout=10.0)
                        if fb_r.status_code == 200:
                            fb_data = fb_r.json()
                            team_data = fb_data.get("teams", {}).get("home", {})
                            batting_order = team_data.get("battingOrder", [])
                            players = team_data.get("players", {})
                            for pid in batting_order[:9]:
                                p_info = players.get(f"ID{pid}", {})
                                p_name = p_info.get("person", {}).get("fullName", "Unknown")
                                p_pos = p_info.get("position", {}).get("abbreviation", "N/A")
                                home_lineup.append({"id": pid, "name": p_name, "position": p_pos})
                    except Exception as e:
                        print(f"Error fetching fallback home lineup: {e}")
                        
        self.lineups_cache[cache_key] = {
            "date": today_str,
            "away_lineup": away_lineup,
            "home_lineup": home_lineup,
            "is_official": is_official
        }
        self._save_json(self.lineups_cache_path, self.lineups_cache)
        return away_lineup, home_lineup

    async def fetch_team_splits_async(self, client: httpx.AsyncClient) -> dict:
        splits_file = os.path.join(self.data_dir, "team_splits.json")
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        if os.path.exists(splits_file):
            try:
                with open(splits_file, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached.get("date") == today_str:
                        return cached.get("splits")
            except Exception:
                pass
                
        print("📡 Fetching team splits vs LHP/RHP in parallel...")
        url_teams = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
        try:
            res = await client.get(url_teams)
            teams = res.json().get("teams", [])
            
            tasks = []
            team_info = []
            for t in teams:
                team_id = t["id"]
                team_name = t["name"]
                url_splits = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=statSplits&group=hitting&sitCodes=vl,vr&season={datetime.now().year}"
                tasks.append(client.get(url_splits, timeout=15.0))
                team_info.append((team_id, team_name))
                
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            splits_db = {}
            for (team_id, team_name), resp in zip(team_info, responses):
                if isinstance(resp, Exception) or resp.status_code != 200:
                    continue
                    
                data = resp.json()
                splits = data.get("stats", [{}])[0].get("splits", [])
                
                vs_LHP = {"avg": 0.250, "obp": 0.320, "slg": 0.400, "ops": 0.720, "k_pct": 22.0}
                vs_RHP = {"avg": 0.250, "obp": 0.320, "slg": 0.400, "ops": 0.720, "k_pct": 22.0}
                
                for s in splits:
                    code = s.get("split", {}).get("code")
                    stat = s.get("stat", {})
                    
                    def safe_float(k, default):
                        v = stat.get(k)
                        if v is None: return default
                        try: return float(str(v).replace("%", ""))
                        except ValueError: return default
                            
                    pa = safe_float("plateAppearances", 1.0)
                    so = safe_float("strikeOuts", 0.0)
                    k_pct = round((so / pa) * 100.0, 1) if pa > 0 else 22.0
                    
                    parsed_split = {
                        "avg": safe_float("avg", 0.250),
                        "obp": safe_float("obp", 0.320),
                        "slg": safe_float("slg", 0.400),
                        "ops": safe_float("ops", 0.720),
                        "k_pct": k_pct
                    }
                    
                    if code == "vl":
                        vs_LHP = parsed_split
                    elif code == "vr":
                        vs_RHP = parsed_split
                        
                tr_name = self.mlb_to_tr_map.get(team_name, team_name)
                splits_db[tr_name] = {
                    "vs_LHP": vs_LHP,
                    "vs_RHP": vs_RHP
                }
                
            payload = {"date": today_str, "splits": splits_db}
            self._save_json(splits_file, payload)
            return splits_db
        except Exception as e:
            print(f"⚠️ Failed to fetch team splits: {e}")
            return {}

    async def get_pitcher_last_5_k_async(self, client: httpx.AsyncClient, pitcher_id: int) -> list:
        if not pitcher_id:
            return []
            
        today_str = datetime.now().strftime('%Y-%m-%d')
        cache_file = os.path.join(self.data_dir, "pitcher_logs_cache.json")
        cache_data = {}
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            except Exception:
                pass
                
        if cache_data.get("date") == today_str:
            cached_logs = cache_data.get("logs", {}).get(str(pitcher_id))
            if cached_logs is not None:
                return cached_logs
                
        current_year = datetime.now().year
        url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats?stats=gameLog&group=pitching&season={current_year}"
        
        local_client = client
        created_client = False
        if client is None or client.is_closed:
            local_client = httpx.AsyncClient()
            created_client = True
            
        try:
            res = await local_client.get(url, timeout=10.0)
            k_counts = []
            if res.status_code == 200:
                data = res.json()
                splits = data.get("stats", [{}])[0].get("splits", [])
                recent_games = splits[-5:]
                k_counts = [int(g.get("stat", {}).get("strikeOuts", 0)) for g in recent_games]
                
            if len(k_counts) < 3:
                prev_url = f"https://statsapi.mlb.com/api/v1/people/{pitcher_id}/stats?stats=gameLog&group=pitching&season={current_year - 1}"
                prev_res = await local_client.get(prev_url, timeout=10.0)
                if prev_res.status_code == 200:
                    prev_data = prev_res.json()
                    prev_splits = prev_data.get("stats", [{}])[0].get("splits", [])
                    prev_recent = prev_splits[-5:]
                    prev_k_counts = [int(g.get("stat", {}).get("strikeOuts", 0)) for g in prev_recent]
                    k_counts = (prev_k_counts + k_counts)[-5:]
                    
            if "logs" not in cache_data or cache_data.get("date") != today_str:
                cache_data = {"date": today_str, "logs": {}}
            cache_data["logs"][str(pitcher_id)] = k_counts
            self._save_json(cache_file, cache_data)
            return k_counts
        except Exception as e:
            print(f"⚠️ Failed to fetch game logs for pitcher {pitcher_id}: {e}")
        finally:
            if created_client:
                await local_client.aclose()
            
        return []

    async def get_player_stats_async(self, client: httpx.AsyncClient, player_id: int, group: str) -> dict:
        today_str = datetime.now().strftime('%Y-%m-%d')
        cache_key = f"{player_id}_{group}"
        
        if cache_key in self.player_stats_cache:
            cached = self.player_stats_cache[cache_key]
            if cached.get("date") == today_str:
                return cached.get("stats")
                
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group={group}&season={datetime.now().year}"
        stats_data = {}
        try:
            resp = await client.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                splits = data.get("stats", [{}])[0].get("splits", [])
                if splits:
                    stats_data = splits[0].get("stat", {})
        except Exception as e:
            print(f"Error fetching player stats for {player_id}: {e}")
            
        self.player_stats_cache[cache_key] = {
            "date": today_str,
            "stats": stats_data
        }
        self._save_json(self.player_stats_cache_path, self.player_stats_cache)
        return stats_data

    def calculate_hitter_metrics(self, stat: dict) -> dict:
        avg = float(stat.get("avg", 0.250))
        obp = float(stat.get("obp", 0.320))
        slg = float(stat.get("slg", 0.400))
        ops = float(stat.get("ops", 0.720))
        
        bb = int(stat.get("baseOnBalls", 0))
        ibb = int(stat.get("intentionalWalks", 0))
        hbp = int(stat.get("hitByPitch", 0))
        h = int(stat.get("hits", 0))
        hr = int(stat.get("homeRuns", 0))
        double = int(stat.get("doubles", 0))
        triple = int(stat.get("triples", 0))
        ab = int(stat.get("atBats", 0))
        sf = int(stat.get("sacFlies", 0))
        pa = int(stat.get("plateAppearances", 0))
        so = int(stat.get("strikeOuts", 0))
        
        single = h - double - triple - hr
        denom = (ab + bb - ibb + sf + hbp)
        
        if denom > 0:
            woba = (0.69 * (bb - ibb) + 0.72 * hbp + 0.89 * single + 1.27 * double + 1.62 * triple + 2.10 * hr) / denom
        else:
            woba = obp
            
        wrc_plus = (woba / 0.315) * 100.0
        
        k_pct = (so / pa * 100.0) if pa > 0 else 22.0
        bb_pct = (bb / pa * 100.0) if pa > 0 else 8.0
        pitches_per_pa = float(stat.get("numberOfPitches", 0)) / pa if pa > 0 else 3.8
        
        swstr_pct = 0.45 * k_pct + 2.0
        csw_pct = 0.55 * k_pct + 15.0
        whiff_pct = 0.9 * k_pct + 5.0
        oswing_pct = k_pct * 0.8 + 12.0
        in_zone_contact_pct = 95.0 - (swstr_pct * 1.5)
        swing_pct = 47.0
        
        return {
            "avg": round(avg, 3),
            "obp": round(obp, 3),
            "slg": round(slg, 3),
            "ops": round(ops, 3),
            "woba": round(woba, 3),
            "wrc_plus": round(wrc_plus, 1),
            "k_pct": round(k_pct, 1),
            "bb_pct": round(bb_pct, 1),
            "pitches_per_pa": round(pitches_per_pa, 2),
            "swstr_pct": round(swstr_pct, 1),
            "csw_pct": round(csw_pct, 1),
            "whiff_pct": round(whiff_pct, 1),
            "oswing_pct": round(oswing_pct, 1),
            "in_zone_contact_pct": round(in_zone_contact_pct, 1),
            "swing_pct": swing_pct
        }

    def calculate_pitcher_metrics(self, stat: dict) -> dict:
        era = float(stat.get("era", 4.20))
        fip = float(stat.get("fip", 4.20))
        xera = float(stat.get("xera", 4.20))
        xfip = float(stat.get("xfip", 4.20))

        bf = int(stat.get("battersFaced", 1)) or 1
        ip = float(stat.get("inningsPitched", stat.get("innings_pitched", 1.0)))
        bb = int(stat.get("baseOnBalls", 0))
        k = int(stat.get("strikeOuts", 0))
        games = int(stat.get("gamesPitched", 1)) or 1
        pitches = int(stat.get("numberOfPitches", 0))

        # Prefer pre-computed values from pitcher_stats.json (set by PitcherScraper).
        # Fall back to formula-derived values only when absent or zero.
        stored_k_pct = stat.get("k_pct")
        if stored_k_pct is not None and float(stored_k_pct) > 0:
            k_pct = float(stored_k_pct)
        else:
            k_pct = (k / bf * 100.0) if bf > 1 else 20.0

        stored_bb_pct = stat.get("bb_pct")
        bb_pct = float(stored_bb_pct) if stored_bb_pct is not None else (bb / bf * 100.0 if bf > 1 else 8.0)

        k_bb_pct = k_pct - bb_pct
        pitches_per_pa = pitches / bf if bf > 1 else 3.8

        stored_avg_bf = stat.get("avg_bf")
        avg_bf = float(stored_avg_bf) if stored_avg_bf is not None else (bf / games if games > 0 else 22.5)

        stored_avg_ip = stat.get("avg_ip")
        avg_ip = float(stored_avg_ip) if stored_avg_ip is not None else (ip / games if games > 0 else 5.2)

        stored_swstr = stat.get("swstr_pct")
        swstr_pct = float(stored_swstr) if stored_swstr is not None else (0.45 * k_pct + 2.0)

        stored_csw = stat.get("csw_pct")
        csw_pct = float(stored_csw) if stored_csw is not None else (0.55 * k_pct + 15.0)

        whiff_pct = 0.9 * k_pct + 5.0
        putaway_pct = 1.2 * k_pct
        throws = stat.get("throws", "R")

        return {
            "era": era,
            "fip": fip,
            "xera": xera,
            "xfip": xfip,
            "k_pct": round(k_pct, 1),
            "bb_pct": round(bb_pct, 1),
            "k_bb_pct": round(k_bb_pct, 1),
            "pitches_per_pa": round(pitches_per_pa, 2),
            "avg_bf": round(avg_bf, 1),
            "avg_ip": round(avg_ip, 1),
            "swstr_pct": round(swstr_pct, 1),
            "csw_pct": round(csw_pct, 1),
            "whiff_pct": round(whiff_pct, 1),
            "putaway_pct": round(putaway_pct, 1),
            "throws": throws
        }


    def _poisson_cdf(self, k: int, lamb: float) -> float:
        if lamb <= 0:
            return 1.0
        sum_prob = 0.0
        for i in range(k + 1):
            log_term = -lamb + i * math.log(lamb) - math.lgamma(i + 1)
            sum_prob += math.exp(log_term)
        return min(1.0, sum_prob)

    def _normal_cdf(self, x: float, mean: float, std_dev: float) -> float:
        return 0.5 * (1.0 + math.erf((x - mean) / (std_dev * math.sqrt(2.0))))

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
            
        if not isinstance(results[3], Exception) and results[3]:
            self._atomic_save(os.path.join(self.data_dir, "nrfi_trends.json"), results[3])
        else:
            reason = results[3] if isinstance(results[3], Exception) else "Boş veri döndü"
            print(f"⚠️ Uyarı: OddlySpecificScraper başarısız oldu veya boş veri döndü ({reason}). Mevcut önbellek dosyası korunuyor.")

        return True

    async def run_daily_predictions_async(self):
        print("\n🚀 V8 Tahmin Motoru Başlatılıyor...")
        
        # 1. AI Servisini başlat
        ai_service = get_ai_predictor()

        # 1.5 Eski tahminleri yükle (AI Yorumlarını ve diğer kalıcı verileri korumak için)
        old_predictions_db = {}
        old_consensus_edges = None
        try:
            old_file = os.path.join(self.data_dir, "todays_predictions.json")
            if os.path.exists(old_file):
                with open(old_file, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    old_consensus_edges = old_data.get("consensus_edges")
                    for p in old_data.get("predictions", []):
                        key = (p["matchup"]["away_team"], p["matchup"]["home_team"])
                        old_predictions_db[key] = p
                print(f"✅ AI Önbellek Sistemi: {len(old_predictions_db)} eski maç tahmini diskten başarıyla kurtarıldı.")
        except Exception as e:
            print(f"⚠️ Eski tahminler yüklenirken hata oluştu: {e}")

        async with httpx.AsyncClient() as client:
            if not await self._run_scrapers_async(client):
                print("🛑 Zincirleme hata tespit edildi. Tahmin motoru durduruldu.")
                return []

            team_splits_db = await self.fetch_team_splits_async(client)
            
            # Pre-calculate team offensive strikeout ranks vs LHP and RHP (higher rank = strikes out more)
            team_k_rank_vs_lhp = {}
            team_k_rank_vs_rhp = {}
            if team_splits_db:
                lhp_sorted = sorted(
                    [(t_name, t_val.get("vs_LHP", {}).get("k_pct", 22.0)) for t_name, t_val in team_splits_db.items()],
                    key=lambda x: x[1],
                    reverse=True
                )
                team_k_rank_vs_lhp = {t_name: rank + 1 for rank, (t_name, _) in enumerate(lhp_sorted)}

                rhp_sorted = sorted(
                    [(t_name, t_val.get("vs_RHP", {}).get("k_pct", 22.0)) for t_name, t_val in team_splits_db.items()],
                    key=lambda x: x[1],
                    reverse=True
                )
                team_k_rank_vs_rhp = {t_name: rank + 1 for rank, (t_name, _) in enumerate(rhp_sorted)}
            
            # Load daily matchups
            matchups_data = self._load_json("daily_matchups.json")
            games = matchups_data.get("games", [])
            target_date = matchups_data.get("date")
            
            # Gather starting lineup rosters
            print("⚾ Starting lineups çözümleniyor...")
            unique_player_ids = set()
            for game_dict in games:
                game_pk = game_dict["game_id"]
                away_id = game_dict.get("away_team_id") or resolve_team_id(game_dict.get("away_team"))
                home_id = game_dict.get("home_team_id") or resolve_team_id(game_dict.get("home_team"))
                
                away_lineup, home_lineup = await self.get_lineup_for_game(client, game_pk, away_id, home_id)
                game_dict["away_lineup"] = away_lineup
                game_dict["home_lineup"] = home_lineup
                
                for p in away_lineup + home_lineup:
                    unique_player_ids.add(p["id"])
                    
            # Fetch all player hitting stats in parallel
            player_stats_db = {}
            if unique_player_ids:
                print(f"📡 Fetching hit stats for {len(unique_player_ids)} starting batters...")
                p_ids = list(unique_player_ids)
                p_tasks = [self.get_player_stats_async(client, pid, "hitting") for pid in p_ids]
                p_results = await asyncio.gather(*p_tasks, return_exceptions=True)
                for pid, res in zip(p_ids, p_results):
                    player_stats_db[pid] = {} if isinstance(res, Exception) else res
                    
            # Hydrate matchups with lineup averages and splits
            for game_dict in games:
                for side in ["away", "home"]:
                    lineup = game_dict[f"{side}_lineup"]
                    wrc_sum, woba_sum, k_sum, bb_sum, pitches_pa_sum = 0.0, 0.0, 0.0, 0.0, 0.0
                    swstr_sum, csw_sum, whiff_sum, oswing_sum, swing_sum = 0.0, 0.0, 0.0, 0.0, 0.0
                    count = 0
                    
                    hydrated = []
                    for player in lineup[:9]:
                        pid = player["id"]
                        raw_stat = player_stats_db.get(pid, {})
                        metrics = self.calculate_hitter_metrics(raw_stat)
                        
                        player_stat = player.copy()
                        player_stat.update(metrics)
                        hydrated.append(player_stat)
                        
                        wrc_sum += metrics["wrc_plus"]
                        woba_sum += metrics["woba"]
                        k_sum += metrics["k_pct"]
                        bb_sum += metrics["bb_pct"]
                        pitches_pa_sum += metrics["pitches_per_pa"]
                        swstr_sum += metrics["swstr_pct"]
                        csw_sum += metrics["csw_pct"]
                        whiff_sum += metrics["whiff_pct"]
                        oswing_sum += metrics["oswing_pct"]
                        swing_sum += metrics["swing_pct"]
                        count += 1
                        
                    if count > 0:
                        lineup_avg = {
                            "wrc_plus": round(wrc_sum / count, 1),
                            "woba": round(woba_sum / count, 3),
                            "k_pct": round(k_sum / count, 1),
                            "bb_pct": round(bb_sum / count, 1),
                            "pitches_per_pa": round(pitches_pa_sum / count, 2),
                            "swstr_pct": round(swstr_sum / count, 1),
                            "csw_pct": round(csw_sum / count, 1),
                            "whiff_pct": round(whiff_sum / count, 1),
                            "oswing_pct": round(oswing_sum / count, 1),
                            "swing_pct": round(swing_sum / count, 1)
                        }
                    else:
                        lineup_avg = {
                            "wrc_plus": 100.0, "woba": 0.315, "k_pct": 22.0, "bb_pct": 8.0,
                            "pitches_per_pa": 3.8, "swstr_pct": 11.9, "csw_pct": 27.1,
                            "whiff_pct": 24.8, "oswing_pct": 29.6, "swing_pct": 47.0
                        }
                        
                    game_dict[f"{side}_lineup_hydrated"] = hydrated
                    game_dict[f"{side}_lineup_avg"] = lineup_avg
                    
            # 2. Fetch Player Props Odds
            player_props_odds_db = await self.odds_provider.fetch_player_props_for_games_async(client, games)

            # Perform parallel history fetching
            print("📡 MLB API'den takımların geçmiş performansları çekiliyor (Parallel History)...")
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
        all_pitcher_projs = []
        
        print(f"\n⚾ Bugünün {len(games)} maçı için EDGE (Avantaj) analizleri yapılıyor...\n")
        print("=" * 75)

        for game_dict in games:
            try:
                try:
                    game_input = GameInputData(**game_dict)
                except ValidationError as ve:
                    print(f"❌ Veri Formatı Hatası ({game_dict.get('away_team')} vs {game_dict.get('home_team')}): {ve}")
                    continue

                trend_data = self._find_trend_data(game_input.away_team, game_input.home_team, trends_db)
                
                if trend_data:
                    trends_schema = NRFITrendSchema(**trend_data)
                else:
                    trends_schema = NRFITrendSchema(is_scraper_fallback=True)

                weather_info = weather_db.get(game_input.home_team, {})
                
                # Fetch splits and lineup averages for this game
                away_lineup_avg = game_dict.get("away_lineup_avg")
                home_lineup_avg = game_dict.get("home_lineup_avg")
                away_splits = team_splits_db.get(game_input.away_team)
                home_splits = team_splits_db.get(game_input.home_team)

                # Predict Matchup with splits & lineups
                prediction = engine.predict_matchup(
                    game_input, trends=trends_schema, weather=weather_info,
                    away_lineup_avg=away_lineup_avg, home_lineup_avg=home_lineup_avg,
                    away_splits=away_splits, home_splits=home_splits
                )

                away_team = game_input.away_team
                home_team = game_input.home_team

                # Load old odds as fallback if present
                old_game_key = (away_team, home_team)
                old_odds = None
                if old_game_key in old_predictions_db:
                    old_prediction_data = old_predictions_db[old_game_key]
                    if "Odds" in old_prediction_data:
                        old_odds = old_prediction_data["Odds"]

                status = game_dict.get("status", "Scheduled")
                status_lower = status.lower().replace("-", "")
                is_started = status_lower not in ["scheduled", "pregame", "warmup", "preview"]

                best_odds = self.odds_provider.get_best_odds_for_game(
                    away_team, home_team, live_odds_data, target_date
                )

                use_old_odds = False
                if is_started:
                    if old_odds and old_odds.get("best_away_odds", 0) > 0:
                        use_old_odds = True
                else:
                    if (best_odds["away_odds"] == 0.0 or best_odds["home_odds"] == 0.0) and old_odds and old_odds.get("best_away_odds", 0) > 0:
                        use_old_odds = True

                if use_old_odds:
                    prediction["Odds"] = old_odds
                    if is_started:
                        print(f"🔒 [Pregame Odds Freeze] Maç başladı ({status}). {away_team} vs {home_team} maçının pregame oranları donduruldu.")
                    else:
                        print(f"🔄 [Odds Fallback Cache] API oranları çekilemedi, {away_team} vs {home_team} için eski oranlar korundu.")
                else:
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

                # Attach History & Weather
                history_data = history_lookup.get((away_team, home_team), {
                    "away_l10": [], "home_l10": [], "h2h": []
                })
                prediction["History"] = history_data
                prediction["Weather"] = weather_info

                # ----------------------------------------------------
                # PITCHER PROPS PROJECTION & ODDS MATCHING (XGBoost/RF style)
                # ----------------------------------------------------
                props_engine = PitcherPropsEngine(engine.ballpark_db)
                props_odds_data = player_props_odds_db.get((away_team, home_team))
                if not props_odds_data:
                    props_odds_data = player_props_odds_db.get(f"{away_team}-{home_team}")
                    
                pitcher_projs = []
                for side, p_name in [("away", game_input.away_pitcher), ("home", game_input.home_pitcher)]:
                    if p_name and p_name != "TBD":
                        p_stat_raw = pitcher_db.get(p_name, {"era": 4.20, "fip": 4.20, "xera": 4.20, "xfip": 4.20, "k_bb_pct": 0.14, "throws": "R"})
                        p_features = self.calculate_pitcher_metrics(p_stat_raw)
                        
                        opp_side = "home" if side == "away" else "away"
                        opp_lineup_avg = game_dict.get(f"{opp_side}_lineup_avg")
                        opp_team_name = home_team if side == "away" else away_team
                        
                        # Fix A: Determine actual is_home
                        is_home = (side == "home")
                        
                        # Fix B: Get opponent splits vs LHP/RHP and inject
                        opp_splits = team_splits_db.get(opp_team_name, {}) if team_splits_db else {}
                        opp_lineup_avg_copy = opp_lineup_avg.copy() if opp_lineup_avg else {}
                        
                        k_pct_vs_lhp = opp_splits.get("vs_LHP", {}).get("k_pct", opp_lineup_avg_copy.get("k_pct", 22.0))
                        k_pct_vs_rhp = opp_splits.get("vs_RHP", {}).get("k_pct", opp_lineup_avg_copy.get("k_pct", 22.0))
                        
                        opp_lineup_avg_copy["k_pct_vs_lhp"] = k_pct_vs_lhp
                        opp_lineup_avg_copy["k_pct_vs_rhp"] = k_pct_vs_rhp
                        
                        projs = props_engine.project_pitcher_props(p_features, opp_lineup_avg_copy, weather_info, home_team, is_home=is_home)
                        proj_k = projs["projected_k"]
                        proj_outs = projs["projected_outs"]
                        
                        odds_matched = self.odds_provider.parse_pitcher_props_odds(props_odds_data, p_name)
                        
                        k_line = odds_matched["k_line"]
                        k_choice = "PASS"
                        k_edge = 0.0
                        if k_line is not None:
                            p_under = self._poisson_cdf(int(k_line), proj_k)
                            p_over = 1.0 - p_under
                            
                            implied_over = 1.0 / odds_matched["k_over_odds"] if odds_matched["k_over_odds"] > 0 else 0.0
                            implied_under = 1.0 / odds_matched["k_under_odds"] if odds_matched["k_under_odds"] > 0 else 0.0
                            
                            edge_over = p_over - implied_over
                            edge_under = p_under - implied_under
                            
                            if edge_over >= 0.05:
                                k_choice = "OVER"
                                k_edge = round(edge_over * 100, 1)
                            elif edge_under >= 0.05:
                                k_choice = "UNDER"
                                k_edge = round(edge_under * 100, 1)
                                
                        outs_line = odds_matched["outs_line"]
                        outs_choice = "PASS"
                        outs_edge = 0.0
                        if outs_line is not None:
                            p_over = 1.0 - self._normal_cdf(outs_line, proj_outs, 1.5)
                            p_under = self._normal_cdf(outs_line, proj_outs, 1.5)
                            
                            implied_over = 1.0 / odds_matched["outs_over_odds"] if odds_matched["outs_over_odds"] > 0 else 0.0
                            implied_under = 1.0 / odds_matched["outs_under_odds"] if odds_matched["outs_under_odds"] > 0 else 0.0
                            
                            edge_over = p_over - implied_over
                            edge_under = p_under - implied_under
                            
                            if edge_over >= 0.05:
                                outs_choice = "OVER"
                                outs_edge = round(edge_over * 100, 1)
                            elif edge_under >= 0.05:
                                outs_choice = "UNDER"
                                outs_edge = round(edge_under * 100, 1)

                        # Task 3: Opp K Rank & K% vs pitcher throws
                        p_throws = p_features.get("throws", "R")
                        opp_k_rank = 15
                        opp_k_pct = 22.0
                        if p_throws == "L" and opp_team_name in team_k_rank_vs_lhp:
                            opp_k_rank = team_k_rank_vs_lhp[opp_team_name]
                            opp_k_pct = k_pct_vs_lhp
                        elif p_throws == "R" and opp_team_name in team_k_rank_vs_rhp:
                            opp_k_rank = team_k_rank_vs_rhp[opp_team_name]
                            opp_k_pct = k_pct_vs_rhp

                        # Task 4: Matchup Grade & Confidence Score
                        score = 72.0
                        score += (p_features.get("k_pct", 22.0) - 22.0) * 1.0
                        score += (opp_k_pct - 22.0) * 1.5
                        
                        temp_val = float(weather_info.get("temp_f", 72.0))
                        if temp_val > 80.0:
                            score += 2.0
                        elif temp_val < 50.0:
                            score -= 3.0
                            
                        max_edge = max(k_edge, outs_edge)
                        if max_edge > 0.0:
                            score += max_edge * 1.2
                            
                        confidence_score = int(max(50, min(99, score)))
                        
                        if confidence_score >= 95:
                            matchup_grade = "A+"
                        elif confidence_score >= 90:
                            matchup_grade = "A"
                        elif confidence_score >= 85:
                            matchup_grade = "A-"
                        elif confidence_score >= 80:
                            matchup_grade = "B"
                        elif confidence_score >= 72:
                            matchup_grade = "C"
                        elif confidence_score >= 60:
                            matchup_grade = "D"
                        else:
                            matchup_grade = "F"

                        # Task 5: Pitcher recent K game logs
                        pitcher_id = game_dict.get(f"{side}_pitcher_id")
                        last_5_k = []
                        if pitcher_id:
                            last_5_k = await self.get_pitcher_last_5_k_async(client, pitcher_id)
                                
                        proj_dict = {
                            "pitcher": p_name,
                            "pitcher_id": pitcher_id,
                            "team": away_team if side == "away" else home_team,
                            "opponent": opp_team_name,
                            "throws": p_throws,
                            "proj_k": proj_k,
                            "proj_outs": proj_outs,
                            
                            "k_line": k_line,
                            "k_over_odds": odds_matched["k_over_odds"],
                            "k_under_odds": odds_matched["k_under_odds"],
                            "k_book": odds_matched["k_book"],
                            "k_choice": k_choice,
                            "k_edge": k_edge,
                            
                            "outs_line": outs_line,
                            "outs_over_odds": odds_matched["outs_over_odds"],
                            "outs_under_odds": odds_matched["outs_under_odds"],
                            "outs_book": odds_matched["outs_book"],
                            "outs_choice": outs_choice,
                            "outs_edge": outs_edge,
                            
                            "opp_k_rank": opp_k_rank,
                            "opp_k_pct": opp_k_pct,
                            "matchup_grade": matchup_grade,
                            "confidence_score": confidence_score,
                            "last_5_k": last_5_k
                        }
                        pitcher_projs.append(proj_dict)
                        all_pitcher_projs.append(proj_dict)
                        
                prediction["pitcher_projs"] = pitcher_projs
                # ----------------------------------------------------

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

            key = (away, home)
            old_pred = old_predictions_db.get(key)
            old_insight = None
            if old_pred and "Details" in old_pred:
                # Verify that starting pitchers have not changed before using cached AI insight
                old_away_sp = old_pred.get("matchup", {}).get("away_pitcher")
                old_home_sp = old_pred.get("matchup", {}).get("home_pitcher")
                curr_away_sp = pred.get("matchup", {}).get("away_pitcher")
                curr_home_sp = pred.get("matchup", {}).get("home_pitcher")
                
                if old_away_sp == curr_away_sp and old_home_sp == curr_home_sp:
                    old_insight = old_pred["Details"].get("ai_insight")
                
            if old_insight and not old_insight.startswith("AI analysis"):
                print(f"   ⚡ AI Önbelleği Koruması: {away} vs {home} için mevcut geçerli AI yorumu başarıyla korundu.")
                pred["Details"]["ai_insight"] = old_insight
                continue

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
                if not getattr(ai_service, 'quota_exhausted', False):
                    await asyncio.sleep(4.5)

        if skipped_count > 0:
            print(f"⚡ {skipped_count} maç için AI analizi atlandı (kota/sınır aşımı).")
        print("✅ Tüm AI analizleri tamamlandı.")

        # Consensus Edges Lock
        if old_consensus_edges:
            consensus_edges = old_consensus_edges
            print("🔒 [Consensus Edges Lock] Günün en iyi avantajları (Consensus Edges) kilitli kalarak korundu.")
        else:
            consensus_edges = calculate_consensus_edges(all_predictions)
            print("⚡ [Consensus Edges Lock] Bugünün Consensus Edges listesi sıfırdan hesaplandı.")

        output_path = os.path.join(self.data_dir, "todays_predictions.json")
        payload = {
            "date": matchups_data.get("date"),
            "total_games": len(all_predictions),
            "consensus_edges": consensus_edges,
            "pitcher_projections": all_pitcher_projs,
            "predictions": all_predictions,
        }

        self._atomic_save(output_path, payload)

        print(f"\n✅ EDGE Analizleri tamamlandı! {len(all_predictions)} maç verisi kaydedildi.")
        return all_predictions

    def run_daily_predictions(self):
        """Senkron tetikleyiciler için asenkron metodun sarmalayıcısı."""
        return asyncio.run(self.run_daily_predictions_async())
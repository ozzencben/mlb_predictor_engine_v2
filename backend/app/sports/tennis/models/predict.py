import sys
import json
import math
import asyncio
import httpx
from pathlib import Path
import xgboost as xgb

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# Add root folder to sys.path to resolve 'app' imports correctly
project_root = Path(__file__).parent.parent.parent.parent.parent.resolve()
sys.path.append(str(project_root))

from datetime import datetime
from zoneinfo import ZoneInfo
from app.sports.tennis.services.odds_provider import TennisOddsProvider
from app.sports.tennis.services.feature_builder import (
    is_player_match,
    load_player_matches,
    calculate_surface_win_rate,
    calculate_momentum_score,
    calculate_fatigue_score,
    get_player_rank,
    calculate_dominance_score,
    calculate_h2h_score,
    calculate_game_dominance,
    calculate_rest_days,
    calculate_tiebreak_win_rate,
    calculate_first_set_win_rate,
    calculate_comeback_rate,
    calculate_close_set_rate,
    calculate_avg_games_per_set,
    calculate_bagel_breadstick_rate,
    clear_matches_cache,
    _load_pi_to_id_cache
)

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data"
brain_path = data_dir / "tennis_brain.json"

_player_elo_cache = None

def _load_player_elo():
    global _player_elo_cache
    if _player_elo_cache is not None:
        return _player_elo_cache
    
    elo_path = data_dir / "player_elo.json"
    if elo_path.exists():
        try:
            with open(elo_path, "r", encoding="utf-8") as f:
                _player_elo_cache = json.load(f)
        except Exception:
            _player_elo_cache = {}
    else:
        _player_elo_cache = {}
    return _player_elo_cache

def reset_elo_cache():
    """Resets the in-memory Elo cache so the next call re-reads from disk."""
    global _player_elo_cache
    _player_elo_cache = None

_calibration_cache = None

def _load_calibration():
    global _calibration_cache
    if _calibration_cache is not None:
        return _calibration_cache
    calib_path = data_dir / "tennis_brain_calibration.json"
    if calib_path.exists():
        try:
            with open(calib_path, "r", encoding="utf-8") as f:
                _calibration_cache = json.load(f)
        except Exception:
            _calibration_cache = {}
    else:
        _calibration_cache = {}
    return _calibration_cache

def _calibrate_prob(raw_prob):
    """Applies Platt scaling calibration to a raw XGBoost probability."""
    cal = _load_calibration()
    if not cal or "coef" not in cal:
        return raw_prob
    coef = cal["coef"]
    intercept = cal["intercept"]
    logit = coef * raw_prob + intercept
    return 1.0 / (1.0 + math.exp(-logit))

def get_player_elo_from_cache(p_id, p_name, surface):
    elo_data = _load_player_elo()
    pi_to_id = _load_pi_to_id_cache()
    p_key = pi_to_id.get(p_id, p_id) # Resolves to numeric ID if available
    
    if p_key not in elo_data:
        p_key = p_name.lower().strip()
    
    if p_key in elo_data:
        if surface == "Indoors" or surface == "Unknown":
            surface = "Hard"
        return elo_data[p_key].get(surface, 1500)
    return 1500


def get_current_player_features(p1_name, p1_id, p2_name, p2_id, current_ground):
    """Returns P1's 14-feature vector vs P2 for the current match context."""
    p1_matches = load_player_matches(p1_id)
    p2_matches = load_player_matches(p2_id)

    if not p1_matches:
        return None

    # P1 metrics
    p1_ground_ratio, _ = calculate_surface_win_rate(p1_matches, current_ground, p1_name)
    p1_momentum = calculate_momentum_score(p1_matches, p1_name)
    p1_fatigue = calculate_fatigue_score(p1_matches, target_matches=3)
    p1_rank = get_player_rank(p1_name)
    p1_dominance = calculate_dominance_score(p1_matches, p1_name)

    # P2 defaults
    p2_ground_ratio = 0.5
    p2_momentum = 0.5
    p2_fatigue = 5
    p2_rank = get_player_rank(p2_name)
    p2_dominance = 0.5
    p2_game_dominance = 0.5
    p2_rest_days = 7
    p2_tiebreak_rate = 0.5
    p2_first_set_rate = 0.5
    p2_comeback_rate = 0.5
    p2_avg_games = 11.0

    if p2_matches:
        p2_ground_ratio, _ = calculate_surface_win_rate(p2_matches, current_ground, p2_name)
        p2_momentum = calculate_momentum_score(p2_matches, p2_name)
        p2_fatigue = calculate_fatigue_score(p2_matches, target_matches=3)
        p2_dominance = calculate_dominance_score(p2_matches, p2_name)
        p2_tiebreak_rate = calculate_tiebreak_win_rate(p2_matches, p2_name)
        p2_first_set_rate = calculate_first_set_win_rate(p2_matches, p2_name)
        p2_comeback_rate = calculate_comeback_rate(p2_matches, p2_name)
        p2_avg_games = calculate_avg_games_per_set(p2_matches, p2_name)

    # Differential features
    momentum_diff = p1_momentum - p2_momentum
    ground_diff = p1_ground_ratio - p2_ground_ratio
    rank_diff = p1_rank - p2_rank
    dominance_diff = p1_dominance - p2_dominance
    fatigue_diff = p1_fatigue - p2_fatigue

    h2h_score = calculate_h2h_score(p1_matches, p1_name, p2_name) - 0.5

    today_str = datetime.now().strftime("%Y-%m-%d")
    p1_game_dominance = calculate_game_dominance(p1_matches, p1_name)
    p1_rest_days = calculate_rest_days(today_str, p1_matches)

    if p2_matches:
        p2_game_dominance = calculate_game_dominance(p2_matches, p2_name)
        p2_rest_days = calculate_rest_days(today_str, p2_matches)

    game_dominance_diff = p1_game_dominance - p2_game_dominance
    rest_days_diff = p1_rest_days - p2_rest_days

    # New set-score based metrics
    p1_tiebreak_rate = calculate_tiebreak_win_rate(p1_matches, p1_name)
    p1_first_set_rate = calculate_first_set_win_rate(p1_matches, p1_name)
    p1_comeback_rate = calculate_comeback_rate(p1_matches, p1_name)
    p1_avg_games = calculate_avg_games_per_set(p1_matches, p1_name)

    tiebreak_rate_diff = p1_tiebreak_rate - p2_tiebreak_rate
    first_set_rate_diff = p1_first_set_rate - p2_first_set_rate
    comeback_rate_diff = p1_comeback_rate - p2_comeback_rate
    avg_games_diff = p1_avg_games - p2_avg_games

    # Surface Elo
    p1_elo = get_player_elo_from_cache(p1_id, p1_name, current_ground)
    p2_elo = get_player_elo_from_cache(p2_id, p2_name, current_ground)
    surface_elo_diff = p1_elo - p2_elo

    # Grass court adjustment
    if current_ground == "Grass":
        momentum_diff = momentum_diff * 1.20
        surface_elo_diff = surface_elo_diff * 0.90

    return [
        p1_ground_ratio,
        momentum_diff,
        ground_diff,
        fatigue_diff,
        rank_diff,
        dominance_diff,
        h2h_score,
        game_dominance_diff,
        rest_days_diff,
        surface_elo_diff,
        tiebreak_rate_diff,
        first_set_rate_diff,
        comeback_rate_diff,
        avg_games_diff,
    ]

def detect_surface(tournament_name: str) -> str:
    if not tournament_name:
        return "Hard"
    name_lower = tournament_name.lower()
    if "grass" in name_lower:
        return "Grass"
    elif "clay" in name_lower:
        return "Clay"
    elif "hard" in name_lower or "carpet" in name_lower:
        return "Hard"
    elif "indoors" in name_lower or "indoor" in name_lower:
        return "Hard"
    return "Hard"

def get_match_prediction(p1_name, p1_id, p2_name, p2_id, ground_type, model):
    p1_features = get_current_player_features(p1_name, p1_id, p2_name, p2_id, ground_type)
    p2_features = get_current_player_features(p2_name, p2_id, p1_name, p1_id, ground_type)

    if not p1_features or not p2_features:
        return None

    p1_raw_prob = _calibrate_prob(model.predict_proba([p1_features])[0][1])
    p2_raw_prob = _calibrate_prob(model.predict_proba([p2_features])[0][1])

    sum_prob = p1_raw_prob + p2_raw_prob
    if sum_prob == 0.0:
        p1_win_chance = 50.0
    else:
        p1_win_chance = (p1_raw_prob / sum_prob) * 100

    return float(p1_win_chance)

def _prob_to_model_odds(p: float, vig: float = 0.05) -> float:
    """Converts a win probability (0-1) to decimal model-implied odds with a small vig."""
    p = max(0.10, min(0.92, p))
    return round((1.0 - vig) / p, 2)


def generate_alternative_bets(model_prob_p1, p1_metrics, p2_metrics):
    """
    Rule engine: produces alternative market recommendations using model probabilities
    and player metrics. Each recommendation includes probability and model-implied odds.
    Markets: Set Handicap, Total Games O/U, Game Spread, Both Players to Win a Set,
    First Set Winner, Any Set to Tiebreak, Bagel/Breadstick.
    """
    recommendations = []

    p1_name = p1_metrics["name"]
    p2_name = p2_metrics["name"]

    is_p1_fav = model_prob_p1 >= 50.0
    fav_prob = model_prob_p1 if is_p1_fav else (100.0 - model_prob_p1)

    favorite = p1_metrics if is_p1_fav else p2_metrics
    underdog = p2_metrics if is_p1_fav else p1_metrics

    fav_name = favorite["name"]
    und_name = underdog["name"]

    set_dominance_diff = favorite["set_dominance"] - underdog["set_dominance"]
    game_dominance_diff = favorite["game_dominance"] - underdog["game_dominance"]

    # ── 1. SET HANDİKAPI ───────────────────────────────────────────────────
    if fav_prob >= 70.0 and set_dominance_diff > 0.15 and favorite["fatigue"] <= 6:
        p_straight = max(0.35, min(0.82, (fav_prob - 50) / 100 * 1.5 + 0.35 + set_dominance_diff * 0.5))
        recommendations.append({
            "market": "Set Handicap",
            "selection": f"{fav_name} -1.5 Sets",
            "confidence": "High",
            "probability": round(p_straight * 100, 1),
            "model_odds": _prob_to_model_odds(p_straight),
            "reason": f"AI models project {fav_name} for a straight-set win backed by set dominance diff (+{set_dominance_diff*100:.1f}%) and optimal fatigue ({favorite['fatigue']} sets)."
        })
    elif fav_prob < 58.0 or favorite["fatigue"] >= 8:
        p_cover = max(0.40, min(0.80, 1.0 - max(0.15, (fav_prob - 50) / 100 * 1.2 + 0.25)))
        if fav_prob < 58.0:
            reason_str = f"Close projection ({fav_prob:.1f}%) indicates a tight contest — value on {und_name} to take at least one set."
        else:
            reason_str = f"{fav_name} carries high fatigue ({favorite['fatigue']} sets in last 3 matches), creating a set-cover opportunity for {und_name}."
        recommendations.append({
            "market": "Set Handicap",
            "selection": f"{und_name} +1.5 Sets",
            "confidence": "Medium",
            "probability": round(p_cover * 100, 1),
            "model_odds": _prob_to_model_odds(p_cover),
            "reason": reason_str
        })

    # ── 2. TOPLAM OYUN ALT/ÜST ─────────────────────────────────────────────
    p1_avg = p1_metrics.get("avg_games_per_set", 11.0)
    p2_avg = p2_metrics.get("avg_games_per_set", 11.0)
    combined_avg = (p1_avg + p2_avg) / 2.0
    abs_set_dom_diff = abs(p1_metrics["set_dominance"] - p2_metrics["set_dominance"])

    if combined_avg >= 11.5 or (abs_set_dom_diff < 0.08 and fav_prob < 58.0):
        line = "Over 22.5 Games" if combined_avg >= 11.8 else "Over 21.5 Games"
        base = 11.8 if combined_avg >= 11.8 else 11.5
        p_over = max(0.40, min(0.80, (combined_avg - base + 0.3) / 2.5 + 0.45))
        recommendations.append({
            "market": "Total Games",
            "selection": line,
            "confidence": "High" if combined_avg >= 11.8 else "Medium",
            "probability": round(p_over * 100, 1),
            "model_odds": _prob_to_model_odds(p_over),
            "reason": f"Both players average {p1_avg:.1f} and {p2_avg:.1f} games/set — combined style projects a high-game-count match ({line})."
        })
    elif combined_avg <= 10.3 and fav_prob >= 72.0:
        p_under = max(0.42, min(0.80, (11.5 - combined_avg) / 2.5 + 0.38 + (fav_prob - 50) / 300))
        recommendations.append({
            "market": "Total Games",
            "selection": "Under 21.5 Games",
            "confidence": "High" if fav_prob >= 78.0 else "Medium",
            "probability": round(p_under * 100, 1),
            "model_odds": _prob_to_model_odds(p_under),
            "reason": f"Quick-set profiles (avg {p1_avg:.1f}/{p2_avg:.1f} games/set) and a dominant favorite ({fav_prob:.1f}%) point to an efficient, low-game match."
        })

    # ── 3. OYUN HANDİKAPI ─────────────────────────────────────────────────
    if game_dominance_diff > 0.08 and fav_prob >= 65.0 and favorite["fatigue"] < 7:
        spread = "-4.5 Games" if game_dominance_diff > 0.12 else "-3.5 Games"
        p_spread = max(0.40, min(0.78, game_dominance_diff * 2.2 + (fav_prob - 50) / 150 + 0.40))
        recommendations.append({
            "market": "Game Spread",
            "selection": f"{fav_name} {spread}",
            "confidence": "High",
            "probability": round(p_spread * 100, 1),
            "model_odds": _prob_to_model_odds(p_spread),
            "reason": f"Game dominance diff of +{game_dominance_diff*100:.1f}% and low fatigue for {fav_name} support a comfortable margin across sets."
        })

    # ── 4. BOTH PLAYERS TO WIN A SET ──────────────────────────────────────
    fav_straight_rate = favorite.get("straight_sets_rate", 50.0) / 100.0
    und_comeback_rate = underdog.get("comeback_rate", 50.0) / 100.0

    p_three_sets = max(0.20, min(0.88, (
        (1.0 - fav_straight_rate) * 0.45
        + (1.0 - fav_prob / 100.0) * 0.35
        + und_comeback_rate * 0.20
    )))

    if p_three_sets >= 0.55:
        conf = "High" if p_three_sets >= 0.65 else "Medium"
        recommendations.append({
            "market": "Both Players to Win a Set",
            "selection": "Yes",
            "confidence": conf,
            "probability": round(p_three_sets * 100, 1),
            "model_odds": _prob_to_model_odds(p_three_sets),
            "reason": (
                f"{und_name} has a {und_comeback_rate*100:.0f}% comeback rate and "
                f"{fav_name} wins in straight sets only {fav_straight_rate*100:.0f}% of the time — "
                f"a competitive 3-set battle is the projected outcome."
            )
        })
    elif p_three_sets < 0.38 and fav_prob >= 68.0:
        p_no = 1.0 - p_three_sets
        conf = "High" if p_three_sets < 0.28 else "Medium"
        recommendations.append({
            "market": "Both Players to Win a Set",
            "selection": "No",
            "confidence": conf,
            "probability": round(p_no * 100, 1),
            "model_odds": _prob_to_model_odds(p_no),
            "reason": (
                f"{fav_name} wins in straight sets {fav_straight_rate*100:.0f}% of the time with a {fav_prob:.1f}% "
                f"match projection — a clean sweep is the dominant scenario."
            )
        })

    # ── 5. FIRST SET WINNER ───────────────────────────────────────────────
    p1_fsr = p1_metrics.get("first_set_win_rate", 50.0) / 100.0
    p2_fsr = p2_metrics.get("first_set_win_rate", 50.0) / 100.0
    fsr_diff = p1_fsr - p2_fsr

    if abs(fsr_diff) >= 0.12:
        fsw_name = p1_name if fsr_diff > 0 else p2_name
        fsw_rate = max(0.30, min(0.88, max(p1_fsr, p2_fsr)))
        conf = "High" if abs(fsr_diff) >= 0.20 else "Medium"
        recommendations.append({
            "market": "First Set Winner",
            "selection": fsw_name,
            "confidence": conf,
            "probability": round(fsw_rate * 100, 1),
            "model_odds": _prob_to_model_odds(fsw_rate),
            "reason": (
                f"{fsw_name} wins the opening set in {fsw_rate*100:.0f}% of matches — "
                f"a +{abs(fsr_diff)*100:.0f}% edge over the opponent on the first-set market."
            )
        })

    # ── 6. ANY SET TO TIEBREAK ────────────────────────────────────────────
    p1_tbr = p1_metrics.get("tiebreak_win_rate", 50.0) / 100.0
    p2_tbr = p2_metrics.get("tiebreak_win_rate", 50.0) / 100.0
    p1_csr = p1_metrics.get("close_set_rate", 30.0) / 100.0
    p2_csr = p2_metrics.get("close_set_rate", 30.0) / 100.0

    combined_tb_prob = max(0.15, min(0.85, (
        (p1_tbr + p2_tbr) / 2.0 * 0.55
        + (p1_csr + p2_csr) / 2.0 * 0.35
        + (1.0 - fav_prob / 100.0) * 0.10
    )))

    if combined_tb_prob >= 0.48:
        conf = "High" if combined_tb_prob >= 0.58 else "Medium"
        recommendations.append({
            "market": "Any Set to Tiebreak",
            "selection": "Yes",
            "confidence": conf,
            "probability": round(combined_tb_prob * 100, 1),
            "model_odds": _prob_to_model_odds(combined_tb_prob),
            "reason": (
                f"Both players have strong tiebreak profiles "
                f"({p1_tbr*100:.0f}% / {p2_tbr*100:.0f}%) and close-set rates "
                f"({p1_csr*100:.0f}% / {p2_csr*100:.0f}%) — at least one set reaching a tiebreak is the projected outcome."
            )
        })
    elif combined_tb_prob < 0.30 and fav_prob >= 68.0:
        p_no_tb = 1.0 - combined_tb_prob
        conf = "High" if combined_tb_prob < 0.20 else "Medium"
        recommendations.append({
            "market": "Any Set to Tiebreak",
            "selection": "No",
            "confidence": conf,
            "probability": round(p_no_tb * 100, 1),
            "model_odds": _prob_to_model_odds(p_no_tb),
            "reason": (
                f"A dominant favorite ({fav_prob:.1f}%) with low close-set profiles "
                f"({p1_csr*100:.0f}% / {p2_csr*100:.0f}%) makes a clean, non-tiebreak win the likely scenario."
            )
        })

    # ── 7. BAGEL / BREADSTICK (A Set Won 6-0 or 6-1) ─────────────────────
    p1_bagel = p1_metrics.get("bagel_breadstick_rate", 10.0) / 100.0
    p2_bagel = p2_metrics.get("bagel_breadstick_rate", 10.0) / 100.0
    p_bagel = max(0.10, min(0.65, 1.0 - (1.0 - p1_bagel) * (1.0 - p2_bagel)))

    if p_bagel >= 0.28:
        conf = "High" if p_bagel >= 0.42 else "Medium"
        higher_bagel = p1_name if p1_bagel >= p2_bagel else p2_name
        recommendations.append({
            "market": "Bagel / Breadstick",
            "selection": "Yes — A Set Won 6-0 or 6-1",
            "confidence": conf,
            "probability": round(p_bagel * 100, 1),
            "model_odds": _prob_to_model_odds(p_bagel),
            "reason": (
                f"{higher_bagel} wins a dominant set (6-0/6-1) in "
                f"{max(p1_bagel, p2_bagel)*100:.0f}% of their matches — "
                f"the combined match profile projects at least one lopsided set."
            )
        })

    return recommendations

def went_to_deciding_set(match):
    home_score = match.get("home_score", 0)
    away_score = match.get("away_score", 0)
    if not isinstance(home_score, int) or not isinstance(away_score, int):
        try:
            home_score = int(home_score)
            away_score = int(away_score)
        except (ValueError, TypeError):
            return False
    
    total_sets = home_score + away_score
    if total_sets == 3:
        return True
    
    t_name = (match.get("tournament") or "").lower()
    gs_keywords = ["french open", "roland garros", "wimbledon", "us open", "australian open"]
    is_gs = any(kw in t_name for kw in gs_keywords)
    if is_gs and total_sets == 5:
        return True
        
    return False

def calculate_clutch_win_rate(matches, player_name):
    total_deciders = 0
    deciders_won = 0
    for m in matches:
        is_home = is_player_match(m["home_player"], player_name)
        is_away = is_player_match(m["away_player"], player_name)
        if not is_home and not is_away:
            continue
        if went_to_deciding_set(m):
            total_deciders += 1
            if m["winner"] == "home" and is_home:
                deciders_won += 1
            elif m["winner"] == "away" and is_away:
                deciders_won += 1
    if total_deciders == 0:
        return 0.5
    return deciders_won / total_deciders

def calculate_straight_sets_rate(matches, player_name):
    total_wins = 0
    straight_wins = 0
    for m in matches:
        is_home = is_player_match(m["home_player"], player_name)
        is_away = is_player_match(m["away_player"], player_name)
        if not is_home and not is_away:
            continue
        
        player_won = False
        if m["winner"] == "home" and is_home:
            player_won = True
        elif m["winner"] == "away" and is_away:
            player_won = True
            
        if player_won:
            total_wins += 1
            h_score = m.get("home_score", 0)
            a_score = m.get("away_score", 0)
            try:
                h_score = int(h_score)
                a_score = int(a_score)
            except (ValueError, TypeError):
                continue
            
            t_name = (m.get("tournament") or "").lower()
            gs_keywords = ["french open", "roland garros", "wimbledon", "us open", "australian open"]
            is_gs = any(kw in t_name for kw in gs_keywords)
            
            if is_gs:
                if (is_home and h_score == 3 and a_score == 0) or (is_away and a_score == 3 and h_score == 0):
                    straight_wins += 1
            else:
                if (is_home and h_score == 2 and a_score == 0) or (is_away and a_score == 2 and h_score == 0):
                    straight_wins += 1
                    
    if total_wins == 0:
        return 0.0
    return straight_wins / total_wins

def _build_recent_form(matches, player_name, count=5):
    """Son N maçın W/L özetini (rakip, skor, zemin, tarih) listesi olarak döner."""
    form = []
    for m in matches[:count]:
        is_home = is_player_match(m["home_player"], player_name)
        is_away = is_player_match(m["away_player"], player_name)
        if not is_home and not is_away:
            continue
        
        won = (m["winner"] == "home" and is_home) or (m["winner"] == "away" and is_away)
        opponent = m["away_player"] if is_home else m["home_player"]
        h_score = m.get("home_score", 0)
        a_score = m.get("away_score", 0)
        
        form.append({
            "result": "W" if won else "L",
            "opponent": opponent,
            "score": f"{h_score}-{a_score}" if is_home else f"{a_score}-{h_score}",
            "surface": m.get("ground", "Unknown"),
            "tournament": (m.get("tournament") or "Unknown").split("(")[0].strip(),
            "date": m.get("date", "")
        })
    return form

def calculate_h2h_summary(p1_name, p1_matches, p2_name, p2_matches):
    """İki oyuncunun karşılıklı geçmiş maçlarını hesaplar."""
    h2h_matches = []
    p1_wins = 0
    p2_wins = 0
    
    # P1'in maç listesinden P2 ile olan karşılaşmaları bul
    for m in p1_matches:
        opponent_home = is_player_match(m["home_player"], p2_name)
        opponent_away = is_player_match(m["away_player"], p2_name)
        
        if not opponent_home and not opponent_away:
            continue
        
        p1_is_home = is_player_match(m["home_player"], p1_name)
        p1_won = (m["winner"] == "home" and p1_is_home) or (m["winner"] == "away" and not p1_is_home)
        
        if p1_won:
            p1_wins += 1
        else:
            p2_wins += 1
        
        h_score = m.get("home_score", 0)
        a_score = m.get("away_score", 0)
        
        h2h_matches.append({
            "date": m.get("date", ""),
            "tournament": (m.get("tournament") or "Unknown").split("(")[0].strip(),
            "surface": m.get("ground", "Unknown"),
            "winner": p1_name if p1_won else p2_name,
            "score": f"{h_score}-{a_score}" if p1_is_home else f"{a_score}-{h_score}"
        })
    
    return {
        "p1_wins": p1_wins,
        "p2_wins": p2_wins,
        "total_matches": len(h2h_matches),
        "matches": h2h_matches[:5]  # Son 5 H2H maçı göster
    }

def compile_player_stats(player_name, player_id, ground, matches=None):
    if matches is None:
        matches = load_player_matches(player_id)
        
    rank = get_player_rank(player_name)
    elo = get_player_elo_from_cache(player_id, player_name, ground)
    
    if not matches:
        return {
            "rank": int(rank),
            "elo": float(elo),
            "surface_rate": 0.5,
            "momentum": 0.5,
            "fatigue": 5,
            "set_dominance": 0.5,
            "game_dominance": 0.5,
            "rest_days": 7,
            "clutch_win_rate": 50.0,
            "straight_sets_rate": 50.0,
            "tiebreak_win_rate": 50.0,
            "first_set_win_rate": 50.0,
            "comeback_rate": 50.0,
            "close_set_rate": 30.0,
            "avg_games_per_set": 11.0,
            "bagel_breadstick_rate": 10.0,
            "recent_form": []
        }
        
    surface_rate, _ = calculate_surface_win_rate(matches, ground, player_name)
    momentum = calculate_momentum_score(matches, player_name)
    fatigue = calculate_fatigue_score(matches, target_matches=3)
    set_dom = calculate_dominance_score(matches, player_name)
    game_dom = calculate_game_dominance(matches, player_name)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    rest_days = calculate_rest_days(today_str, matches)
    
    clutch = calculate_clutch_win_rate(matches, player_name)
    straight = calculate_straight_sets_rate(matches, player_name)
    tiebreak_rate = calculate_tiebreak_win_rate(matches, player_name)
    first_set_rate = calculate_first_set_win_rate(matches, player_name)
    comeback_rate = calculate_comeback_rate(matches, player_name)
    close_set_rate = calculate_close_set_rate(matches, player_name)
    avg_games = calculate_avg_games_per_set(matches, player_name)
    bagel_rate = calculate_bagel_breadstick_rate(matches, player_name)
    recent_form = _build_recent_form(matches, player_name, count=5)
    
    return {
        "rank": int(rank),
        "elo": float(elo),
        "surface_rate": round(float(surface_rate), 3),
        "momentum": round(float(momentum), 3),
        "fatigue": int(fatigue),
        "set_dominance": round(float(set_dom), 3),
        "game_dominance": round(float(game_dom), 3),
        "rest_days": int(rest_days),
        "clutch_win_rate": round(clutch * 100, 1),
        "straight_sets_rate": round(straight * 100, 1),
        "tiebreak_win_rate": round(tiebreak_rate * 100, 1),
        "first_set_win_rate": round(first_set_rate * 100, 1),
        "comeback_rate": round(comeback_rate * 100, 1),
        "close_set_rate": round(close_set_rate * 100, 1),
        "avg_games_per_set": round(avg_games, 2),
        "bagel_breadstick_rate": round(bagel_rate * 100, 1),
        "recent_form": recent_form
    }

async def generate_tennis_ai_insights_async(predictions):
    from app.services.ai.factory import get_ai_predictor
    predictor = get_ai_predictor()
    
    for p in predictions.get("active_predictions", []):
        print(f"Generating AI insight for main play: {p['home_player']} vs {p['away_player']}...")
        try:
            p["ai_insight"] = await predictor.generate_tennis_insight_async(p)
        except Exception as e:
            p["ai_insight"] = f"AI insight generation failed: {e}"
            
    for p in predictions.get("skipped_low_confidence", []):
        print(f"Generating AI insight for risky pick: {p['home_player']} vs {p['away_player']}...")
        try:
            p["ai_insight"] = await predictor.generate_tennis_insight_async(p)
        except Exception as e:
            p["ai_insight"] = f"AI insight generation failed: {e}"

def predict_today_matches():
    fixtures_path = data_dir / "today_matches.json"
    if not fixtures_path.exists():
        print("Hata: today_matches.json bulunamadi. Lutfen once fetch_fexture.py calistirin.")
        return

    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # status_code == "1" means Not Started
    unplayed = [m for m in fixtures if m.get("status_code") == "1"]

    if not unplayed:
        print("\nTahmin edilecek oynanmamis (baslamamis) mac bulunamadi.")
        return

    if not brain_path.exists():
        print("Hata: tennis_brain.json bulunamadi. Once train_model.py calistirilmalidir.")
        return

    model = xgb.XGBClassifier()
    model.load_model(str(brain_path))

    # Tenis Oran Sağlayıcısını başlat ve oranları çek
    odds_provider = TennisOddsProvider()
    async def _fetch_odds():
        async with httpx.AsyncClient() as client:
            return await odds_provider.fetch_live_tennis_odds_async(client)
            
    try:
        tennis_odds = asyncio.run(_fetch_odds())
    except Exception as e:
        print(f"⚠️ [TennisOddsProvider] Canli oranlar internetten alinamadi: {e}")
        tennis_odds = []

    if not tennis_odds:
        local_odds_path = data_dir / "live_odds_tennis.json"
        if local_odds_path.exists():
            try:
                with open(local_odds_path, "r", encoding="utf-8") as f:
                    tennis_odds = json.load(f)
                print("🔄 [TennisOddsProvider] live_odds_tennis.json lokal önbelleği yüklendi.")
            except Exception:
                pass

    active_predictions = []
    low_confidence_predictions = []
    alt_league_predictions = []
    skipped_count = 0

    for m in unplayed:
        p1_name = m["home_player"]["name"]
        p1_id = m["home_player"]["id"]
        p1_country = m["home_player"].get("country", "")
        p2_name = m["away_player"]["name"]
        p2_id = m["away_player"]["id"]
        p2_country = m["away_player"].get("country", "")
        t_name = m["tournament"]["name"] if m.get("tournament") else "Unknown"
        ground = detect_surface(t_name)

        chance = get_match_prediction(p1_name, p1_id, p2_name, p2_id, ground, model)
        if chance is None:
            skipped_count += 1
            continue

        p1_prob = chance
        p2_prob = 100 - chance
        
        predicted_winner = p1_name if p1_prob > 50 else p2_name

        # Bahis oranlarını eşleştir ve Edge/Kelly hesaplamalarını yap
        p1_odds = None
        p2_odds = None
        edge_percentage = None
        recommended_kelly_bet_percentage = None

        timestamp = m.get("timestamp")
        if timestamp and tennis_odds:
            matched_odds = odds_provider.match_odds_for_game(p1_name, p2_name, timestamp, tennis_odds)
            if matched_odds:
                p1_odds = matched_odds["p1_odds"]
                p2_odds = matched_odds["p2_odds"]
                
                win_prob = p1_prob / 100.0 if p1_prob > 50.0 else p2_prob / 100.0
                win_odds = p1_odds if p1_prob > 50.0 else p2_odds
                
                if win_odds > 1.0:
                    edge = win_prob - (1.0 / win_odds)
                    edge_percentage = round(edge * 100, 2)
                    
                    if edge > 0.0:
                        b = win_odds - 1.0
                        kelly = ((win_prob * b) - (1.0 - win_prob)) / b
                        recommended_kelly_bet_percentage = round(kelly * 0.25 * 100, 2)
                    else:
                        recommended_kelly_bet_percentage = 0.0
                else:
                    edge_percentage = 0.0
                    recommended_kelly_bet_percentage = 0.0
        
        # Alternatif Bahis Önerilerini Hesapla (Kural Motoru)
        p1_matches = load_player_matches(p1_id)
        p2_matches = load_player_matches(p2_id)
        
        p1_stats = compile_player_stats(p1_name, p1_id, ground, p1_matches)
        p1_stats["name"] = p1_name
        p2_stats = compile_player_stats(p2_name, p2_id, ground, p2_matches)
        p2_stats["name"] = p2_name
        
        alternative_bets = generate_alternative_bets(p1_prob, p1_stats, p2_stats)
        
        # H2H Geçmiş Karşılaşma Özeti
        h2h_summary = calculate_h2h_summary(p1_name, p1_matches, p2_name, p2_matches)

        round_code = m.get("round_code")
        match_stage = "Main Draw"
        if round_code:
            round_mapping = {
                "1": "Round of 32",
                "2": "Round of 16",
                "3": "Quarter-finals",
                "4": "Semi-finals",
                "5": "Final",
                "11": "Qualification Round 1",
                "12": "Qualification Round 2",
            }
            match_stage = round_mapping.get(str(round_code), f"Round {round_code}")

        match_time = "TBD"
        if timestamp:
            try:
                dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("America/New_York"))
                match_time = dt.strftime("%H:%M ET")
            except Exception:
                pass

        match_data = {
            "match_id": m["match_id"],
            "tournament": t_name,
            "match_stage": match_stage,
            "match_time": match_time,
            "timestamp": timestamp,
            "surface": ground,
            "home_player": p1_name,
            "away_player": p2_name,
            "p1_id": str(p1_id),
            "p2_id": str(p2_id),
            "p1_country": p1_country,
            "p2_country": p2_country,
            "home_win_probability": round(p1_prob, 2),
            "away_win_probability": round(p2_prob, 2),
            "predicted_winner": predicted_winner,
            "p1_odds": p1_odds,
            "p2_odds": p2_odds,
            "edge_percentage": edge_percentage,
            "recommended_kelly_bet_percentage": recommended_kelly_bet_percentage,
            "alternative_bets": alternative_bets,
            "p1_stats": p1_stats,
            "p2_stats": p2_stats,
            "h2h_summary": h2h_summary
        }

        # Check Tier Filter (Challenger or ITF)
        t_upper = t_name.upper()
        if "CHALLENGER" in t_upper or "ITF" in t_upper:
            alt_league_predictions.append(match_data)
        # Check Confidence Threshold (< 60%)
        elif max(p1_prob, p2_prob) < 60.0:
            low_confidence_predictions.append(match_data)
        else:
            active_predictions.append(match_data)

    # Console Printout
    print(f"\n=== TAHMIN TALEBI SONUCLARI ({len(unplayed)} Toplam Mac) ===")
    
    if active_predictions:
        print(f"\n[+] ANA TAHMINLER (ATP & WTA - Guven >= %60) [{len(active_predictions)} Mac]")
        print(f"{'Turnuva':<45} | {'Oyuncu 1':<25} vs {'Oyuncu 2':<25} | {'Yapay Zeka Tahmini':<22} | {'Oranlar (P1/P2)':<15} | {'Kenar (Edge)':<12} | {'Kelly %':<8}")
        print("-" * 150)
        for p in active_predictions:
            t_short = p["tournament"][:42] + "..." if len(p["tournament"]) > 45 else p["tournament"]
            prob_val = max(p["home_win_probability"], p["away_win_probability"])
            prob_str = f"{p['predicted_winner']} (%{prob_val:.1f})"
            
            odds_str = f"{p['p1_odds']:.2f} / {p['p2_odds']:.2f}" if p['p1_odds'] else "- / -"
            edge_str = f"{p['edge_percentage']:+.2f}%" if p['edge_percentage'] is not None else "-"
            kelly_str = f"{p['recommended_kelly_bet_percentage']:.2f}%" if p['recommended_kelly_bet_percentage'] is not None else "-"
            
            print(f"{t_short:<45} | {p['home_player']:<25} vs {p['away_player']:<25} | {prob_str:<22} | {odds_str:<15} | {edge_str:<12} | {kelly_str:<8}")
        print("-" * 150)

    if low_confidence_predictions:
        print(f"\n[i] Skipped: Low Confidence (< %60) [{len(low_confidence_predictions)} Mac]")
        print(f"{'Turnuva':<45} | {'Oyuncu 1':<25} vs {'Oyuncu 2':<25} | {'Tahmin (Belirsiz)':<22} | {'Oranlar (P1/P2)':<15} | {'Kenar (Edge)':<12} | {'Kelly %':<8}")
        print("-" * 150)
        for p in low_confidence_predictions:
            t_short = p["tournament"][:42] + "..." if len(p["tournament"]) > 45 else p["tournament"]
            prob_val = max(p["home_win_probability"], p["away_win_probability"])
            prob_str = f"{p['predicted_winner']} (%{prob_val:.1f})"
            
            odds_str = f"{p['p1_odds']:.2f} / {p['p2_odds']:.2f}" if p['p1_odds'] else "- / -"
            edge_str = f"{p['edge_percentage']:+.2f}%" if p['edge_percentage'] is not None else "-"
            kelly_str = f"{p['recommended_kelly_bet_percentage']:.2f}%" if p['recommended_kelly_bet_percentage'] is not None else "-"
            
            print(f"{t_short:<45} | {p['home_player']:<25} vs {p['away_player']:<25} | {prob_str:<22} | {odds_str:<15} | {edge_str:<12} | {kelly_str:<8}")
        print("-" * 150)

    if alt_league_predictions:
        print(f"\n[i] Skipped: Challenger / ITF [{len(alt_league_predictions)} Mac]")
        print(f"{'Turnuva':<45} | {'Oyuncu 1':<25} vs {'Oyuncu 2':<25} | {'Tahmin (Alt Lig)':<22} | {'Oranlar (P1/P2)':<15} | {'Kenar (Edge)':<12} | {'Kelly %':<8}")
        print("-" * 150)
        for p in alt_league_predictions:
            t_short = p["tournament"][:42] + "..." if len(p["tournament"]) > 45 else p["tournament"]
            prob_val = max(p["home_win_probability"], p["away_win_probability"])
            prob_str = f"{p['predicted_winner']} (%{prob_val:.1f})"
            
            odds_str = f"{p['p1_odds']:.2f} / {p['p2_odds']:.2f}" if p['p1_odds'] else "- / -"
            edge_str = f"{p['edge_percentage']:+.2f}%" if p['edge_percentage'] is not None else "-"
            kelly_str = f"{p['recommended_kelly_bet_percentage']:.2f}%" if p['recommended_kelly_bet_percentage'] is not None else "-"
            
            print(f"{t_short:<45} | {p['home_player']:<25} vs {p['away_player']:<25} | {prob_str:<22} | {odds_str:<15} | {edge_str:<12} | {kelly_str:<8}")
        print("-" * 150)
    # Save to file (Option 2: Structured JSON)
    out_data = {
        "date": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d"),
        "active_predictions": active_predictions,
        "skipped_low_confidence": low_confidence_predictions,
        "skipped_low_tier": alt_league_predictions,
        "statistics": {
            "total_unplayed": len(unplayed),
            "active_predictions_count": len(active_predictions),
            "skipped_low_confidence_count": len(low_confidence_predictions),
            "skipped_low_tier_count": len(alt_league_predictions),
            "skipped_data_missing_count": skipped_count
        }
    }
    
    # AI Yorumlarını Asenkron Olarak Üret
    print("\n[AI] Tenis AI Edge Insight anlatilari uretiliyor...")
    try:
        async def run_tennis_ai_insights():
            await generate_tennis_ai_insights_async(out_data)
        asyncio.run(run_tennis_ai_insights())
        print("[AI] Yapay zeka yorumlari basariyla eklendi.")
    except Exception as e:
        print(f"⚠️ AI Yorumlari uretilirken hata olustu: {e}")
    
    out_path = data_dir / "today_predictions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out_data, f, ensure_ascii=False, indent=4)

    print(f"[OK] {len(active_predictions)} aktif mac tahmin edildi.")
    print(f" -> {len(low_confidence_predictions)} mac dusuk guven nedeniyle atlandi.")
    print(f" -> {len(alt_league_predictions)} mac alt lig (Challenger/ITF) nedeniyle atlandi.")
    print(f" -> {skipped_count} mac gecmis veri eksikligi nedeniyle atlandi.")
    print(f"Tahminler '{out_path}' dosyasina kaydedildi.")

def evaluate_today_accuracy():
    fixtures_path = data_dir / "today_matches.json"
    if not fixtures_path.exists():
        print("Hata: today_matches.json bulunamadi. Lutfen once fetch_fexture.py calistirin.")
        return

    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # status_code == "3" means Finished
    finished = [
        m for m in fixtures 
        if m.get("status_code") == "3" 
        and m.get("winner") in [1, 2]
        and m.get("status") != "Walkover"
    ]

    if not finished:
        print("\nDegerlendirilecek oynanmis (bitmis) mac bulunamadi.")
        return

    if not brain_path.exists():
        print("Hata: tennis_brain.json bulunamadi. Once train_model.py calistirilmalidir.")
        return

    model = xgb.XGBClassifier()
    model.load_model(str(brain_path))

    # Tenis Oran Sağlayıcısını başlat ve oranları çek
    odds_provider = TennisOddsProvider()
    async def _fetch_odds():
        async with httpx.AsyncClient() as client:
            return await odds_provider.fetch_live_tennis_odds_async(client)
            
    try:
        tennis_odds = asyncio.run(_fetch_odds())
    except Exception as e:
        print(f"⚠️ [TennisOddsProvider] Canli oranlar internetten alinamadi: {e}")
        tennis_odds = []

    if not tennis_odds:
        local_odds_path = data_dir / "live_odds_tennis.json"
        if local_odds_path.exists():
            try:
                with open(local_odds_path, "r", encoding="utf-8") as f:
                    tennis_odds = json.load(f)
                print("🔄 [TennisOddsProvider] live_odds_tennis.json lokal önbelleği yüklendi.")
            except Exception:
                pass

    active_results = []
    low_confidence_results = []
    alt_league_results = []
    
    correct_predictions = 0
    total_predicted = 0
    
    low_conf_correct = 0
    low_conf_total = 0
    
    alt_league_correct = 0
    alt_league_total = 0
    
    skipped_count = 0

    for m in finished:
        p1_name = m["home_player"]["name"]
        p1_id = m["home_player"]["id"]
        p2_name = m["away_player"]["name"]
        p2_id = m["away_player"]["id"]
        t_name = m["tournament"]["name"] if m.get("tournament") else "Unknown"
        ground = detect_surface(t_name)
        actual_winner = m["winner"]

        chance = get_match_prediction(p1_name, p1_id, p2_name, p2_id, ground, model)
        if chance is None:
            skipped_count += 1
            continue

        p1_prob = chance
        p2_prob = 100 - chance
        
        predicted_winner = 1 if chance > 50 else 2
        is_correct = (predicted_winner == actual_winner)

        res_str = "[DOGRU]" if is_correct else "[YANLIS]"

        # Bahis oranlarını eşleştir ve Edge/Kelly hesaplamalarını yap
        p1_odds = None
        p2_odds = None
        edge_percentage = None
        recommended_kelly_bet_percentage = None

        timestamp = m.get("timestamp")
        if timestamp and tennis_odds:
            matched_odds = odds_provider.match_odds_for_game(p1_name, p2_name, timestamp, tennis_odds)
            if matched_odds:
                p1_odds = matched_odds["p1_odds"]
                p2_odds = matched_odds["p2_odds"]
                
                win_prob = p1_prob / 100.0 if chance > 50.0 else p2_prob / 100.0
                win_odds = p1_odds if chance > 50.0 else p2_odds
                
                if win_odds > 1.0:
                    edge = win_prob - (1.0 / win_odds)
                    edge_percentage = round(edge * 100, 2)
                    
                    if edge > 0.0:
                        b = win_odds - 1.0
                        kelly = ((win_prob * b) - (1.0 - win_prob)) / b
                        recommended_kelly_bet_percentage = round(kelly * 0.25 * 100, 2)
                    else:
                        recommended_kelly_bet_percentage = 0.0
                else:
                    edge_percentage = 0.0
                    recommended_kelly_bet_percentage = 0.0

        # Alternatif Bahis Önerilerini Hesapla (Kural Motoru)
        p1_matches = load_player_matches(p1_id)
        p2_matches = load_player_matches(p2_id)
        
        p1_stats = compile_player_stats(p1_name, p1_id, ground, p1_matches)
        p1_stats["name"] = p1_name
        p2_stats = compile_player_stats(p2_name, p2_id, ground, p2_matches)
        p2_stats["name"] = p2_name
        
        alternative_bets = generate_alternative_bets(chance, p1_stats, p2_stats)

        round_code = m.get("round_code")
        match_stage = "Main Draw"
        if round_code:
            round_mapping = {
                "1": "Round of 32",
                "2": "Round of 16",
                "3": "Quarter-finals",
                "4": "Semi-finals",
                "5": "Final",
                "11": "Qualification Round 1",
                "12": "Qualification Round 2",
            }
            match_stage = round_mapping.get(str(round_code), f"Round {round_code}")

        match_time = "TBD"
        if timestamp:
            try:
                dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("America/New_York"))
                match_time = dt.strftime("%H:%M ET")
            except Exception:
                pass

        match_res = {
            "match_id": m["match_id"],
            "tournament": t_name,
            "match_stage": match_stage,
            "match_time": match_time,
            "timestamp": timestamp,
            "home_player": p1_name,
            "away_player": p2_name,
            "predicted_winner": predicted_winner,
            "actual_winner": actual_winner,
            "is_correct": is_correct,
            "home_win_probability": round(chance, 2),
            "away_win_probability": round(p2_prob, 2),
            "result_status": res_str,
            "p1_odds": p1_odds,
            "p2_odds": p2_odds,
            "edge_percentage": edge_percentage,
            "recommended_kelly_bet_percentage": recommended_kelly_bet_percentage,
            "alternative_bets": alternative_bets,
            "p1_stats": p1_stats,
            "p2_stats": p2_stats,
            "set_scores": m.get("set_scores", [])
        }

        # Check Tier Filter
        t_upper = t_name.upper()
        if "CHALLENGER" in t_upper or "ITF" in t_upper:
            alt_league_results.append(match_res)
            alt_league_total += 1
            if is_correct:
                alt_league_correct += 1
        # Check Confidence Threshold
        elif max(chance, p2_prob) < 60.0:
            low_confidence_results.append(match_res)
            low_conf_total += 1
            if is_correct:
                low_conf_correct += 1
        else:
            active_results.append(match_res)
            total_predicted += 1
            if is_correct:
                correct_predictions += 1

    # Print accuracy test results in sections
    print(f"\n=== OYNANMIS MACLARIN DOGRULUK TESTI ({len(finished)} Mac) ===")
    
    if active_results:
        print(f"\n[+] ANA TAHMINLER (ATP & WTA - Guven >= %60) [{len(active_results)} Mac]")
        print(f"{'Turnuva':<35} | {'Oyuncu 1':<22} vs {'Oyuncu 2':<22} | {'AI Tahmin':<18} | {'Gercek':<6} | {'Sonuc':<8} | {'Oranlar (P1/P2)':<15} | {'Kenar (Edge)':<12} | {'Kelly %':<8}")
        print("-" * 150)
        for r in active_results:
            t_short = r["tournament"][:32] + "..." if len(r["tournament"]) > 35 else r["tournament"]
            prob_val = max(r["home_win_probability"], r["away_win_probability"])
            p_lbl = "P1" if r["home_win_probability"] > 50 else "P2"
            p_str = f"{p_lbl} %{prob_val:.1f}"
            act_str = "P1" if r["actual_winner"] == 1 else "P2"
            
            odds_str = f"{r['p1_odds']:.2f} / {r['p2_odds']:.2f}" if r['p1_odds'] else "- / -"
            edge_str = f"{r['edge_percentage']:+.2f}%" if r['edge_percentage'] is not None else "-"
            kelly_str = f"{r['recommended_kelly_bet_percentage']:.2f}%" if r['recommended_kelly_bet_percentage'] is not None else "-"
            
            print(f"{t_short:<35} | {r['home_player']:<22} vs {r['away_player']:<22} | {p_str:<18} | {act_str:<6} | {r['result_status']:<8} | {odds_str:<15} | {edge_str:<12} | {kelly_str:<8}")
        print("-" * 150)

    if low_confidence_results:
        print(f"\n[i] Skipped: Low Confidence (< %60) [{len(low_confidence_results)} Mac]")
        print(f"{'Turnuva':<35} | {'Oyuncu 1':<22} vs {'Oyuncu 2':<22} | {'AI Tahmin':<18} | {'Gercek':<6} | {'Sonuc':<8} | {'Oranlar (P1/P2)':<15} | {'Kenar (Edge)':<12} | {'Kelly %':<8}")
        print("-" * 150)
        for r in low_confidence_results:
            t_short = r["tournament"][:32] + "..." if len(r["tournament"]) > 35 else r["tournament"]
            prob_val = max(r["home_win_probability"], r["away_win_probability"])
            p_lbl = "P1" if r["home_win_probability"] > 50 else "P2"
            p_str = f"{p_lbl} %{prob_val:.1f}"
            act_str = "P1" if r["actual_winner"] == 1 else "P2"
            
            odds_str = f"{r['p1_odds']:.2f} / {r['p2_odds']:.2f}" if r['p1_odds'] else "- / -"
            edge_str = f"{r['edge_percentage']:+.2f}%" if r['edge_percentage'] is not None else "-"
            kelly_str = f"{r['recommended_kelly_bet_percentage']:.2f}%" if r['recommended_kelly_bet_percentage'] is not None else "-"
            
            print(f"{t_short:<35} | {r['home_player']:<22} vs {r['away_player']:<22} | {p_str:<18} | {act_str:<6} | {r['result_status']:<8} | {odds_str:<15} | {edge_str:<12} | {kelly_str:<8}")
        print("-" * 150)

    if alt_league_results:
        print(f"\n[i] Skipped: Challenger / ITF (Alt Ligler) [{len(alt_league_results)} Mac]")
        print(f"{'Turnuva':<35} | {'Oyuncu 1':<22} vs {'Oyuncu 2':<22} | {'AI Tahmin':<18} | {'Gercek':<6} | {'Sonuc':<8} | {'Oranlar (P1/P2)':<15} | {'Kenar (Edge)':<12} | {'Kelly %':<8}")
        print("-" * 150)
        for r in alt_league_results:
            t_short = r["tournament"][:32] + "..." if len(r["tournament"]) > 35 else r["tournament"]
            prob_val = max(r["home_win_probability"], r["away_win_probability"])
            p_lbl = "P1" if r["home_win_probability"] > 50 else "P2"
            p_str = f"{p_lbl} %{prob_val:.1f}"
            act_str = "P1" if r["actual_winner"] == 1 else "P2"
            
            odds_str = f"{r['p1_odds']:.2f} / {r['p2_odds']:.2f}" if r['p1_odds'] else "- / -"
            edge_str = f"{r['edge_percentage']:+.2f}%" if r['edge_percentage'] is not None else "-"
            kelly_str = f"{r['recommended_kelly_bet_percentage']:.2f}%" if r['recommended_kelly_bet_percentage'] is not None else "-"
            
            print(f"{t_short:<35} | {r['home_player']:<22} vs {r['away_player']:<22} | {p_str:<18} | {act_str:<6} | {r['result_status']:<8} | {odds_str:<15} | {edge_str:<12} | {kelly_str:<8}")
        print("-" * 150)

    # Detailed statistics printout
    print("\n================== DETAYLI TEST RAPORU ==================")
    active_accuracy = (correct_predictions / total_predicted) * 100 if total_predicted > 0 else 0.0
    if total_predicted > 0:
        print(f"🎯 ANA ATP & WTA (%60+ GUVEN):")
        print(f" -> Toplam Tahmin Edilen Mac: {total_predicted}")
        print(f" -> Dogru Tahmin Sayisi: {correct_predictions}")
        print(f" -> Yanlis Tahmin Sayisi: {total_predicted - correct_predictions}")
        print(f" -> Basari Orani (Accuracy): %{active_accuracy:.2f}")
    else:
        print("🎯 ANA ATP & WTA (%60+ GUVEN): Tahmin edilebilir mac bulunamadi.")

    print("-" * 57)
    low_conf_accuracy = (low_conf_correct / low_conf_total) * 100 if low_conf_total > 0 else 0.0
    if low_conf_total > 0:
        print(f"⚠️ DUSUK GUVENLI MACLAR (<%60):")
        print(f" -> Toplam Mac: {low_conf_total} | Dogru: {low_conf_correct} | Basari Orani: %{low_conf_accuracy:.2f}")
    else:
        print(f"⚠️ DUSUK GUVENLI MACLAR (<%60): Mac bulunamadi.")

    print("-" * 57)
    alt_league_accuracy = (alt_league_correct / alt_league_total) * 100 if alt_league_total > 0 else 0.0
    if alt_league_total > 0:
        print(f"🎾 CHALLENGER / ITF LIGLERI:")
        print(f" -> Toplam Mac: {alt_league_total} | Dogru: {alt_league_correct} | Basari Orani: %{alt_league_accuracy:.2f}")
    else:
        print(f"🎾 CHALLENGER / ITF LIGLERI: Mac bulunamadi.")

    print("-" * 57)
    print(f"ℹ️ Veri Eksikligi Nedeniyle Atlanan: {skipped_count}")
    print("=========================================================")

    # Save test results JSON
    out_path = data_dir / "today_accuracy_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d"),
            "active_statistics": {
                "total_predicted": total_predicted,
                "correct_predictions": correct_predictions,
                "accuracy_percentage": round(active_accuracy, 2)
            },
            "low_confidence_statistics": {
                "total_predicted": low_conf_total,
                "correct_predictions": low_conf_correct,
                "accuracy_percentage": round(low_conf_accuracy, 2)
            },
            "alt_league_statistics": {
                "total_predicted": alt_league_total,
                "correct_predictions": alt_league_correct,
                "accuracy_percentage": round(alt_league_accuracy, 2)
            },
            "skipped_count": skipped_count,
            "active_results": active_results,
            "low_confidence_results": low_confidence_results,
            "alt_league_results": alt_league_results
        }, f, ensure_ascii=False, indent=4)

def predict_match(p1_name, p2_name, p1_id, p2_id, ground_type):
    """Iki oyuncunun verilerini birlestirip muhurlu beyne sorar ve tahmini yapar."""
    if not brain_path.exists():
        print("Hata: tennis_brain.json bulunamadi. Once train_model.py calistirilmalidir.")
        return

    p1_features = get_current_player_features(p1_name, p1_id, p2_name, p2_id, ground_type)
    p2_features = get_current_player_features(p2_name, p2_id, p1_name, p1_id, ground_type)

    if not p1_features or not p2_features:
        print("Hata: Oyunculardan birinin mac gecmisi yuklenemedi!")
        return

    model = xgb.XGBClassifier()
    model.load_model(str(brain_path))

    p1_raw_prob = model.predict_proba([p1_features])[0][1]
    p2_raw_prob = model.predict_proba([p2_features])[0][1]

    sum_prob = p1_raw_prob + p2_raw_prob
    if sum_prob == 0.0:
        p1_win_chance = 50.0
    else:
        p1_win_chance = (p1_raw_prob / sum_prob) * 100

    p1_rank = get_player_rank(p1_name)
    p2_rank = get_player_rank(p2_name)

    p1_matches = load_player_matches(p1_id)
    p2_matches = load_player_matches(p2_id)
    p1_dom = calculate_dominance_score(p1_matches, p1_name)
    p2_dom = calculate_dominance_score(p2_matches, p2_name)

    today_str = datetime.now().strftime("%Y-%m-%d")
    p1_game_dom = calculate_game_dominance(p1_matches, p1_name)
    p2_game_dom = calculate_game_dominance(p2_matches, p2_name)
    p1_rest = calculate_rest_days(today_str, p1_matches)
    p2_rest = calculate_rest_days(today_str, p2_matches)

    p1_elo = get_player_elo_from_cache(p1_id, p1_name, ground_type)
    p2_elo = get_player_elo_from_cache(p2_id, p2_name, ground_type)

    print("\n==============================================")
    print("       CANLI YAPAY ZEKA TAHMIN MOTORU         ")
    print("==============================================")
    print(f"Zemin Turu: {ground_type}")
    print("----------------------------------------------")
    print(f"[P1] {p1_name} -> Rank: {p1_rank} | Elo: {p1_elo:.0f} | Zemin: %{p1_features[0]*100:.1f} | Form: {p1_features[1]:+.2f} | Set Dom: %{p1_dom*100:.1f} | Oyun Dom: %{p1_game_dom*100:.1f} | Yorgunluk Fark: {p1_features[3]:+.0f} set | Dinlenme: {p1_rest} gun")
    print(f"[P2] {p2_name} -> Rank: {p2_rank} | Elo: {p2_elo:.0f} | Zemin: %{p2_features[0]*100:.1f} | Form: {p2_features[1]:+.2f} | Set Dom: %{p2_dom*100:.1f} | Oyun Dom: %{p2_game_dom*100:.1f} | Yorgunluk Fark: {p2_features[3]:+.0f} set | Dinlenme: {p2_rest} gun")
    print("----------------------------------------------")
    print("Diferansiyel Farklar (P1 - P2):")
    print(f"   -> Elo: {p1_features[9]:+.0f} | Set Dom: {p1_features[5]:+.2f} | Oyun Dom: {p1_features[7]:+.2f} | Dinlenme: {p1_features[8]:+d} gun")
    print(f"   -> TB Win Rate: {p1_features[10]:+.2f} | 1st Set Win Rate: {p1_features[11]:+.2f} | Comeback Rate: {p1_features[12]:+.2f} | Avg Games/Set: {p1_features[13]:+.1f}")
    print("----------------------------------------------")
    print(f"Head-to-Head (H2H) Ustunlugu (P1 vs P2): %{p1_features[6]*100:.1f}")
    print("----------------------------------------------")
    print("YAPAY ZEKA TAHMINI:")
    print(f"-> {p1_name} kazanma olasiligi: %{p1_win_chance:.2f}")
    print(f"-> {p2_name} kazanma olasiligi: %{100 - p1_win_chance:.2f}")
    print("==============================================\n")

if __name__ == "__main__":
    # Check CLI arguments
    action = None
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["--today", "-today", "today"]:
            action = "today"
        elif arg in ["--test", "-test", "test"]:
            action = "test"
            
    if action == "today":
        predict_today_matches()
    elif action == "test":
        evaluate_today_accuracy()
    else:
        # Default: run both to show all statistics
        print("TENNIS PREDICTOR RUNNING BOTH MODES")
        print("Kullanim:")
        print("  uv run python app/sports/tennis/models/predict.py --today")
        print("  uv run python app/sports/tennis/models/predict.py --test")
        print("="*60)
        predict_today_matches()
        print("="*60)
        evaluate_today_accuracy()
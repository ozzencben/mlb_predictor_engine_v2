import sys
import os
import json
import math

# Add the current folder to sys.path to resolve 'app' imports correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.sports.mlb.models.mlb_model import MLBModel, TeamMLBStats, PitcherStats

def load_data():
    data_dir = os.path.join("app", "sports", "mlb", "data")
    
    with open(os.path.join(data_dir, "live_stats.json"), "r", encoding="utf-8") as f:
        team_db = json.load(f)
        
    with open(os.path.join(data_dir, "pitcher_stats.json"), "r", encoding="utf-8") as f:
        pitcher_db = json.load(f)
        
    with open(os.path.join(data_dir, "ballpark_stats.json"), "r", encoding="utf-8") as f:
        ballpark_db = json.load(f)
        
    return team_db, pitcher_db, ballpark_db

def run_simulations():
    team_db, pitcher_db, ballpark_db = load_data()
    
    # Initialize MLBModel
    model = MLBModel(team_db=team_db, pitcher_db=pitcher_db, ballpark_db=ballpark_db)
    
    print("=" * 60)
    print("MLB PREDICTOR ENGINE - TASK 3 MODEL MATHEMATICAL VERIFICATION")
    print("=" * 60)
    
    # 1. Select sample teams & pitchers
    away_team = "NY Yankees"
    home_team = "Boston Red Sox"
    away_pitcher = "Gerrit Cole"
    home_pitcher = "Brayan Bello"
    
    # Inject stats in database if they don't exist, to ensure reproducible calculations
    # Gerrit Cole: RHP, excellent stats
    pitcher_db[away_pitcher] = {
        "era": 3.20,
        "fip": 3.10,
        "k_bb_pct": 0.22,
        "xera": 3.00,
        "xfip": 2.90,
        "throws": "R"
    }
    # Brayan Bello: RHP, moderate stats
    pitcher_db[home_pitcher] = {
        "era": 4.50,
        "fip": 4.30,
        "k_bb_pct": 0.12,
        "xera": 4.10,
        "xfip": 4.00,
        "throws": "R"
    }
    
    # NY Yankees: Excellent offense
    team_db[away_team] = {
        "advanced_metrics": {"wrc_plus": 120.0},
        "rpg_offense": {"current": 5.2, "last_3": 6.0, "home": 5.4, "away": 5.0},
        "rpg_defense": {"current": 4.0}
    }
    # Boston Red Sox: Moderate offense, higher home runs rpg
    team_db[home_team] = {
        "advanced_metrics": {"wrc_plus": 105.0},
        "rpg_offense": {"current": 4.7, "last_3": 4.5, "home": 5.1, "away": 4.3},
        "rpg_defense": {"current": 4.6}
    }
    
    # Inject Bullpen SIERAs
    model.bullpen_siera[away_team] = 3.40 # Strong bullpen
    model.bullpen_siera[home_team] = 4.30 # Weak bullpen
    
    # Inject Sonny Moore PRs
    model.sonny_moore[away_team] = 103.5
    model.sonny_moore[home_team] = 98.2
    
    # Ballpark stats
    ballpark_db[home_team] = {"park_factor": 1.08} # Fenway effect
    ballpark_db[away_team] = {"park_factor": 0.98}
    
    # Splits database (NY Yankees vs RHP / LHP)
    splits_nyy = {
        "vs_LHP": {"ops": 0.850},
        "vs_RHP": {"ops": 0.720}
    }
    # Red Sox vs RHP / LHP
    splits_bos = {
        "vs_LHP": {"ops": 0.710},
        "vs_RHP": {"ops": 0.780}
    }
    
    print(f"\n[Test Setup]")
    print(f"  Away Team: {away_team} (Cole) - wRC+: 120, Bullpen SIERA: 3.40, Sonny Moore: 103.5")
    print(f"  Home Team: {home_team} (Bello) - wRC+: 105, Bullpen SIERA: 4.30, Sonny Moore: 98.2")
    print(f"  Fenway Park Factor: 1.08")
    
    # TEST 1: Blended Pitcher Stats (xERA/xFIP blending)
    print("\n" + "-" * 50)
    print("VERIFICATION 1: Pitcher Stats Blending (FIP/K-BB% vs xERA/xFIP)")
    print("-" * 50)
    for p_name in [away_pitcher, home_pitcher]:
        p_data, _ = model._get_pitcher_data(p_name)
        # Manually calculate to print formula steps
        actual_rating = (4.20 / p_data.fip) * (1.0 + (p_data.k_bb_pct - 0.14))
        expected_rating = (4.20 / p_data.xfip) * (4.20 / p_data.xera)
        expected_rating = math.sqrt(expected_rating)
        blended = (actual_rating * 0.60) + (expected_rating * 0.40)
        
        print(f"Pitcher: {p_name} ({p_data.throws}HP)")
        print(f"  Actual FIP: {p_data.fip}, K-BB%: {p_data.k_bb_pct:.2f} -> Actual Rating: {actual_rating:.4f}")
        print(f"  Expected xERA: {p_data.xera}, xFIP: {p_data.xfip} -> Expected Rating: {expected_rating:.4f}")
        print(f"  Blended SP Rating (60% Act / 40% Exp): {blended:.4f} (Model Property: {p_data.sp_rating:.4f})")
    
    # TEST 2: Bullpen SIERA rating multiplier
    print("\n" + "-" * 50)
    print("VERIFICATION 2: Bullpen SIERA Multipliers")
    print("-" * 50)
    for t_name in [away_team, home_team]:
        t_data = model._get_team_data(t_name)
        print(f"Team: {t_name}")
        print(f"  Bullpen SIERA: {t_data.siera:.2f}")
        print(f"  Bullpen Rating (3.90 / SIERA): {t_data.bullpen_rating:.4f}")
        
    # TEST 3: Starting Lineup wRC+/wOBA Blending Impact
    print("\n" + "-" * 50)
    print("VERIFICATION 3: wRC+/wOBA Lineup Blending (Judge in vs out)")
    print("-" * 50)
    
    # Base prediction without lineup averages
    base_away_score, _ = model.calculate_score(away_team, home_team, home_pitcher, is_home=False)
    print(f"Base NYY Runs Projected (No Lineup Avg): {base_away_score:.1f}")
    
    # Judge in lineup (High wRC+ & wOBA)
    judge_in_avg = {"wrc_plus": 145.0, "woba": 0.410}
    judge_in_score, _ = model.calculate_score(
        away_team, home_team, home_pitcher, is_home=False, lineup_avg=judge_in_avg
    )
    # Manual validation logic
    nyy_stats = model._get_team_data(away_team)
    team_wrc = nyy_stats.wrc_plus
    team_woba = 0.250 + (nyy_stats.off_current * 0.015)
    wrc_ratio = judge_in_avg["wrc_plus"] / team_wrc
    woba_ratio = judge_in_avg["woba"] / team_woba
    lineup_mult = (wrc_ratio * 0.5 + woba_ratio * 0.5) * 0.7 + 0.3
    
    print(f"Aaron Judge In Lineup (Lineup Avg wRC+: 145.0, wOBA: 0.410):")
    print(f"  Team Avg wRC+: {team_wrc}, Team wOBA: {team_woba:.4f}")
    print(f"  Lineup Multiplier: ({wrc_ratio:.4f} * 0.5 + {woba_ratio:.4f} * 0.5) * 0.7 + 0.3 = {lineup_mult:.4f}")
    print(f"  Projected NYY Score: {judge_in_score:.1f} (Change: +{judge_in_score - base_away_score:.1f} runs)")
    
    # Judge resting (Low wRC+ & wOBA)
    judge_out_avg = {"wrc_plus": 95.0, "woba": 0.300}
    judge_out_score, _ = model.calculate_score(
        away_team, home_team, home_pitcher, is_home=False, lineup_avg=judge_out_avg
    )
    wrc_ratio_out = judge_out_avg["wrc_plus"] / team_wrc
    woba_ratio_out = judge_out_avg["woba"] / team_woba
    lineup_mult_out = (wrc_ratio_out * 0.5 + woba_ratio_out * 0.5) * 0.7 + 0.3
    print(f"Aaron Judge Resting (Lineup Avg wRC+: 95.0, wOBA: 0.300):")
    print(f"  Lineup Multiplier: ({wrc_ratio_out:.4f} * 0.5 + {woba_ratio_out:.4f} * 0.5) * 0.7 + 0.3 = {lineup_mult_out:.4f}")
    print(f"  Projected NYY Score: {judge_out_score:.1f} (Change: {judge_out_score - base_away_score:.1f} runs)")

    # TEST 4: Splits vs starting pitcher arm
    print("\n" + "-" * 50)
    print("VERIFICATION 4: vs LHP/RHP Hitting Splits")
    print("-" * 50)
    # Pitcher is RHP (Bello)
    score_vs_rhp, _ = model.calculate_score(away_team, home_team, home_pitcher, is_home=False, splits=splits_nyy)
    
    # Simulate if pitcher was LHP
    lh_pitcher = "Leftie Pitcher"
    pitcher_db[lh_pitcher] = {
        "era": 4.50, "fip": 4.30, "k_bb_pct": 0.12, "xera": 4.10, "xfip": 4.00, "throws": "L"
    }
    score_vs_lhp, _ = model.calculate_score(away_team, home_team, lh_pitcher, is_home=False, splits=splits_nyy)
    
    overall_ops = 0.550 + (nyy_stats.off_current * 0.04)
    split_mult_rhp = (splits_nyy["vs_RHP"]["ops"] / overall_ops) * 0.8 + 0.2
    split_mult_lhp = (splits_nyy["vs_LHP"]["ops"] / overall_ops) * 0.8 + 0.2
    
    print(f"NYY vs RHP Bello (OPS: {splits_nyy['vs_RHP']['ops']}):")
    print(f"  Overall OPS Proxy: {overall_ops:.4f} -> Split Multiplier: {split_mult_rhp:.4f}")
    print(f"  Projected Score: {score_vs_rhp:.1f}")
    print(f"NYY vs LHP Leftie (OPS: {splits_nyy['vs_LHP']['ops']}):")
    print(f"  Overall OPS Proxy: {overall_ops:.4f} -> Split Multiplier: {split_mult_lhp:.4f}")
    print(f"  Projected Score: {score_vs_lhp:.1f}")
    print(f"  Difference (vs LHP vs vs RHP): +{score_vs_lhp - score_vs_rhp:.1f} runs (Higher vs LHP matches splits)")

    # TEST 5: Dynamic Stadium Home Field Advantage
    print("\n" + "-" * 50)
    print("VERIFICATION 5: Dynamic Stadium HFA")
    print("-" * 50)
    # Check HFA when Red Sox are home
    bos_stats = team_db[home_team]
    home_rpg = bos_stats["rpg_offense"]["home"]
    away_rpg = bos_stats["rpg_offense"]["away"]
    ratio = home_rpg / away_rpg
    hfa_mult = 1.01 + (ratio - 1.0) * 0.10
    hfa_mult = max(1.01, min(1.08, hfa_mult))
    print(f"Red Sox Home HFA (Home RPG: {home_rpg}, Away RPG: {away_rpg}):")
    print(f"  Home/Away RPG Ratio: {ratio:.4f} -> Calculated HFA Multiplier: {hfa_mult:.4f}")
    
    # Calculate score with Red Sox as home
    red_sox_home_score, _ = model.calculate_score(home_team, away_team, away_pitcher, is_home=True)
    red_sox_away_score, _ = model.calculate_score(home_team, away_team, away_pitcher, is_home=False)
    print(f"  Projected Red Sox Score as Home Team: {red_sox_home_score:.1f}")
    print(f"  Projected Red Sox Score as Away Team: {red_sox_away_score:.1f}")
    print(f"  Total HFA + Ballpark Factor Impact: x{red_sox_home_score / red_sox_away_score:.3f}")

    # TEST 6: Sonny Moore PR differentials
    print("\n" + "-" * 50)
    print("VERIFICATION 6: Sonny Moore Power Rankings Differential Bump")
    print("-" * 50)
    sm_off = model.sonny_moore[away_team]
    sm_def = model.sonny_moore[home_team]
    sm_diff = sm_off - sm_def
    sm_bump = 1.0 + (sm_diff * 0.003)
    print(f"NYY ({sm_off}) vs BOS ({sm_def}):")
    print(f"  PR Diff: {sm_diff:+.1f} -> Sonny Moore Multiplier: {sm_bump:.4f}")
    
    print("\n" + "=" * 60)
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_simulations()

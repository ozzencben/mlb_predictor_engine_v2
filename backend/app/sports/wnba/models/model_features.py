"""WNBA model feature listeleri — tek kaynak."""

# Orijinal 12 diferansiyel (L5)
_DIFF_FEATURES: list[str] = [
    "feature_net_rating_diff",
    "feature_elo_diff",
    "feature_ppg_diff",
    "feature_efg_diff",
    "feature_tov_diff",
    "feature_pace_diff",
    "feature_ts_diff",
    "feature_reb_diff",
    "feature_rest_diff",
    "feature_b2b_fatigue",
    "feature_h2h_edge",
    "feature_hca_weight",
]

# Stage 2: L10 diferansiyel
_L10_DIFF_FEATURES: list[str] = [
    "feature_net_rating_diff_l10",
    "feature_ppg_diff_l10",
    "feature_efg_diff_l10",
]

# Stage 2: Home/Away court split (L5)
_HA_COURT_FEATURES: list[str] = [
    "feature_home_court_off_diff",
    "feature_home_court_def_diff",
]

_CONTEXT_FEATURES: list[str] = [
    "feature_opp_quality_diff",
    "feature_form_streak_diff",
]

_ABS_FEATURES: list[str] = [
    "feature_home_off_abs",
    "feature_away_off_abs",
    "feature_home_def_abs",
    "feature_away_def_abs",
    "feature_pace_abs",
]

# Stage 3: Star player / injury proxy
_STAR_FEATURES: list[str] = [
    "feature_star_out_impact_diff",
    "feature_star_out_count_diff",
    "feature_star_minutes_avail_diff",
]

# Win: diferansiyel + form/opp + L10 + H/A court + star (mutlak skorlar haric)
WIN_FEATURE_COLS: list[str] = [
    *_DIFF_FEATURES,
    *_CONTEXT_FEATURES,
    *_L10_DIFF_FEATURES,
    *_HA_COURT_FEATURES,
    *_STAR_FEATURES,
]

# Spread / Total: tam feature seti (yeniden egitimde kullanilir)
REGRESS_FEATURE_COLS: list[str] = [
    *_DIFF_FEATURES,
    *_ABS_FEATURES,
    *_CONTEXT_FEATURES,
    *_L10_DIFF_FEATURES,
    *_HA_COURT_FEATURES,
    *_STAR_FEATURES,
]

# Mevcut spread/total modelleri Stage 2 oncesi 19 feature ile egitildi
SPREAD_TOTAL_FEATURE_COLS: list[str] = [
    *_DIFF_FEATURES,
    *_ABS_FEATURES,
    *_CONTEXT_FEATURES,
]

ALL_FEATURE_COLS = REGRESS_FEATURE_COLS

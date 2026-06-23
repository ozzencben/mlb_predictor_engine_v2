from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
TEAMS_FILE = DATA_DIR / "teams.json"
RAW_GAMES_DIR = DATA_DIR / "raw" / "games"
RAW_BOX_SCORES_DIR = DATA_DIR / "raw" / "box_scores"
RAW_PLAYER_BOX_DIR = DATA_DIR / "raw" / "player_box"
BULK_PROGRESS_FILE = DATA_DIR / "raw" / "bulk_fetch_progress.json"

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba"

# 2016-2024 arası lig 12 takımdı; expansion sonrası yeni takımlar eklenir.
CORE_TEAM_IDS = {
    "20": "ATL",
    "19": "CHI",
    "18": "CON",
    "3": "DAL",
    "5": "IND",
    "17": "LV",
    "6": "LA",
    "8": "MIN",
    "9": "NY",
    "11": "PHX",
    "14": "SEA",
    "16": "WSH",
}

# Tarihsel / relokasyon franchise ID'leri (ELO gecmisinde gorunur)
HISTORICAL_TEAM_NAMES: dict[str, str] = {
    "104959": "San Antonio Stars",
    "21": "Tulsa Shock",
    "130927": "Charlotte Sting",
    "131935": "Toronto Tempo (hist)",
    "132052": "Portland Fire (hist)",
    "17473": "Detroit Shock",
    "17475": "Miami Sol",
    "17476": "Cleveland Rockers",
}

# Aktif expansion takimlari (CORE disi)
EXPANSION_TEAM_IDS = {
    "129689": "GS",
    "132052": "POR",
    "131935": "TOR",
}

DEFAULT_PIPELINE_LOOKBACK_DAYS = 14

DEFAULT_START_SEASON = 2016
DEFAULT_END_SEASON = 2026
DEFAULT_REQUEST_DELAY = 0.25

REQUIRED_BOX_FIELDS = ("FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "OREB", "DRB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS")

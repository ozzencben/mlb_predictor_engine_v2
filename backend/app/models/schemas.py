from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PitcherStatsSchema(BaseModel):
    era: float = Field(default=4.20)
    fip: float = Field(default=4.20)
    k_bb_pct: float = Field(default=0.14)
    xera: float = Field(default=4.20)
    xfip: float = Field(default=4.20)
    is_fallback: bool = Field(default=False)
    record: str = Field(default="0-0")

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, values):
        if not isinstance(values, dict):
            return values

        fallback = False
        normalized = {}
        defaults = {"era": 4.20, "fip": 4.20, "k_bb_pct": 0.14, "xera": 4.20, "xfip": 4.20}

        for field_name, default in defaults.items():
            raw = values.get(field_name, None)
            if (
                raw is None
                or raw == ""
                or (isinstance(raw, str) and raw.strip().upper() == "N/A")
            ):
                normalized[field_name] = default
                fallback = True
                continue

            try:
                normalized[field_name] = float(raw)
            except (TypeError, ValueError):
                normalized[field_name] = default
                fallback = True

        normalized["record"] = str(values.get("record", "0-0"))
        normalized["is_fallback"] = bool(values.get("is_fallback", False)) or fallback
        return normalized


class TeamStatsSchema(BaseModel):
    wrc_plus: float = Field(default=100.0)
    off_current: float = Field(default=4.5)
    off_last3: float = Field(default=4.5)
    def_current: float = Field(default=4.5)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, values):
        if not isinstance(values, dict):
            return values

        normalized = {}
        defaults = {
            "wrc_plus": 100.0,
            "off_current": 4.5,
            "off_last3": 4.5,
            "def_current": 4.5,
        }

        for field_name, default in defaults.items():
            raw = values.get(field_name, None)
            if raw is None or raw == "":
                normalized[field_name] = default
                continue
            try:
                normalized[field_name] = float(raw)
            except (TypeError, ValueError):
                normalized[field_name] = default

        return normalized


class BallparkStatsSchema(BaseModel):
    nrfi_pct: float = Field(default=0.50)
    yrfi_pct: float = Field(default=0.50)
    park_factor: float = Field(default=1.0)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, values):
        if not isinstance(values, dict):
            return values

        def _coerce(name, raw, default):
            if raw is None or raw == "":
                return default
            try:
                value = float(raw)
            except (TypeError, ValueError):
                return default

            if value > 10.0:
                return value / 100.0
            return value

        return {
            "nrfi_pct": _coerce("nrfi_pct", values.get("nrfi_pct"), 0.50),
            "yrfi_pct": _coerce("yrfi_pct", values.get("yrfi_pct"), 0.50),
            "park_factor": _coerce("park_factor", values.get("park_factor") or values.get("run_factor"), 1.0),
        }

class PitcherTrendData(BaseModel):
    season_nrfi_pct: float = Field(default=50.0)
    location_nrfi_pct: float = Field(default=50.0)
    last10_nrfi_pct: float = Field(default=50.0)
    streak_score: int = Field(default=0)
    season_record: str = Field(default="0-0")
    location_record: str = Field(default="0-0")
    last10_record: str = Field(default="0-0")
    streak_emoji: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def normalize_trend_fields(cls, values):
        if not isinstance(values, dict):
            return values
        
        normalized = {}
        for field in ["season_nrfi_pct", "location_nrfi_pct", "last10_nrfi_pct"]:
            raw = values.get(field, 50.0)
            try:
                normalized[field] = float(raw)
            except (TypeError, ValueError):
                normalized[field] = 50.0
                
        try:
            normalized["streak_score"] = int(values.get("streak_score", 0))
        except (TypeError, ValueError):
            normalized["streak_score"] = 0
            
        normalized["season_record"] = str(values.get("season_record", "0-0"))
        normalized["location_record"] = str(values.get("location_record", "0-0"))
        normalized["last10_record"] = str(values.get("last10_record", "0-0"))
        normalized["streak_emoji"] = str(values.get("streak_emoji", ""))
            
        return normalized

class NRFITrendSchema(BaseModel):
    away_pitcher: PitcherTrendData = Field(default_factory=PitcherTrendData)
    home_pitcher: PitcherTrendData = Field(default_factory=PitcherTrendData)
    away_team_nrfi: PitcherTrendData = Field(default_factory=PitcherTrendData)
    home_team_nrfi: PitcherTrendData = Field(default_factory=PitcherTrendData)
    is_scraper_fallback: bool = Field(default=False)

    # --- GERİYE DÖNÜK UYUMLULUK (FACADE PATTERN) ---
    @property
    def away_team_nrfi_pct(self) -> float:
        return self.away_pitcher.season_nrfi_pct
    
    @property
    def home_team_nrfi_pct(self) -> float:
        return self.home_pitcher.season_nrfi_pct

    @property
    def away_pitcher_nrfi_streak(self) -> int:
        return self.away_pitcher.streak_score

    @property
    def home_pitcher_nrfi_streak(self) -> int:
        return self.home_pitcher.streak_score




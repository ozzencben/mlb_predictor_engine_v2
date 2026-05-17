from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class PitcherStatsSchema(BaseModel):
    era: float = Field(default=4.20)
    fip: float = Field(default=4.20)
    k_bb_pct: float = Field(default=0.14)
    is_fallback: bool = Field(default=False)

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, values):
        if not isinstance(values, dict):
            return values

        fallback = False
        normalized = {}
        defaults = {"era": 4.20, "fip": 4.20, "k_bb_pct": 0.14}

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
            "park_factor": _coerce("park_factor", values.get("park_factor"), 1.0),
        }

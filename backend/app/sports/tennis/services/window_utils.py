"""Rolling 24-hour window helpers for tennis scheduling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

ROLLING_WINDOW_HOURS = 24
TENNIS_REFRESH_STALE_HOURS = 4


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def rolling_window_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return inclusive UTC window [now, now + ROLLING_WINDOW_HOURS]."""
    now_utc = _as_utc(now or datetime.now(timezone.utc))
    return now_utc, now_utc + timedelta(hours=ROLLING_WINDOW_HOURS)


def match_timestamp_utc(match: dict[str, Any]) -> datetime | None:
    ts = match.get("timestamp")
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def match_in_rolling_window(match: dict[str, Any], now: datetime | None = None) -> bool:
    """
    True when match kickoff is within the next ROLLING_WINDOW_HOURS.
    Matches without a timestamp but marked not-started are kept (Flashscore feed gaps).
    """
    kickoff = match_timestamp_utc(match)
    if kickoff is None:
        return match.get("status_code") == "1"

    start, end = rolling_window_bounds(now)
    return start <= kickoff <= end


def filter_matches_in_window(matches: list[dict[str, Any]], now: datetime | None = None) -> list[dict[str, Any]]:
    return [m for m in matches if match_in_rolling_window(m, now)]


def window_meta(now: datetime | None = None) -> dict[str, Any]:
    start, end = rolling_window_bounds(now)
    return {
        "window_hours": ROLLING_WINDOW_HOURS,
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def predictions_are_stale(payload: dict[str, Any] | None, max_age_hours: int = TENNIS_REFRESH_STALE_HOURS) -> bool:
    """True when rolling-window predictions should be refreshed."""
    if not payload:
        return True

    generated_at = payload.get("generated_at")
    if generated_at:
        try:
            gen_dt = datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
            age_hours = (_as_utc(datetime.now(timezone.utc)) - _as_utc(gen_dt)).total_seconds() / 3600
            if age_hours > max_age_hours:
                return True
        except ValueError:
            return True

        window_end = payload.get("window_end")
        if window_end:
            try:
                end_dt = datetime.fromisoformat(str(window_end).replace("Z", "+00:00"))
                if _as_utc(datetime.now(timezone.utc)) > _as_utc(end_dt):
                    return True
            except ValueError:
                pass
        return False

    # Legacy ET-date payloads (pre rolling-window)
    from zoneinfo import ZoneInfo
    et_today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    return payload.get("date") != et_today

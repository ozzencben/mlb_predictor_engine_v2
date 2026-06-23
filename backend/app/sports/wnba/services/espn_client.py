import time
from typing import Any

from app.sports.wnba.services.config import ESPN_BASE, DEFAULT_REQUEST_DELAY
from app.sports.wnba.services.http import make_requests_session


class EspnClient:
    def __init__(self, delay: float = DEFAULT_REQUEST_DELAY):
        self.delay = delay
        self.session = make_requests_session()
        self.request_count = 0

    def get_json(self, path: str, params: dict | None = None) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{ESPN_BASE}/{path.lstrip('/')}"
        if self.delay > 0:
            time.sleep(self.delay)
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        self.request_count += 1
        return response.json()

    def get_teams(self) -> dict[str, Any]:
        return self.get_json("/teams")

    def get_team_schedule(self, team_id: str, season: int) -> dict[str, Any]:
        return self.get_json(f"/teams/{team_id}/schedule", params={"season": season})

    def get_game_summary(self, game_id: str) -> dict[str, Any]:
        return self.get_json("/summary", params={"event": game_id})

    def get_scoreboard(self, date_str: str | None = None) -> dict[str, Any]:
        params = {"dates": date_str} if date_str else None
        return self.get_json("/scoreboard", params=params)

    def get_injuries(self) -> dict[str, Any]:
        return self.get_json("/injuries")

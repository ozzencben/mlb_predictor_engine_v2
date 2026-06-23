"""
WNBA Faz 1 — Toplu veri çekimi.

Kullanım:
  cd backend
  uv run python -m app.sports.wnba.services.bulk_fetch

  # Test (1 sezon, 5 box score):
  uv run python -m app.sports.wnba.services.bulk_fetch --test

  # Tam bulk (2016-2026):
  uv run python -m app.sports.wnba.services.bulk_fetch --start 2016 --end 2026
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from app.sports.wnba.services.config import (
    BULK_PROGRESS_FILE,
    DATA_DIR,
    DEFAULT_END_SEASON,
    DEFAULT_REQUEST_DELAY,
    DEFAULT_START_SEASON,
    RAW_BOX_SCORES_DIR,
    RAW_GAMES_DIR,
)
from app.sports.wnba.services.espn_client import EspnClient
from app.sports.wnba.services.fetch_box_scores import box_score_exists, fetch_box_score
from app.sports.wnba.services.fetch_games import fetch_season_games, load_all_games
from app.sports.wnba.services.fetch_teams import fetch_teams, load_teams


def _save_progress(data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_GAMES_DIR.mkdir(parents=True, exist_ok=True)
    RAW_BOX_SCORES_DIR.mkdir(parents=True, exist_ok=True)
    with open(BULK_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_bulk_fetch(
    start_season: int = DEFAULT_START_SEASON,
    end_season: int = DEFAULT_END_SEASON,
    delay: float = DEFAULT_REQUEST_DELAY,
    skip_existing: bool = True,
    max_box_scores: int | None = None,
    skip_box_scores: bool = False,
) -> dict:
    client = EspnClient(delay=delay)
    started_at = datetime.now(timezone.utc).isoformat()

    print("=" * 60)
    print("WNBA Faz 1 — Toplu Veri Çekimi")
    print(f"Sezon aralığı: {start_season}-{end_season} | delay={delay}s")
    print("=" * 60)

    print("\n[1/3] Takım listesi çekiliyor...")
    teams = fetch_teams(client=client, save=True)
    print(f"  -> {len(teams)} takım kaydedildi: {DATA_DIR / 'teams.json'}")

    print("\n[2/3] Sezon fikstürleri ve maç sonuçları çekiliyor...")
    season_counts: dict[int, int] = {}
    for season in range(start_season, end_season + 1):
        games = fetch_season_games(season, client=client, teams=teams, save=True)
        season_counts[season] = len(games)
        print(f"  -> {season}: {len(games)} maç")

    all_games = load_all_games(start_season, end_season)
    print(f"\n  Toplam benzersiz maç: {len(all_games)}")

    box_stats = {"fetched": 0, "skipped": 0, "failed": 0, "warnings": 0}

    if skip_box_scores:
        print("\n[3/3] Box score adımı atlandı (--skip-box-scores)")
    else:
        print("\n[3/3] Box score verileri çekiliyor...")
        target_games = all_games[:max_box_scores] if max_box_scores else all_games
        total = len(target_games)

        for idx, game in enumerate(target_games, start=1):
            game_id = game["game_id"]

            if skip_existing and box_score_exists(game_id):
                box_stats["skipped"] += 1
                if idx % 100 == 0 or idx == total:
                    print(f"  [{idx}/{total}] skipped={box_stats['skipped']} fetched={box_stats['fetched']} failed={box_stats['failed']}")
                continue

            try:
                parsed = fetch_box_score(
                    game_id,
                    client=client,
                    game_meta=game,
                    save=True,
                    skip_existing=False,
                )
                box_stats["fetched"] += 1
                if parsed and parsed.get("validation_warnings"):
                    box_stats["warnings"] += 1
            except Exception as exc:
                box_stats["failed"] += 1
                print(f"  [HATA] game_id={game_id}: {exc}")

            if idx % 25 == 0 or idx == total:
                print(
                    f"  [{idx}/{total}] fetched={box_stats['fetched']} "
                    f"skipped={box_stats['skipped']} failed={box_stats['failed']}"
                )

    finished_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "started_at": started_at,
        "finished_at": finished_at,
        "start_season": start_season,
        "end_season": end_season,
        "team_count": len(teams),
        "season_game_counts": season_counts,
        "total_unique_games": len(all_games),
        "espn_requests": client.request_count,
        "box_scores": box_stats,
    }
    _save_progress(summary)

    print("\n" + "=" * 60)
    print("Tamamlandı")
    print(f"  ESPN istek sayısı : {client.request_count}")
    print(f"  Maç kayıtları       : {RAW_GAMES_DIR}")
    print(f"  Box score kayıtları : {RAW_BOX_SCORES_DIR}")
    print(f"  İlerleme özeti      : {BULK_PROGRESS_FILE}")
    print("=" * 60)

    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WNBA Faz 1 bulk veri çekimi")
    parser.add_argument("--start", type=int, default=DEFAULT_START_SEASON, help="Başlangıç sezonu")
    parser.add_argument("--end", type=int, default=DEFAULT_END_SEASON, help="Bitiş sezonu")
    parser.add_argument("--delay", type=float, default=DEFAULT_REQUEST_DELAY, help="İstekler arası bekleme (sn)")
    parser.add_argument("--no-skip-existing", action="store_true", help="Mevcut box score dosyalarını yeniden indir")
    parser.add_argument("--skip-box-scores", action="store_true", help="Yalnızca takım + maç listesi çek")
    parser.add_argument("--max-box-scores", type=int, default=None, help="Test için box score limiti")
    parser.add_argument("--test", action="store_true", help="Hızlı test: 2024 sezonu, max 5 box score")

    args = parser.parse_args(argv)

    start = args.start
    end = args.end
    max_box = args.max_box_scores

    if args.test:
        start = end = 2024
        max_box = 5
        print("TEST MODU: 2024 sezonu, 5 box score\n")

    run_bulk_fetch(
        start_season=start,
        end_season=end,
        delay=args.delay,
        skip_existing=not args.no_skip_existing,
        max_box_scores=max_box,
        skip_box_scores=args.skip_box_scores,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

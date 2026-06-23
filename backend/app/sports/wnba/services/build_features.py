"""
WNBA Faz 2 — Feature Engineering CLI.

Çalıştırma:
  cd backend
  uv run python -m app.sports.wnba.services.build_features

  # Test modu (sadece 2024):
  uv run python -m app.sports.wnba.services.build_features --test
"""
from __future__ import annotations

import argparse
import sys
import time

from app.sports.wnba.services.team_game_logs import build_team_game_logs, load_team_game_logs
from app.sports.wnba.services.elo import build_elo_history
from app.sports.wnba.services.feature_builder import build_game_features, FEATURES_FILE
from app.sports.wnba.services.config import DATA_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WNBA Faz 2 feature engineering")
    parser.add_argument("--test", action="store_true", help="Sadece 2024 verisi (hız testi)")
    parser.add_argument("--skip-logs", action="store_true", help="team_game_logs yeniden oluşturma")
    parser.add_argument("--skip-players", action="store_true", help="player_game_logs yeniden oluşturma")
    parser.add_argument("--no-fetch-players", action="store_true", help="Eksik player box fetch etme")
    args = parser.parse_args(argv)

    t0 = time.time()
    print("=" * 60)
    print("WNBA Faz 2 — Feature Engineering")
    print("=" * 60)

    # 1. Team game logs
    print("\n[1/4] Takım maç logu oluşturuluyor...")
    if args.skip_logs:
        logs = load_team_game_logs()
        print(f"  -> Mevcut log yüklendi: {len(logs)} satır")
    else:
        start_s = 2024 if args.test else 2016
        logs = build_team_game_logs(start_season=start_s, end_season=2026, save=True)
        print(f"  -> {len(logs)} satır oluşturuldu")

    # 2. ELO geçmişi
    print("\n[2/4] Basketball ELO geçmişi hesaplanıyor...")
    elo_data = build_elo_history(logs, save=True)
    print(f"  -> {elo_data['total_games']} maç ELO güncellendi")

    # 3. Player game logs (Stage 3)
    print("\n[3/4] Oyuncu maç logları oluşturuluyor...")
    from app.sports.wnba.services.player_game_logs import build_player_game_logs, load_player_game_logs
    if args.skip_players:
        player_logs = load_player_game_logs()
        print(f"  -> Mevcut player log: {len(player_logs)} satır")
    else:
        player_logs = build_player_game_logs(
            start_season=2024 if args.test else 2016,
            end_season=2026,
            fetch_missing=not args.no_fetch_players,
            save=True,
        )
        print(f"  -> {len(player_logs)} oyuncu satırı")

    # 4. Game features
    print("\n[4/4] Maç feature'ları hesaplanıyor...")
    features = build_game_features(logs, elo_data, save=True, player_logs=player_logs)

    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"Tamamlandı ({elapsed:.1f}s)")
    print(f"  Team game logs   : {DATA_DIR / 'processed' / 'team_game_logs.json'}")
    print(f"  ELO geçmişi      : {DATA_DIR / 'processed' / 'team_elo_history.json'}")
    print(f"  Game features    : {FEATURES_FILE}")
    print(f"  Model için hazır : {len(features)} maç")
    print("=" * 60)

    if features:
        print("\nÖrnek (son 3 maç):")
        for g in features[-3:]:
            f = g["features"]
            print(
                f"  {g['date']} | {g['home_team_abbr']} vs {g['away_team_abbr']} | "
                f"sonuç: {g['target_home_win']} | spread: {g['target_spread']:+d} | "
                f"total: {g['target_total']} | "
                f"elo_diff: {f['feature_elo_diff']:+.0f} | "
                f"net_rtg_diff: {f['feature_net_rating_diff'] or 'N/A'}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())

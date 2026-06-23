"""Faz 1 veri kalite kontrolü."""
import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
GAMES_DIR = DATA / "raw" / "games"
BOX_DIR = DATA / "raw" / "box_scores"
REQUIRED = ("FGM", "FGA", "3PM", "3PA", "FTM", "FTA", "OREB", "DRB", "REB", "AST", "STL", "BLK", "TOV", "PF", "PTS")


def main() -> None:
    all_game_ids: list[str] = []
    season_stats: dict[int, dict] = {}

    for gf in sorted(GAMES_DIR.glob("*.json")):
        year = int(gf.stem)
        games = json.loads(gf.read_text(encoding="utf-8"))["games"]
        season_stats[year] = {
            "count": len(games),
            "missing_score": sum(1 for g in games if g.get("home_score") is None or g.get("away_score") is None),
            "missing_date": sum(1 for g in games if not g.get("date")),
            "missing_season": sum(1 for g in games if not g.get("season")),
        }
        all_game_ids.extend(g["game_id"] for g in games)

    unique_ids = set(all_game_ids)
    box_files = {p.stem for p in BOX_DIR.glob("*.json")}
    missing_box = sorted(unique_ids - box_files)
    extra_box = sorted(box_files - unique_ids)

    issues: list[tuple] = []
    warnings: list[tuple] = []
    score_mismatch = 0
    incomplete_box = 0

    for gf in sorted(GAMES_DIR.glob("*.json")):
        for g in json.loads(gf.read_text(encoding="utf-8"))["games"]:
            gid = g["game_id"]
            bp = BOX_DIR / f"{gid}.json"
            if not bp.exists():
                continue
            box = json.loads(bp.read_text(encoding="utf-8"))
            for side in ("home_box", "away_box"):
                missing = [f for f in REQUIRED if box.get(side, {}).get(f) is None]
                if missing:
                    incomplete_box += 1
                    issues.append((gid, side, missing))
                    break
            if box.get("validation_warnings"):
                warnings.append((gid, box["validation_warnings"]))
            hs, as_ = g.get("home_score"), g.get("away_score")
            bhs, bas = box.get("home_score"), box.get("away_score")
            if hs is not None and bhs is not None and hs != bhs:
                score_mismatch += 1
            if as_ is not None and bas is not None and as_ != bas:
                score_mismatch += 1

    print("=== WNBA FAZ 1 VERI DOGRULAMA ===")
    print(f"Toplam sezon dosyasi : {len(season_stats)}")
    print(f"Toplam mac kaydi     : {len(all_game_ids)} (benzersiz: {len(unique_ids)})")
    print(f"Box score dosyasi    : {len(box_files)}")
    print(f"Eksik box score      : {len(missing_box)}")
    print(f"Fazla box score      : {len(extra_box)}")
    print(f"Eksik stat box       : {incomplete_box}")
    print(f"Skor uyumsuzlugu     : {score_mismatch}")
    print(f"Validation warning   : {len(warnings)}")
    print()
    print("Sezon bazli:")
    for y in sorted(season_stats):
        s = season_stats[y]
        print(
            f"  {y}: {s['count']} mac | eksik skor={s['missing_score']} | "
            f"eksik tarih={s['missing_date']} | eksik season={s['missing_season']}"
        )

    if warnings:
        print("\nValidation warning dosyalari:")
        for gid, w in warnings[:10]:
            print(f"  {gid}: {w}")

    for sample_year in [2016, 2020, 2026]:
        games = json.loads((GAMES_DIR / f"{sample_year}.json").read_text(encoding="utf-8"))["games"]
        g = games[len(games) // 2]
        box = json.loads((BOX_DIR / f"{g['game_id']}.json").read_text(encoding="utf-8"))
        print(
            f"\nOrnek {sample_year}: {g['name']} | skor {g['home_score']}-{g['away_score']} | "
            f"PTS {box['home_box'].get('PTS')}-{box['away_box'].get('PTS')}"
        )


if __name__ == "__main__":
    main()

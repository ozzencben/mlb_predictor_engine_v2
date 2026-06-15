import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# Add root folder to sys.path to resolve 'app' imports correctly
project_root = Path(__file__).parent.parent.parent.parent.parent.resolve()
sys.path.append(str(project_root))

from app.sports.tennis.services.feature_builder import _load_pi_to_id_cache

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data"
raw_data_dir = data_dir / "raw" / "player_matches"

def detect_surface(tournament_name: str) -> str:
    if not tournament_name:
        return "Hard"
    name_lower = tournament_name.lower()
    if "grass" in name_lower:
        return "Grass"
    elif "clay" in name_lower:
        return "Clay"
    elif "hard" in name_lower or "carpet" in name_lower:
        return "Hard"
    elif "indoors" in name_lower or "indoor" in name_lower:
        return "Hard"
    return "Hard"

def update_player_profile(player_pi: str, player_name: str, new_match: dict, pi_to_id: dict) -> bool:
    if not player_pi or "/" in player_pi or "\\" in player_pi:
        return False
        
    # Resolve alphanumeric ID (e.g. 6HdC3z4H) to numeric ID (e.g. 866047731)
    resolved_id = pi_to_id.get(player_pi)
    if not resolved_id:
        # Fallback: if not in ranks cache, use the alphanumeric ID as filename
        resolved_id = player_pi
        
    file_path = raw_data_dir / f"{resolved_id}.json"
    
    # Load existing matches or initialize empty
    player_matches = []
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                player_matches = json.load(f)
        except Exception as e:
            print(f"Hata: {file_path.name} okunamadi: {e}")
            return False
            
    # Check if the match already exists in player matches to prevent duplicates
    match_ids = {m.get("match_id") for m in player_matches if m.get("match_id")}
    if new_match["match_id"] in match_ids:
        return False # Match already recorded, no need to update
        
    # Insert new match at the beginning (index 0)
    player_matches.insert(0, new_match)
    
    # Limit list to 50 matches (rolling buffer)
    if len(player_matches) > 50:
        player_matches = player_matches[:50]
        
    # Write back to file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(player_matches, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"Hata: {file_path.name} yazilamadi: {e}")
        return False

def main():
    fixtures_path = data_dir / "today_matches.json"
    if not fixtures_path.exists():
        print("Hata: today_matches.json bulunamadi. Lutfen once fetch_fexture.py calistirin.")
        return

    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # Filter finished matches with a valid winner, excluding walkovers
    finished_matches = [
        m for m in fixtures 
        if m.get("status_code") == "3" 
        and m.get("winner") in [1, 2]
        and m.get("status") != "Walkover"
    ]

    if not finished_matches:
        print("Guncellenecek yeni bitmis mac bulunamadi.")
        return

    pi_to_id = _load_pi_to_id_cache()
    updated_players = set()
    total_updates = 0

    print(f"\n=== PROFILLERIN GUNCELLEMESI BASLIYOR ({len(finished_matches)} Mac Analiz Ediliyor) ===")
    
    for m in finished_matches:
        t_name = m["tournament"]["name"] if m.get("tournament") else "Unknown"
        ground = detect_surface(t_name)
        
        timestamp = m.get("timestamp")
        date_text = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%d.%m. %H:%M") if timestamp else ""
        date_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d") if timestamp else ""
        
        home_name = m["home_player"]["name"]
        away_name = m["away_player"]["name"]
        
        home_score = m["home_player"]["sets_won"] if m["home_player"]["sets_won"] is not None else 0
        away_score = m["away_player"]["sets_won"] if m["away_player"]["sets_won"] is not None else 0
        
        winner_str = "home" if m["winner"] == 1 else "away"
        
        # Build matches in local profile schema format
        home_match_entry = {
            "match_id": m["match_id"],
            "tournament": t_name,
            "ground": ground,
            "date_text": date_text,
            "home_player": home_name,
            "away_player": away_name,
            "home_score": home_score,
            "away_score": away_score,
            "winner": winner_str,
            "date": date_str
        }
        
        # Home player update
        home_pi = m["home_player"]["id"]
        if home_pi:
            success = update_player_profile(home_pi, home_name, home_match_entry, pi_to_id)
            if success:
                updated_players.add(home_name)
                total_updates += 1
                
        # Away player update
        away_pi = m["away_player"]["id"]
        if away_pi:
            success = update_player_profile(away_pi, away_name, home_match_entry, pi_to_id)
            if success:
                updated_players.add(away_name)
                total_updates += 1

    print("-" * 60)
    print("[OK] Profil guncelleme operasyonu tamamlandi!")
    print(f" -> Guncellenen toplam oyuncu sayisi: {len(updated_players)}")
    print(f" -> Eklenen yeni mac kaydi sayisi: {total_updates}")
    if len(updated_players) > 0:
        print(f" -> Guncellenen bazi oyuncular: {', '.join(sorted(list(updated_players))[:8])}...")
    print("-" * 60)

if __name__ == "__main__":
    main()

import sys
import json
import time
import random
from pathlib import Path
import requests

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

base_dir = Path(__file__).parent.resolve()
# Add root folder to sys.path to resolve 'app' imports correctly
project_root = Path(__file__).parent.parent.parent.parent.resolve()
sys.path.append(str(project_root))

from app.sports.tennis.services.fetch_matches import get_player_matches

def main():
    atp_path = base_dir / "data" / "atp_ranks.json"
    wta_path = base_dir / "data" / "wta_ranks.json"
    raw_data_dir = base_dir / "data" / "raw" / "player_matches"
    raw_data_dir.mkdir(parents=True, exist_ok=True)
    
    players = []
    seen_pis = set()
    
    for rank_path in [atp_path, wta_path]:
        if rank_path.exists():
            try:
                with open(rank_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for p_id, p_info in data.items():
                        pi = p_info.get("PI")
                        p_info["ID_KEY"] = p_id
                        if pi and pi not in seen_pis:
                            seen_pis.add(pi)
                            players.append(p_info)
            except Exception as e:
                print(f"Error reading {rank_path.name}: {e}")
        else:
            print(f"Warning: {rank_path.name} not found!")
            
    total_players = len(players)
    print(f"=== GLOBAL TENNIS ENGINE: PIPELINE START ===")
    print(f"Total unique players in queue: {total_players}\n")
    
    for idx, player in enumerate(players, 1):
        pi = player.get("PI")
        pn = player.get("PN")
        pu = player.get("PU")
        p_id_key = player.get("ID_KEY")
        
        if not pi or not pu or not p_id_key:
            print(f"[{idx}/{total_players}] Skipped due to missing info: {pn}")
            continue
            
        file_path = raw_data_dir / f"{p_id_key}.json"
        
        # Resume Rule: Eğer dosya varsa, içi doluysa ve tarihli kaydı varsa atla
        if file_path.exists():
            try:
                existing_data = json.loads(file_path.read_text(encoding="utf-8"))
                if len(existing_data) > 0 and "date" in existing_data[0] and existing_data[0]["date"]:
                    print(f"[{idx}/{total_players}] Already exists (with dates): {pn}")
                    continue
            except Exception:
                pass
            
        print(f"Downloading: [{idx}/{total_players}] {pn}...")
        
        try:
            # Trigger English Scraper without session parameter
            matches = get_player_matches(p_id_key, pu, target=50)
            print(f"   -> Success! {len(matches)} matches saved.")
            
            # Anti-Ban Protection
            sleep_time = random.uniform(1.0, 2.0)
            time.sleep(sleep_time)
            
        except Exception as e:
            print(f"   -> Error pulling {pn} ({p_id_key}): {e}")
            time.sleep(1.0)

if __name__ == "__main__":
    main()
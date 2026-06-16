import re
import json
import requests
from pathlib import Path
from datetime import datetime, timezone

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data"
data_dir.mkdir(parents=True, exist_ok=True)

def get_live_flashscore_feed() -> str:
    url = "https://2.flashscore.ninja/2/x/feed/f_2_0_3_en_1"
    
    clean_headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "Origin": "https://www.flashscore.com",
        "Referer": "https://www.flashscore.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "X-fsign": "SW9D1eZo",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        response = requests.get(url, headers=clean_headers, timeout=10)

        if response.status_code == 200:
            print("[OK] Canlı veri akışı başarıyla indirildi!")
            return response.text
        else:
            print(f"Hata: Sunucu {response.status_code} hatası döndü.")
            return ""
    except Exception as e:
        print(f"Bağlantı Hatası: {e}")
        return ""

def parse_flashscore_feed(feed_text: str) -> list:
    if not feed_text:
        return []
        
    blocks = feed_text.split("~")
    matches = []
    current_tournament = None
    
    for block in blocks:
        if not block.strip():
            continue
            
        fields = block.split("¬")
        field_dict = {}
        first_key = None
        
        for idx, field in enumerate(fields):
            if "÷" in field:
                k, v = field.split("÷", 1)
                field_dict[k] = v
                if idx == 0:
                    first_key = k
                    
        if not first_key:
            continue
            
        if first_key == "ZA":
            t_name = field_dict.get("ZA", "")
            if "ITF" in t_name.upper():
                current_tournament = None
            else:
                current_tournament = {
                    "name": t_name,
                    "id": field_dict.get("ZEE"),
                    "country_id": field_dict.get("ZB"),
                    "category_id": field_dict.get("ZC"),
                    "url": field_dict.get("ZL"),
                    "gender": "Singles" if "SINGLES" in t_name.upper() else ("Doubles" if "DOUBLES" in t_name.upper() else "Unknown")
                }
        elif first_key == "AA":
            match_id = field_dict.get("AA")
            if not match_id or not current_tournament:
                continue
                
            set_scores = []
            for h_key, a_key in [('BA', 'BB'), ('BC', 'BD'), ('BE', 'BF'), ('BG', 'BH'), ('BI', 'BJ')]:
                if h_key in field_dict or a_key in field_dict:
                    set_scores.append({
                        "home": field_dict.get(h_key),
                        "away": field_dict.get(a_key)
                    })
            
            ab_code = field_dict.get("AB")
            ac_code = field_dict.get("AC")
            note = field_dict.get("AM")
            
            status_text = "Unknown"
            if ab_code == "1":
                status_text = "Not Started"
            elif ab_code == "2":
                status_text = f"Live (Set {len(set_scores)})" if set_scores else "Live"
            elif ab_code == "3":
                if ac_code == "5":
                    status_text = "Walkover"
                elif ac_code == "8":
                    status_text = "Retired"
                else:
                    status_text = "Finished"
            elif ab_code == "4":
                status_text = "Postponed"
            elif ab_code == "5":
                status_text = "Cancelled"
            elif ab_code == "6":
                status_text = "Abandoned"
            
            timestamp = int(field_dict.get("AD")) if field_dict.get("AD") else None
            date_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat() if timestamp else None
            
            match_data = {
                "match_id": match_id,
                "timestamp": timestamp,
                "date_utc": date_str,
                "status_code": ab_code,
                "detail_code": ac_code,
                "status": status_text,
                "note": note,
                "round_code": field_dict.get("CR"),
                "home_player": {
                    "name": field_dict.get("AE"),
                    "short_name": field_dict.get("WM"),
                    "id": field_dict.get("PX"),
                    "slug": field_dict.get("WU"),
                    "country": field_dict.get("FU"),
                    "sets_won": int(field_dict.get("AG")) if field_dict.get("AG") is not None and field_dict.get("AG").isdigit() else None
                },
                "away_player": {
                    "name": field_dict.get("AF"),
                    "short_name": field_dict.get("WN"),
                    "id": field_dict.get("PY"),
                    "slug": field_dict.get("WV"),
                    "country": field_dict.get("FV"),
                    "sets_won": int(field_dict.get("AH")) if field_dict.get("AH") is not None and field_dict.get("AH").isdigit() else None
                },
                "winner": int(field_dict.get("AS")) if field_dict.get("AS") in ["1", "2"] else (int(field_dict.get("AZ")) if field_dict.get("AZ") in ["1", "2"] else None),
                "set_scores": set_scores,
                "tournament": current_tournament
            }
            matches.append(match_data)
            
    return matches

def main():
    feed_text = get_live_flashscore_feed()
    if not feed_text:
        print("Veri alınamadı, çıkılıyor.")
        return
        
    matches = parse_flashscore_feed(feed_text)
    
    output_path = data_dir / "today_matches.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=4)
        
    print(f"[OK] {len(matches)} maç başarıyla '{output_path}' dosyasına kaydedildi!")

if __name__ == "__main__":
    main()
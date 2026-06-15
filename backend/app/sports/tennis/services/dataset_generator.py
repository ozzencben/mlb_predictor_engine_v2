import sys
import json
from pathlib import Path

# Add root folder to sys.path to resolve 'app' imports correctly
base_dir = Path(__file__).parent.parent
project_root = Path(__file__).parent.parent.parent.parent.parent.resolve()
sys.path.append(str(project_root))

from app.sports.tennis.services.feature_builder import (
    is_player_match,
    load_player_matches,
    calculate_surface_win_rate,
    calculate_momentum_score,
    calculate_fatigue_score,
    get_player_rank,
    calculate_dominance_score,
    calculate_h2h_score,
    calculate_game_dominance,
    calculate_rest_days,
    calculate_elo_expectation,
    update_elo_rating,
    get_match_k_factor
)

data_dir = base_dir / "data"

def load_all_ranks():
    """ATP ve WTA sıralamalarındaki tüm oyuncuların ID ve İsimlerini çeker."""
    players = []
    seen_pis = set()
    
    # Rakip (Opponent) bulmak için hızlı bir İsim -> ID sözlüğü oluşturuyoruz
    name_to_id_map = {}

    atp_path = data_dir / "atp_ranks.json"
    wta_path = data_dir / "wta_ranks.json"

    for path in [atp_path, wta_path]:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for p_id, p_info in data.items():
                    pi = p_info.get("PI")
                    pn = p_info.get("PN")
                    if pi and pi not in seen_pis:
                        seen_pis.add(pi)
                        players.append(p_info)
                        if pn:
                            # Rakip ismini ararken sorun yaşamamak için küçük harfe çeviriyoruz
                            name_to_id_map[pn.lower()] = p_id

    return players, name_to_id_map

def get_player_history_at_date(player_matches, target_date_str):
    """
    Hedef maçın tarihinden DAHA ESKİ olan tüm maçları filtreler.
    Rakibin geçmiş formunu hesaplarken zaman makinesinde geriye gitmek için şarttır.
    """
    history = []
    # Tarihler YYYY-MM-DD formatında olduğu için direkt string karşılaştırması yapabiliriz
    for m in player_matches:
        if m.get("date") and m["date"] < target_date_str:
            history.append(m)
    return history

def build_feature_matrix():
    players, name_to_id_map = load_all_ranks()
    total_players = len(players)

    # --- ELO PRE-PROCESSING STAGE ---
    print("=== ELO ÖN İŞLEME AŞAMASI BAŞLADI ===")
    all_raw_matches = []
    seen_matches = set()
    
    for p in players:
        p_id = p.get("ID")
        p_name = p.get("PN")
        if not p_id or not p_name:
            continue
        p_matches = load_player_matches(p_id)
        for m in p_matches:
            m_id = m.get("match_id")
            date = m.get("date")
            if not date:
                continue
            if m_id:
                dedup_key = m_id
            else:
                dedup_key = (date, m.get("home_player", "").lower().strip(), m.get("away_player", "").lower().strip())
                
            if dedup_key in seen_matches:
                continue
            seen_matches.add(dedup_key)
            
            home_name = m.get("home_player", "")
            away_name = m.get("away_player", "")
            
            home_id = name_to_id_map.get(home_name.lower())
            away_id = name_to_id_map.get(away_name.lower())
            
            is_home = is_player_match(home_name, p_name)
            is_away = is_player_match(away_name, p_name)
            
            if is_home and not home_id:
                home_id = p_id
            if is_away and not away_id:
                away_id = p_id
                
            home_key = home_id if home_id else home_name.lower().strip()
            away_key = away_id if away_id else away_name.lower().strip()
            
            all_raw_matches.append({
                "match_id": m_id,
                "date": date,
                "tournament": m.get("tournament", ""),
                "ground": m.get("ground", "Hard"),
                "winner": m.get("winner", ""),
                "home_player": home_name,
                "away_player": away_name,
                "home_key": home_key,
                "away_key": away_key
            })
            
    all_raw_matches.sort(key=lambda x: x["date"])
    print(f"Tekil maç sayısı: {len(all_raw_matches)}. Kronolojik Elo simülasyonu çalıştırılıyor...")
    
    elo_dict = {}
    
    def get_player_elo(p_key, surface):
        if p_key not in elo_dict:
            elo_dict[p_key] = {"Hard": 1500, "Clay": 1500, "Grass": 1500}
        return elo_dict[p_key].get(surface, 1500)
        
    def get_elo_surface(ground):
        if ground == "Indoors" or ground == "Unknown":
            return "Hard"
        return ground
        
    pre_match_elo_history = {}
    
    for m in all_raw_matches:
        m_id = m["match_id"]
        date = m["date"]
        surface = get_elo_surface(m["ground"])
        home_key = m["home_key"]
        away_key = m["away_key"]
        winner = m["winner"]
        tournament = m["tournament"]
        
        home_elo = get_player_elo(home_key, surface)
        away_elo = get_player_elo(away_key, surface)
        
        match_key = m_id if m_id else (date, m["home_player"].lower().strip(), m["away_player"].lower().strip())
        pre_match_elo_history[match_key] = {
            "home_elo": home_elo,
            "away_elo": away_elo
        }
        
        if winner in ["home", "away"]:
            K = get_match_k_factor(tournament)
            if winner == "home":
                new_home = update_elo_rating(home_elo, away_elo, did_win=True, K=K)
                new_away = update_elo_rating(away_elo, home_elo, did_win=False, K=K)
            else:
                new_home = update_elo_rating(home_elo, away_elo, did_win=False, K=K)
                new_away = update_elo_rating(away_elo, home_elo, did_win=True, K=K)
                
            elo_dict[home_key][surface] = new_home
            elo_dict[away_key][surface] = new_away
            
    # Save final Elo ratings to disk
    elo_output_path = data_dir / "player_elo.json"
    with open(elo_output_path, "w", encoding="utf-8") as f:
        json.dump(elo_dict, f, ensure_ascii=False, indent=4)
    print(f"=== ELO ÖN İŞLEME TAMAMLANDI, {elo_output_path.name} kaydedildi ===\n")
    
    # --- END OF ELO PRE-PROCESSING ---

    print(f"=== DEV MATRİS İNŞASI BAŞLADI ===")
    print(f"Toplam {total_players} oyuncu analiz ediliyor...\n")

    feature_rows = []

    for idx, player in enumerate(players, 1):
        p_id = player.get("ID")
        p_name = player.get("PN")

        if not p_id or not p_name:
            continue

        player_matches = load_player_matches(p_id)

        # Filtre 1: Eğer oyuncunun genel maç sayısı 15'ten azsa, yapay zekaya sormaya değmez (Gürültü).
        if len(player_matches) < 15:
            continue

        p1_rank = get_player_rank(p_name)

        # Hedef Maç Sayısını 3'ten 15'e çıkarıyoruz! (Devasa Veri Artışı)
        for i in range(0, 15):
            if i >= len(player_matches):
                break

            target_match = player_matches[i]
            target_date = target_match.get("date")
            
            if not target_date: # Tarihi olmayan bozuk maçı atla
                continue

            history_pool = player_matches[i+1:]

            # Filtre 2: Hedef maçı soruyoruz ama arkasında en az 10 maçlık bir geçmiş kalsın ki form hesabı tutarlı olsun.
            if len(history_pool) < 10:
                continue

            current_ground = target_match["ground"]
            if current_ground == "Unknown":
                continue

            # 1. BİZİM OYUNCUNUN (P1) ÖZELLİKLERİ
            p1_ground_ratio, _ = calculate_surface_win_rate(history_pool, current_ground, p_name) 
            p1_momentum = calculate_momentum_score(history_pool, p_name)
            p1_fatigue = calculate_fatigue_score(history_pool, target_matches=3)

            is_home = is_player_match(target_match["home_player"], p_name)
            is_away = is_player_match(target_match["away_player"], p_name)
            
            if not is_home and not is_away:
                continue

            # 2. RAKİBİN (P2) KİMLİĞİNİ VE GEÇMİŞİNİ BULMA
            opponent_name = target_match["away_player"] if is_home else target_match["home_player"]
            p2_id = name_to_id_map.get(opponent_name.lower())
            
            p2_ground_ratio = 0.5  # Varsayılan
            p2_momentum = 0.5      # Varsayılan
            p2_fatigue = 5         # Varsayılan
            p2_dominance = 0.5     # Varsayılan
            p2_game_dominance = 0.5 # Varsayılan
            p2_rest_days = 7        # Varsayılan
            
            if p2_id:
                p2_matches = load_player_matches(p2_id)
                # Rakibin SADECE O GÜNKÜ MAÇTAN ÖNCEKİ maçlarını bul!
                p2_history_pool = get_player_history_at_date(p2_matches, target_date)
                
                # Rakibin de arkasında tutarlı bir geçmişi varsa hesapla
                if len(p2_history_pool) >= 5:
                    p2_ground_ratio, _ = calculate_surface_win_rate(p2_history_pool, current_ground, opponent_name)
                    p2_momentum = calculate_momentum_score(p2_history_pool, opponent_name)
                    p2_fatigue = calculate_fatigue_score(p2_history_pool, target_matches=3)
                    p2_dominance = calculate_dominance_score(p2_history_pool, opponent_name)
                    p2_game_dominance = calculate_game_dominance(p2_history_pool, opponent_name)
                    p2_rest_days = calculate_rest_days(target_date, p2_history_pool)

            # 3. MATEMATİKSEL FARKLARI HESAPLAMA (Yapay Zekanın Öğreneceği Asıl Şeyler!)
            p2_rank = get_player_rank(opponent_name)
            rank_diff = p1_rank - p2_rank
            momentum_diff = p1_momentum - p2_momentum
            ground_diff = p1_ground_ratio - p2_ground_ratio
            
            # P1 Dominance & H2H
            p1_dominance = calculate_dominance_score(history_pool, p_name)
            dominance_diff = p1_dominance - p2_dominance
            
            h2h_score = calculate_h2h_score(history_pool, p_name, opponent_name)

            p1_game_dominance = calculate_game_dominance(history_pool, p_name)
            game_dominance_diff = p1_game_dominance - p2_game_dominance

            p1_rest_days = calculate_rest_days(target_date, history_pool)
            rest_days_diff = p1_rest_days - p2_rest_days

            # Elo farkını bulalım
            p1_key = p_id
            opponent_key = p2_id if p2_id else opponent_name.lower().strip()
            
            target_match_id = target_match.get("match_id")
            target_match_key = target_match_id if target_match_id else (target_date, target_match.get("home_player", "").lower().strip(), target_match.get("away_player", "").lower().strip())
            
            pre_elo = pre_match_elo_history.get(target_match_key)
            if pre_elo:
                is_p1_home = is_player_match(target_match["home_player"], p_name)
                if is_p1_home:
                    p1_elo = pre_elo["home_elo"]
                    p2_elo = pre_elo["away_elo"]
                else:
                    p1_elo = pre_elo["away_elo"]
                    p2_elo = pre_elo["home_elo"]
            else:
                p1_elo = 1500
                p2_elo = 1500
                
            surface_elo_diff = p1_elo - p2_elo

            # Dinamik Grass Ağırlıklandırması (Çim Kort Dinamikleri)
            if current_ground == "Grass":
                momentum_diff = momentum_diff * 1.20
                surface_elo_diff = surface_elo_diff * 0.90

            # Sonuç
            was_winner = 0
            if target_match["winner"] == "home" and is_home:
                was_winner = 1
            elif target_match["winner"] == "away" and is_away:
                was_winner = 1
 
            row = {
                "player_id": p_id,
                "player_name": p_name,
                "feature_surface_rate": p1_ground_ratio,    # P1'in zemin sevgisi
                "feature_momentum_diff": momentum_diff,     # Form üstünlüğü
                "feature_ground_diff": ground_diff,         # Zemine yatkınlık farkı
                "feature_fatigue": p1_fatigue,              # Yorgunluk
                "feature_rank_diff": rank_diff,             # Klasman farkı
                "feature_dominance_diff": dominance_diff,   # Set dominantlığı farkı
                "feature_h2h_score": h2h_score,             # İkili rekabet üstünlüğü
                "feature_game_dominance_diff": game_dominance_diff, # Oyun dominantlığı farkı
                "feature_rest_days_diff": rest_days_diff,   # Dinlenme günü farkı
                "feature_surface_elo_diff": surface_elo_diff, # Elo farkı (Aşama 3)
                "target_winner": was_winner
            }

            feature_rows.append(row)

    print(f"\nMatris başarıyla inşa edildi! Toplam Satır Sayısı: {len(feature_rows)}")
    return feature_rows

if __name__ == "__main__":
    dataset = build_feature_matrix()

    if dataset:
        output_path = data_dir / "dataset.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, ensure_ascii=False, indent=4)

        print(f"-> Başarı: {output_path.name} dosyası kaydedildi!")
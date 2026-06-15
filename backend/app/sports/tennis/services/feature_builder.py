import json
from pathlib import Path
from datetime import datetime

base_dir = Path(__file__).parent.parent
raw_data_dir = base_dir / "data" / "raw" / "player_matches"

_pi_to_id_cache = None

def _load_pi_to_id_cache():
    global _pi_to_id_cache
    if _pi_to_id_cache is not None:
        return _pi_to_id_cache
    
    _pi_to_id_cache = {}
    atp_ranks_dir = raw_data_dir.parent.parent / "atp_ranks.json"
    wta_ranks_dir = raw_data_dir.parent.parent / "wta_ranks.json"
    for path in [atp_ranks_dir, wta_ranks_dir]:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for r_id, p_info in data.items():
                        pi = p_info.get("PI")
                        if pi:
                            _pi_to_id_cache[pi] = r_id
            except Exception:
                pass
    return _pi_to_id_cache

_player_matches_cache = {}

def load_player_matches(player_id):
    """Belirtilen oyuncunun ID'sine ait olan JSON dosyasını okur ve maç listesini döner."""
    if player_id in _player_matches_cache:
        return _player_matches_cache[player_id]
        
    file_path = raw_data_dir / f"{player_id}.json"
    
    if not file_path.exists():
        cache = _load_pi_to_id_cache()
        resolved_id = cache.get(player_id)
        if resolved_id:
            file_path = raw_data_dir / f"{resolved_id}.json"
            
    if not file_path.exists():
        _player_matches_cache[player_id] = []
        return []
    
    with open(file_path, "r", encoding="utf-8") as f:
        matches = json.load(f)

    # Aynı maçların mükerrer (duplicate) olarak eklenmesini engellemek için match_id ile tekilleştirme yapıyoruz.
    seen_ids = set()
    unique_matches = []
    for m in matches:
        m_id = m.get("match_id")
        if m_id:
            if m_id not in seen_ids:
                seen_ids.add(m_id)
                unique_matches.append(m)
        else:
            unique_matches.append(m)

    _player_matches_cache[player_id] = unique_matches
    return unique_matches

_player_match_cache = {}

def is_player_match(match_player_name, player_name):
    """
    Maç verisindeki oyuncu ismi (ör. 'Cerundolo J. M.', 'De Minaur A.') ile 
    hedef oyuncunun ismini (ör. 'Cerundolo Juan Manuel', 'De Minaur Alex') eşleştirir.
    Böylece kardeş oyuncuları (ör. Cerundolo brothers) ve çift soyisimli oyuncuları doğru eşleştirebiliriz.
    """
    key = (match_player_name, player_name)
    if key in _player_match_cache:
        return _player_match_cache[key]
        
    match_player_name_clean = match_player_name.lower().strip()
    player_name_clean = player_name.lower().strip()
    
    tokens = match_player_name_clean.split()
    surname_parts = []
    initials = []
    for t in tokens:
        if '.' in t or len(t) == 1:
            initials.append(t.replace('.', ''))
        else:
            surname_parts.append(t)
            
    match_surname = " ".join(surname_parts)
    
    if not player_name_clean.startswith(match_surname):
        _player_match_cache[key] = False
        return False
        
    remaining = player_name_clean[len(match_surname):].strip()
    remaining_words = remaining.split()
    
    if initials and remaining_words:
        first_init = initials[0]
        match_found = False
        
        for rw in remaining_words:
            clean_rw = rw.replace('-', '')
            clean_init = first_init.replace('-', '')
            if clean_rw.startswith(clean_init) or clean_init.startswith(clean_rw[0]):
                match_found = True
                break
        if not match_found:
            _player_match_cache[key] = False
            return False
            
    _player_match_cache[key] = True
    return True

def calculate_surface_win_rate(matches, target_ground, player_name):
    """Oyuncunun belli bir zemindeki toplam maç sayısını ve galibiyet oranını hesaplar."""
    total_surface_matches = 0
    surface_wins = 0

    for m in matches:
        if m["ground"] != target_ground:
            continue
        
        is_home = is_player_match(m["home_player"], player_name)
        is_away = is_player_match(m["away_player"], player_name)

        # Eğer oyuncu bu maçta oynamadıysa geçiyoruz (güvenlik kontrolü)
        if not is_home and not is_away:
            continue

        total_surface_matches += 1

        if m["winner"] == "home" and is_home:
            surface_wins += 1
        elif m["winner"] == "away" and is_away:
            surface_wins += 1

    if total_surface_matches == 0:
        return 0.0, 0

    win_rate = surface_wins / total_surface_matches
    return win_rate, total_surface_matches

def calculate_momentum_score(matches, player_name):
    """
    Oyuncunun son maçlardaki galibiyet durumuna göre eksponansiyel form skoru hesaplar.
    En yeni maç en yüksek ağırlığı alır.
    """

    if not matches:
        return 0.0

    decay_factor = 0.9

    total_weight = 0.0
    weighted_score = 0.0

    for idx, m in enumerate(matches):
        is_home = is_player_match(m["home_player"], player_name)
        is_away = is_player_match(m["away_player"], player_name)

        # Güvenlik Kontrolü: Eğer oyuncu iki tarafta da bulunamadıysa (eşleşme hatası vb.) bu maçı es geçiyoruz.
        if not is_home and not is_away:
            continue

        did_win = 0
        if m["winner"] == "home" and is_home:
            did_win += 1
        elif m["winner"] == "away" and is_away:
            did_win += 1

        weight = (decay_factor) ** idx
        weighted_score += did_win * weight
        total_weight += weight
    
    # Division-by-zero hatasını önlemek için koruma
    if total_weight == 0.0:
        return 0.0

    return weighted_score / total_weight

def calculate_fatigue_score(matches, target_matches = 3):
    """Oyuncunun son N maçında oynadığı toplam set sayısını hesaplar. Yuksek set sayısı, yüksek yorgunluk demektir."""

    if not matches:
        return 0

    recent_matches = matches[:target_matches]
    total_set = 0

    for m in recent_matches:
        a_score = m.get("away_score", 0)
        h_score = m.get("home_score", 0)

        if isinstance(h_score, int) and isinstance(a_score, int):
            total_set += (h_score + a_score)

    return total_set

_ranks_cache = None

def _load_ranks_cache():
    global _ranks_cache
    if _ranks_cache is not None:
        return _ranks_cache
    
    _ranks_cache = []
    atp_ranks_dir = base_dir / "data" / "atp_ranks.json"
    wta_ranks_dir = base_dir / "data" / "wta_ranks.json"
    for rank_dir in [atp_ranks_dir, wta_ranks_dir]:
        if rank_dir.exists():
            try:
                with open(rank_dir, "r", encoding="utf-8") as f:
                    _ranks_cache.append(json.load(f))
            except Exception:
                pass
    return _ranks_cache

_ranks_name_to_rank = None

def _get_name_variations(pn):
    pn = pn.lower().strip()
    variations = [pn]
    words = pn.split()
    if len(words) >= 2:
        surname = " ".join(words[:-1])
        first_name = words[-1]
        first_init = first_name[0]
        variations.append(f"{surname} {first_init}.")
        
        surname2 = words[0]
        first_names2 = words[1:]
        init_str2 = ". ".join([w[0] for w in first_names2]) + "."
        variations.append(f"{surname2} {init_str2}")
        variations.append(f"{surname2} {first_names2[0][0]}.")
    return [v.replace("  ", " ").strip() for v in variations]

def _load_ranks_name_to_rank():
    global _ranks_name_to_rank
    if _ranks_name_to_rank is not None:
        return _ranks_name_to_rank
    
    _ranks_name_to_rank = {}
    rank_datasets = _load_ranks_cache()
    for rank_data in rank_datasets:
        for p_id, p_info in rank_data.items():
            pn = p_info.get("PN", "")
            rank = int(p_info.get("RA", 100))
            for var in _get_name_variations(pn):
                _ranks_name_to_rank[var] = rank
    return _ranks_name_to_rank

def get_player_rank(player_name):
    """
    Oyuncunun adına bakarak atp_ranks veya wta_ranks dosyalarından 
    dünya sıralama numarasını (sıra endeksini) bulur.
    Bulamazsa varsayılan olarak büyük bir sayı (100) döner.
    """
    player_name_clean = player_name.lower().strip().replace("  ", " ")
    cache = _load_ranks_name_to_rank()
    if player_name_clean in cache:
        return cache[player_name_clean]

    rank_datasets = _load_ranks_cache()

    for rank_data in rank_datasets:
        for p_id, p_info in rank_data.items():
            pn = p_info.get("PN", "")
            if is_player_match(player_name, pn) or is_player_match(pn, player_name):
                rank = int(p_info.get("RA", 100))
                cache[player_name_clean] = rank
                return rank
    
    cache[player_name_clean] = 100
    return 100
    
def calculate_dominance_score(history_pool, player_name):
    """
    Oyuncunun geçmiş maçlarında aldığı 'Kazanılan Toplam Set / Oynanan Toplam Set' oranını hesaplar.
    """
    if not history_pool:
        return 0.5
        
    total_sets_won = 0
    total_sets_played = 0
    
    for m in history_pool:
        is_home = is_player_match(m["home_player"], player_name)
        is_away = is_player_match(m["away_player"], player_name)
        
        if not is_home and not is_away:
            continue
            
        home_sets = m.get("home_score", 0)
        away_sets = m.get("away_score", 0)
        
        if not isinstance(home_sets, int) or not isinstance(away_sets, int):
            try:
                home_sets = int(home_sets)
                away_sets = int(away_sets)
            except (ValueError, TypeError):
                continue
                
        sets_played = home_sets + away_sets
        if sets_played == 0:
            continue
            
        total_sets_played += sets_played
        if is_home:
            total_sets_won += home_sets
        else:
            total_sets_won += away_sets
            
    if total_sets_played == 0:
        return 0.5
        
    return total_sets_won / total_sets_played

def calculate_h2h_score(p1_history_pool, p1_name, p2_name):
    """
    P1'in geçmiş havuzunda P2'ye karşı olan maçlarındaki kazanma oranını döner.
    Hiç karşılaşmamışlarsa 0.5 döner.
    """
    if not p1_history_pool:
        return 0.5
        
    h2h_matches_count = 0
    p1_h2h_wins = 0
    
    for m in p1_history_pool:
        is_p1_home = is_player_match(m["home_player"], p1_name)
        is_p1_away = is_player_match(m["away_player"], p1_name)
        
        if not is_p1_home and not is_p1_away:
            continue
            
        opponent = m["away_player"] if is_p1_home else m["home_player"]
        if not is_player_match(opponent, p2_name):
            continue
            
        h2h_matches_count += 1
        
        if m["winner"] == "home" and is_p1_home:
            p1_h2h_wins += 1
        elif m["winner"] == "away" and is_p1_away:
            p1_h2h_wins += 1
            
    if h2h_matches_count == 0:
        return 0.5
        
    return p1_h2h_wins / h2h_matches_count

def calculate_game_dominance(history_pool, player_name):
    """
    Oyuncunun geçmiş maçlarında aldığı 'Kazanılan Toplam Oyun / Oynanan Toplam Oyun' oranını hesaplar.
    Eğer detaylı oyun skorları yoksa, set başına kazanan için 6, kaybeden için 4 oyun varsayılır.
    """
    if not history_pool:
        return 0.5
        
    total_games_won = 0
    total_games_played = 0
    
    for m in history_pool:
        is_home = is_player_match(m["home_player"], player_name)
        is_away = is_player_match(m["away_player"], player_name)
        
        if not is_home and not is_away:
            continue
            
        home_sets = m.get("home_score", 0)
        away_sets = m.get("away_score", 0)
        
        if not isinstance(home_sets, int) or not isinstance(away_sets, int):
            try:
                home_sets = int(home_sets)
                away_sets = int(away_sets)
            except (ValueError, TypeError):
                continue
                
        sets_played = home_sets + away_sets
        if sets_played == 0:
            continue
            
        if is_home:
            sets_won = home_sets
            sets_lost = away_sets
        else:
            sets_won = away_sets
            sets_lost = home_sets
            
        games_won = sets_won * 6 + sets_lost * 4
        games_lost = sets_won * 4 + sets_lost * 6
        games_played = games_won + games_lost
        
        total_games_won += games_won
        total_games_played += games_played
        
    if total_games_played == 0:
        return 0.5
        
    return total_games_won / total_games_played

def calculate_rest_days(target_date, history_pool):
    """
    Hedef maç tarihi ile bir önceki maç tarihi arasındaki gün farkını hesaplar.
    """
    if not history_pool or not target_date:
        return 7
        
    last_match = history_pool[0]
    last_date_str = last_match.get("date")
    
    if not last_date_str:
        return 7
        
    try:
        t_date = datetime.strptime(target_date, "%Y-%m-%d")
        l_date = datetime.strptime(last_date_str, "%Y-%m-%d")
        diff_days = (t_date - l_date).days
        return max(0, diff_days)
    except Exception:
        return 7

def calculate_elo_expectation(player_elo, opponent_elo):
    """
    Oyuncunun rakibe karşı kazanma olasılığı beklentisini hesaplar.
    """
    return 1.0 / (1.0 + 10.0 ** ((opponent_elo - player_elo) / 400.0))

def update_elo_rating(player_elo, opponent_elo, did_win, K=32):
    """
    Maç sonucuna göre yeni Elo puanını hesaplar.
    """
    expectation = calculate_elo_expectation(player_elo, opponent_elo)
    score = 1.0 if did_win else 0.0
    new_elo = player_elo + K * (score - expectation)
    return new_elo

def get_match_k_factor(tournament_name):
    """
    Turnuva tipine göre K-Faktörü değerini belirler.
    Grand Slam turnuvaları için 48, diğerleri için 32 döner.
    """
    if not tournament_name:
        return 32
    t_lower = tournament_name.lower()
    gs_keywords = ["french open", "roland garros", "wimbledon", "us open", "australian open"]
    if any(keyword in t_lower for keyword in gs_keywords):
        return 48
    return 32

if __name__ == "__main__":
    test_id = "6HdC3z4H"
    test_name = "Sinner Jannik"

    print(f"--- {test_name} için test analizi başlıyor ---")

    sinner_matches = load_player_matches(test_id)
    print(f"Toplam yüklenen benzersiz maç sayısı: {len(sinner_matches)}\n")

    grounds = ["Hard", "Clay", "Grass"]

    for g in grounds:
        ratio, total_match = calculate_surface_win_rate(sinner_matches, g, test_name)
        print(f"{g} Kort başarı oranı: %{ratio * 100:.2f} (Toplam maç sayısı: {total_match})")

    momentum = calculate_momentum_score(sinner_matches, test_name)
    print(f"\n-> Zaman Ağırlıklı Güncel Form Skoru (Momentum): {momentum:.2f} (0 ile 1 arası)")

    fatigue = calculate_fatigue_score(sinner_matches, target_matches=3)
    print(f"-> Son 3 Maçtaki Fiziksel Yorgunluk (Toplam Set): {fatigue} set")

    rank = get_player_rank(test_name)
    print(f"-> Dünya Sıralaması (Rank): {rank}\n")
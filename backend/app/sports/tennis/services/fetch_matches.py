import re
import json
import time
import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# --- DOSYA VE KLASÖR AYARLARI ---
base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data" / "raw" / "player_matches"
data_dir.mkdir(parents=True, exist_ok=True)
ranks_dir = base_dir / "data"

# --- 1. GLOBAL ZEMİN EŞLEŞTİRME SÖZLÜĞÜ ---
ZEMIN_MAP = {
    "t": "Clay",
    "g": "Grass",
    "h": "Hard",
    "i": "Indoors",
    "p": "Outdoor"
}

# --- 2. ZEMİN DOĞRULAMA ---
def sanitize_ground(tournament_name, current_ground):
    """Turnuva adındaki anahtar kelimelere göre zemini doğrular."""
    name_lower = tournament_name.lower()
    if "grass" in name_lower:
        return "Grass"
    elif "clay" in name_lower:
        return "Clay"
    elif "hard" in name_lower:
        return "Hard"
    elif "indoor" in name_lower or "indoors" in name_lower:
        return "Indoors"
    return current_ground

# --- 3. VERİ BLOĞUNU ANALİZ ET ---
def parse_match_block(raw_data):
    """
    Flashscore'un ham veri bloğunu ('ZA÷...~AA÷...' formatında) okuyarak
    maç listesi oluşturur. Tarih bilgisi (AD alanı - Unix timestamp) dahil.
    """
    match_list = []
    current_tournament = "Unknown Tournament"
    current_ground = "Unknown"

    parts = raw_data.split("~")
    for p in parts:
        if p.startswith("ZA\xf7"):  # ZA÷ = Turnuva başlığı
            pieces = p.split("\xac")  # ¬ ayırıcısı
            current_tournament = pieces[0].replace("ZA\xf7", "")
            for piece in pieces:
                if piece.startswith("ZD\xf7"):  # ZD÷ = Zemin kodu
                    zemin_kodu = piece.replace("ZD\xf7", "")
                    current_ground = ZEMIN_MAP.get(zemin_kodu, f"Unknown ({zemin_kodu})")

        elif p.startswith("AA\xf7"):  # AA÷ = Maç kaydı
            real_ground = sanitize_ground(current_tournament, current_ground)

            match_dict = {
                "tournament": current_tournament,
                "ground": real_ground,
                "match_id": "",
                "date": "",       # <-- YENİ: Tarih alanı
                "home_player": "",
                "away_player": "",
                "home_score": 0,
                "away_score": 0,
                "winner": ""
            }

            set_raw = {}
            match_pieces = p.split("\xac")  # ¬ ayırıcısı
            for mp in match_pieces:
                if mp.startswith("AA\xf7"):
                    match_dict["match_id"] = mp.replace("AA\xf7", "")
                elif mp.startswith("AD\xf7"):  # AD÷ = Unix timestamp (maç tarihi)
                    ts_str = mp.replace("AD\xf7", "")
                    try:
                        ts = int(ts_str)
                        match_dict["date"] = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                    except (ValueError, OSError):
                        match_dict["date"] = ""
                elif mp.startswith("AE\xf7"):  # AE÷ = Ev sahibi oyuncu
                    match_dict["home_player"] = mp.replace("AE\xf7", "")
                elif mp.startswith("AF\xf7"):  # AF÷ = Deplasman oyuncu
                    match_dict["away_player"] = mp.replace("AF\xf7", "")
                elif mp.startswith("AG\xf7"):  # AG÷ = Ev sahibi skor
                    skor = mp.replace("AG\xf7", "")
                    match_dict["home_score"] = int(skor) if skor.isdigit() else skor
                elif mp.startswith("AH\xf7"):  # AH÷ = Deplasman skor
                    skor = mp.replace("AH\xf7", "")
                    match_dict["away_score"] = int(skor) if skor.isdigit() else skor
                elif mp.startswith("AS\xf7"):  # AS÷ = Kazanan (1=ev, 2=dep)
                    outcome = mp.replace("AS\xf7", "")
                    if outcome == "1": match_dict["winner"] = "home"
                    elif outcome == "2": match_dict["winner"] = "away"

                # Set skorlarını yakala (BA-BJ)
                for key in ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BI", "BJ"]:
                    if mp.startswith(f"{key}\xf7"):
                        set_raw[key] = mp.replace(f"{key}\xf7", "")

            # Set skorlarını listeye ekle
            set_scores = []
            for h_key, a_key in [("BA", "BB"), ("BC", "BD"), ("BE", "BF"), ("BG", "BH"), ("BI", "BJ")]:
                if h_key in set_raw or a_key in set_raw:
                    set_scores.append({
                        "home": set_raw.get(h_key, ""),
                        "away": set_raw.get(a_key, "")
                    })
            match_dict["set_scores"] = set_scores

            if match_dict["match_id"]:
                match_list.append(match_dict)

    return match_list


# --- 4. JS-BASED DOM EXTRACTOR QUERY ---
FULL_EXTRACTOR_JS = r"""
() => {
    const results = [];
    const matchEls = document.querySelectorAll('[id^="g_"]');
    
    matchEls.forEach(el => {
        const matchId = el.id.replace(/^g_\d+_/, '');
        
        // Find tournament header (headerLeague__wrapper)
        let currentTournament = 'Unknown';
        let currentGround = 'Unknown';
        let sibling = el.previousElementSibling;
        while (sibling) {
            const sibCls = sibling.className || '';
            if (sibCls.indexOf('headerLeague__wrapper') >= 0) {
                const titleEl = sibling.querySelector('.headerLeague__title');
                currentTournament = titleEl ? (titleEl.getAttribute('title') || titleEl.innerText).trim() : sibling.innerText.trim();
                
                // Determine ground surface
                const titleLower = currentTournament.toLowerCase();
                if (titleLower.indexOf('clay') >= 0) currentGround = 'Clay';
                else if (titleLower.indexOf('grass') >= 0) currentGround = 'Grass';
                else if (titleLower.indexOf('hard') >= 0) currentGround = 'Hard';
                else if (titleLower.indexOf('indoor') >= 0) currentGround = 'Indoors';
                else currentGround = 'Unknown';
                break;
            }
            sibling = sibling.previousElementSibling;
        }
        
        const homePlayerEl = el.querySelector('.event__homeParticipant, [class*="homeParticipant"]');
        const awayPlayerEl = el.querySelector('.event__awayParticipant, [class*="awayParticipant"]');
        const homePlayer = homePlayerEl ? homePlayerEl.innerText.trim() : '';
        const awayPlayer = awayPlayerEl ? awayPlayerEl.innerText.trim() : '';
        
        const homeScoreEl = el.querySelector('.event__score--home');
        const awayScoreEl = el.querySelector('.event__score--away');
        const homeScore = homeScoreEl ? (parseInt(homeScoreEl.innerText.trim()) || 0) : 0;
        const awayScore = awayScoreEl ? (parseInt(awayScoreEl.innerText.trim()) || 0) : 0;
        
        const wlBtn = el.querySelector('button');
        const wlText = wlBtn ? wlBtn.innerText.trim() : '';
        let winner = '';
        if (homeScore > awayScore) {
            winner = 'home';
        } else if (awayScore > homeScore) {
            winner = 'away';
        } else {
            // Eğer skorlar 0-0 ise (örn: maç başlamadan iptal edildiyse) boş bırak
            winner = 'unknown'; 
        }
        
        const timeEl = el.querySelector('.event__time, [class*="event__time"]');
        const dateText = timeEl ? timeEl.innerText.trim() : '';
        
        // Extract set game scores
        const homePartEls = el.querySelectorAll('.event__part--home, [class*="event__part--home"]');
        const awayPartEls = el.querySelectorAll('.event__part--away, [class*="event__part--away"]');
        const setScores = [];
        
        const numSets = Math.min(homePartEls.length, awayPartEls.length);
        for (let i = 0; i < numSets; i++) {
            // Tiebreak puanlarını (sup/extraScore) temizlemek için klonluyoruz
            const hClone = homePartEls[i].cloneNode(true);
            hClone.querySelectorAll('sup, [class*="extraScore"]').forEach(s => s.remove());
            const hText = hClone.innerText.trim();
            
            const aClone = awayPartEls[i].cloneNode(true);
            aClone.querySelectorAll('sup, [class*="extraScore"]').forEach(s => s.remove());
            const aText = aClone.innerText.trim();
            
            if (hText || aText) {
                setScores.push({
                    home: hText,
                    away: aText
                });
            }
        }
        
        if (homePlayer) {
            results.push({
                match_id: matchId,
                tournament: currentTournament,
                ground: currentGround,
                date_text: dateText,
                home_player: homePlayer,
                away_player: awayPlayer,
                home_score: homeScore,
                away_score: awayScore,
                winner: winner,
                set_scores: setScores
            });
        }
    });
    
    return results;
}
"""

# --- 5. ANA MAÇ ÇEKME FONKSİYONU (PLAYWRIGHT DOM) ---
def get_player_matches(player_id, player_url, target=50):
    """
    Playwright (headless Chromium) kullanarak oyuncunun sonuç sayfasını açar,
    'Show more' butonuna basarak en az target adet maçı yükler ve DOM'dan parse edip saklar.
    """
    clean_url = player_url.strip("/").replace("oyuncu", "player")
    full_url = f"https://www.flashscore.com/{clean_url}/results/"

    matches = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Cookie/popup engellemek için timeout'u arttırıyoruz
        page.set_default_timeout(15000)

        try:
            page.goto(full_url, wait_until="networkidle", timeout=20000)
        except Exception:
            pass

        # Cookie/reklam engeli varsa kapat
        try:
            page.click("button#onetrust-accept-btn-handler", timeout=3000)
        except Exception:
            pass

        # 'Show More' butonuna basarak yeterli maçı yükle (scrolling & clicking)
        clicks = 0
        max_clicks = 8

        while clicks < max_clicks:
            # Sayfa sonuna kaydır
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1.0)

            match_count = page.evaluate("() => document.querySelectorAll('[id^=\"g_\"]').length")
            if match_count >= target:
                break

            has_button = page.evaluate("""() => {
                const b = document.querySelector('div.extraContent__button') || document.querySelector('.event__more');
                if (b && window.getComputedStyle(b).display !== 'none') {
                    b.click();
                    return true;
                }
                return false;
            }""")
            if not has_button:
                break

            time.sleep(2.0)
            clicks += 1

        # Son yüklemeleri de almak için tekrar kaydır
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1.0)

        # DOM'dan maçları çıkar
        matches = page.evaluate(FULL_EXTRACTOR_JS)
        browser.close()

    # Tarihlere yıl ekle
    current_year = datetime.datetime.now().year
    for m in matches:
        date_text = m.get("date_text", "")
        # Yıl bilgisi zaten var mı kontrol et (örn: 16.11.2025)
        m_year = re.search(r'(\d{4})', date_text)
        if m_year:
            year = int(m_year.group(1))
        else:
            year = current_year

        m_dm = re.match(r'(\d+)\.(\d+)\.', date_text)
        if m_dm:
            day = int(m_dm.group(1))
            month = int(m_dm.group(2))
            m["date"] = f"{year}-{month:02d}-{day:02d}"
        else:
            m["date"] = ""

    # Diske kaydet (ranking entry id + stabil PI slug kopyasi)
    json_file_path = data_dir / f"{player_id}.json"
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(matches[:target], f, ensure_ascii=False, indent=4)

    pi_slug = player_url.rstrip("/").split("/")[-1]
    if pi_slug and pi_slug != player_id:
        slug_file_path = data_dir / f"{pi_slug}.json"
        with open(slug_file_path, "w", encoding="utf-8") as f:
            json.dump(matches[:target], f, ensure_ascii=False, indent=4)

    return matches[:target]

# --- 6. TÜM OYUNCULAR İÇİN TOPLU ÇEKME ---
def fetch_all_matches():
    import sys

    total_new = 0
    total_skipped = 0
    total_error = 0

    for rank_file in ["atp_ranks.json", "wta_ranks.json"]:
        rank_path = ranks_dir / rank_file
        if not rank_path.exists():
            print(f"[UYARI] {rank_file} bulunamadı, atlandı.")
            continue

        with open(rank_path, "r", encoding="utf-8") as f:
            players = json.load(f)

        # Sadece fetch edilecekleri say (tahmini süre için)
        to_fetch = sum(
            1 for p_id, info in players.items()
            if info.get("PU") and not (data_dir / f"{p_id}.json").exists()
        )

        print(f"\n=== {rank_file} — {len(players)} oyuncu | {to_fetch} yeni çekilecek ===")
        if to_fetch > 0:
            est_min = to_fetch * 12 // 60
            print(f"    Tahmini süre: ~{est_min} dakika ({to_fetch} oyuncu × ~12sn)")
        print()

        count = 1
        for p_id, p_info in players.items():
            p_name = p_info.get("PN", "Bilinmeyen")
            p_url = p_info.get("PU", "")

            # Resume Rule: aynı ID'ye ait geçerli dosya varsa atla
            existing_file = data_dir / f"{p_id}.json"
            if existing_file.exists():
                try:
                    existing_data = json.loads(existing_file.read_text(encoding="utf-8"))
                    if len(existing_data) > 0 and existing_data[0].get("date"):
                        print(f"[{count}/{len(players)}] SKIP — {p_name} ({len(existing_data)} maç mevcut)")
                        total_skipped += 1
                        count += 1
                        continue
                except Exception:
                    pass

            if not p_url:
                print(f"[{count}/{len(players)}] URL eksik, atlandı: {p_name}")
                count += 1
                continue

            print(f"[{count}/{len(players)}] Çekiliyor: {p_name} ...", end=" ", flush=True)

            try:
                result = get_player_matches(p_id, p_url, target=50)
                print(f"{len(result)} maç kaydedildi.")
                total_new += 1
            except Exception as e:
                print(f"HATA: {e}")
                total_error += 1

            count += 1
            time.sleep(1.0)

    print(f"\n{'='*60}")
    print(f"İşlem Tamamlandı!")
    print(f"  Yeni çekilen : {total_new}")
    print(f"  Atlanan      : {total_skipped}")
    print(f"  Hata         : {total_error}")
    print(f"{'='*60}")

# --- 7. BUGÜNKÜ FİKSTÜR OYUNCULARI İÇİN ÇEKME (VERİMLİ MOD) ---
def fetch_todays_players():
    """
    today_matches.json'daki oyuncuların maç verilerini çeker.
    Günlük pipeline'a entegre edilmek üzere tasarlandı:
    Her gün sadece oynayan ~40 oyuncuyu çeker, zamanla tüm veri tabanı dolar.
    """
    import sys

    fixtures_path = ranks_dir / "today_matches.json"
    if not fixtures_path.exists():
        print("HATA: today_matches.json bulunamadı. Önce fetch_fexture.py çalıştırın.")
        return

    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # slug → URL eşlemesini atp/wta ranks'tan derle
    slug_to_url: dict[str, str] = {}
    for rank_file in ["atp_ranks.json", "wta_ranks.json"]:
        rank_path = ranks_dir / rank_file
        if not rank_path.exists():
            continue
        with open(rank_path, "r", encoding="utf-8") as f:
            rank_data = json.load(f)
        # p_id (ranking entry ID) → PI (slug), PU (url)
        for p_id, info in rank_data.items():
            pi = info.get("PI")
            pu = info.get("PU")
            if pi and pu:
                # slug → (ranking_entry_id, url) — ranking_entry_id ile kaydediliyor
                slug_to_url[pi] = (p_id, pu)

    # Bugünkü tüm oyuncuları topla (slug, isim)
    seen_slugs: set[str] = set()
    players_to_fetch: list[tuple[str, str, str, str]] = []  # (slug, ranking_id, name, url)

    for m in fixtures:
        for side in ("home_player", "away_player"):
            player = m.get(side, {})
            slug = player.get("id", "")
            name = player.get("name", "")
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            if slug not in slug_to_url:
                continue  # Ranks'ta bulunamadı (takım maçı vs.)

            ranking_id, url = slug_to_url[slug]

            # Zaten dosya varsa ve geçerliyse atla (rank id veya PI slug)
            existing_paths = [data_dir / f"{ranking_id}.json", data_dir / f"{slug}.json"]
            cached = False
            for existing_file in existing_paths:
                if not existing_file.exists():
                    continue
                try:
                    existing_data = json.loads(existing_file.read_text(encoding="utf-8"))
                    if len(existing_data) > 0 and existing_data[0].get("date"):
                        cached = True
                        break
                except Exception:
                    pass
            if cached:
                continue

            players_to_fetch.append((slug, ranking_id, name, url))

    if not players_to_fetch:
        print("⚡ Bugünkü tüm oyuncuların maç verisi zaten mevcut — işlem gerekmiyor.")
        return

    print(f"📥 Bugünkü fikstür: {len(players_to_fetch)} oyuncu için maç verisi çekiliyor...")
    print(f"   Tahmini süre: ~{len(players_to_fetch) * 12 // 60} dakika\n")

    for i, (slug, ranking_id, name, url) in enumerate(players_to_fetch, 1):
        print(f"[{i}/{len(players_to_fetch)}] {name} ...", end=" ", flush=True)
        try:
            result = get_player_matches(ranking_id, url, target=50)
            print(f"{len(result)} maç kaydedildi.")
        except Exception as e:
            print(f"HATA: {e}")
        time.sleep(1.0)

    print(f"\n✓ Tamamlandı! {len(players_to_fetch)} oyuncu işlendi.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Tüm ranked oyuncuları çek (saatler sürebilir)
        fetch_all_matches()
    else:
        # Varsayılan: sadece bugünkü fikstür oyuncuları (~10-15 dk)
        fetch_todays_players()
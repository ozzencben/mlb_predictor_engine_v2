import re
import time
import json
import requests
from pathlib import Path

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data"
data_dir.mkdir(parents=True, exist_ok=True)

headers = {
    "Referer": "https://www.flashscore.com/",
    "Sec-ch-ua": '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    "Sec-ch-ua-mobile": "?0",
    "Sec-ch-ua-platform": "Windows",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "X-fsign": "SW9D1eZo",
    "X-Requested-With": "XMLHttpRequest"
}

page_headers = {
    "Referer": "https://www.flashscore.com/tennis/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ATP ve WTA için Feed ID'leri
categories = [
    {"name": "ATP", "feed_id": "dSJr14Y8", "file": "atp_ranks.json"},
    {"name": "WTA", "feed_id": "hfDiar3L", "file": "wta_ranks.json"}
]

IMAGE_PATTERN = re.compile(r'heading__logo[^>]*src="(https://static\.flashscore\.com/res/image/data/[^"]+)"')

def fetch_player_image(player_url_path: str) -> str | None:
    """Oyuncu profil sayfasından görsel URL'sini çeker."""
    try:
        url = f"https://www.flashscore.com{player_url_path}"
        resp = requests.get(url, headers=page_headers, timeout=8)
        if resp.status_code == 200:
            m = IMAGE_PATTERN.search(resp.text)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


print("=== SIRALAMA LİSTELERİ GENİŞLETİLİYOR (İLK 200) ===")

# Mevcut player_images.json'u yükle (incremental güncelleme için)
images_path = data_dir / "player_images.json"
player_images: dict[str, str] = {}
if images_path.exists():
    try:
        with open(images_path, "r", encoding="utf-8") as f:
            player_images = json.load(f)
        print(f"ℹ️  Mevcut player_images.json yüklendi: {len(player_images)} kayıt")
    except Exception:
        player_images = {}

for cat in categories:
    all_players = {}

    # Sayfa 1 (1-100) ve Sayfa 2 (101-200) için döngü kuruyoruz
    for page in [1, 2]:
        request_url = f"https://2.flashscore.ninja/2/x/feed/ran_{cat['feed_id']}_{page}"
        response = requests.get(request_url, headers=headers)

        if response.status_code == 200:
            response_text = response.text
            response_parts = re.findall(r"TS÷RW¬(.*?)TE÷RW¬", response_text, re.DOTALL)

            for p in response_parts:
                values = p.split("¬")
                player_dict: dict = {}
                key = None
                value = None
                for v in values:
                    player_info = v.split("÷")
                    if len(player_info) == 2:
                        if player_info[0] == "PT":
                            key = player_info[1]
                        elif player_info[0] == "PV":
                            value = player_info[1]
                        if key is not None:
                            player_dict[key] = value

                if "ID" in player_dict:
                    all_players[player_dict["ID"]] = player_dict
        else:
            print(f"Hata: {cat['name']} Sayfa {page} çekilemedi! HTTP Kodu:", response.status_code)

    # Toplanan tüm veriyi ilgili dosyaya kaydet
    output_path = data_dir / cat["file"]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_players, f, ensure_ascii=False, indent=4)
    print(f"✓ {cat['name']} listesi güncellendi! Toplam {len(all_players)} oyuncu kaydedildi.")

# ── Görsel çekme: sadece bugünkü fikstürdeki oyuncular ────────────────────
# Bu yaklaşım hızlıdır: günde max ~40 istek, cache ile birikir.
fixtures_path = data_dir / "today_matches.json"
slug_to_url: dict[str, str] = {}

# Tüm rank dosyalarından slug -> URL eşlemesini derle
for cat in categories:
    rank_path = data_dir / cat["file"]
    if rank_path.exists():
        with open(rank_path, "r", encoding="utf-8") as f:
            rank_data = json.load(f)
        for player in rank_data.values():
            slug = player.get("PI")
            url_path = player.get("PU")
            if slug and url_path:
                slug_to_url[slug] = url_path

if fixtures_path.exists():
    with open(fixtures_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    # Bugünkü fikstürdeki oyuncu ID'leri (slug formatında)
    todays_slugs: list[tuple[str, str]] = []
    for m in fixtures:
        for side in ("home_player", "away_player"):
            player = m.get(side, {})
            slug = player.get("id")
            if slug and slug not in player_images and slug in slug_to_url:
                todays_slugs.append((slug, slug_to_url[slug]))

    if todays_slugs:
        print(f"\n📸 Bugünkü fikstür: {len(todays_slugs)} oyuncu için görsel çekiliyor...")
        fetched = 0
        for slug, url_path in todays_slugs:
            img_url = fetch_player_image(url_path)
            if img_url:
                player_images[slug] = img_url
                fetched += 1
            time.sleep(0.3)
        print(f"  ✓ {fetched}/{len(todays_slugs)} yeni görsel URL'si alındı.")
    else:
        print("\n⚡ Bugünkü tüm oyuncuların görselleri zaten cache'de.")
else:
    print("\n⚠️  today_matches.json bulunamadı — görsel çekme atlandı.")

# player_images.json kaydet
with open(images_path, "w", encoding="utf-8") as f:
    json.dump(player_images, f, ensure_ascii=False, indent=4)
print(f"✓ player_images.json güncellendi! Toplam {len(player_images)} oyuncu görseli.")
print("\nOperasyon Tamamlandı!")
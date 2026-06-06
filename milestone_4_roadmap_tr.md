# MLB Predictor Engine — Milestone 4 Yol Haritası (Güncel)

---

## ✅ YAPILDI

### Görev 1 — Hamburger / Dropdown Navigasyon Menüsü
- `DropdownNavigation.jsx` bileşeni oluşturuldu
- App.jsx'teki yatay sekmeler kaldırıldı, hamburger menü entegre edildi
- "Pitcher Projections" sekmesi menüye eklendi
- Mobil uyumlu animasyonlar tamamlandı

---

### Görev 2 — Günlük Kadro Veri Toplayıcı (Confirmed Lineups)
- `get_lineup_for_game()` → MLB StatsAPI boxscore ile 9 kişilik resmi kadro çekimi
- `fetch_last_completed_game_pk()` → Resmi kadro yoksa son maçtan fallback kadro
- `lineups_cache.json` → Tarih bazlı cache, resmi kadrolar `is_official: true`
- Tüm başlangıç vurucuların bireysel hitting istatistikleri paralel çekiliyor
- `away_lineup_hydrated / home_lineup_hydrated` + `lineup_avg` engine'e besleniyor

---

### Görev 3 — Ana Model Güçlendirmesi

**Tamamlanan:**
- ✅ xERA / xFIP pitcher expected stats → `pitcher_scraper.py` + engine
- ✅ LHP/RHP team hitting splits → `fetch_team_splits_async()`, tüm takımlar paralel
- ✅ Lineup wRC+ / wOBA harmanlaması → 9 oyuncu ortalaması, engine'e besleniyor
- ✅ `predict_matchup()` imzası güncellendi: `away_splits`, `home_splits`, `lineup_avg` parametreleri eklendi
- ✅ Bullpen SIERA → Covers.com üzerinden dinamik bullpen verilerinin (ERA, WHIP, H, SO, BB, vb.) çekilerek SIERA proxy formülü ile hesaplanması ve modele entegrasyonu (statik json yerine dinamik günlük güncelleme)
- ✅ HFA dinamik stadyum katsayısı & Ballpark Factor Düzeltmesi → Ballpark stats run_factor/park_factor eşleşme bug'ı giderildi; simetrik dinamik HFA (ev sahibi hücum artış katsayısı, misafir takım runs-allowed kısıtlama katsayısı) hem F5 hem de Full Game modellerine entegre edildi.
- ✅ Sonny Moore Power Rankings → Sonny Moore resmi web sitesinden (`sonnymoorepowerratings.com/mlb.htm`) en güncel power ranking verilerinin dinamik çekilip ayrıştırılması, lig ortalaması bazlı güvenli fallback mimarisiyle model tahminlerine dahil edilmesi.

**Henüz Yapılmadı:**
- (Tüm ana model güçlendirme görevleri tamamlandı)

---

### Görev 4 — Atıcı Props Hesaplama Motoru

**Tamamlanan:**
- ✅ `pitcher_k_model.py` → K Model.ods tersine mühendislik (Pydantic schemas + formüller)
  - Home/Away K% ağırlıklı Expected K% (Pitcher %65, Opponent %45)
  - CSW% + SwStr% lig ortalaması fark düzeltmesi (%35'er ağırlık)
  - Baseball notasyonu IP dönüşümü (5.2 → 5.667)
  - ODS dosyasındaki "volume squaring" hatası düzeltildi
- ✅ `pitcher_props_engine.py` → K için KModel, Outs için xFIP×wRC+ regresyon
- ✅ `test_pitcher_k_model.py` → 3 test sınıfı, tümü geçiyor

**Bug Düzeltmesi (v1.1 — 5 Haziran 2026):**
- ✅ `pitcher_scraper.py` → `k_pct`, `avg_ip`, `avg_bf`, `swstr_pct`, `csw_pct` artık `pitcher_stats.json`'a kaydediliyor (önceden kaydedilmiyordu)
- ✅ `calculate_pitcher_metrics()` → Pre-computed değerleri öncelikli kullanıyor; sıfır fallback sorunu giderildi
- ✅ `pitcher_stats.json` → 29 atıcı MLB StatsAPI'den backfill edildi (0 hata)
- **Sonuç:** "1.5 K / 3 IP floor" bug'ı çözüldü; gerçek projeksiyonlar: Framber Valdez 4.83 K · Ryan Weathers 7.14 K

---

### Görev 5 — Bahis Oranları Entegrasyonu & Props Tablosu UI

**Tamamlanan:**
- ✅ `odds_provider.py` → `fetch_player_props_for_games_async()` the-odds-api `pitcher_strikeouts` + `pitcher_outs` market
- ✅ `parse_pitcher_props_odds()` → Pitcher isim fuzzy match, Over/Under ayrıştırma, birincil kitap önceliği
- ✅ `prediction_runner.py` → Poisson CDF (K) + Normal CDF (Outs) edge hesabı, `pitcher_projections` JSON'a ekleniyor
- ✅ `PitcherProjections.jsx` → Mobile-first card grid yeniden tasarlandı:
  - 1 sütun (mobil) → 2 sütun (tablet+)
  - Kompakt pitcher header (isim + HP badge + matchup tek satır)
  - PropBar: model proj vs book line görsel karşılaştırması
  - Over **ve** Under odds her iki taraf gösteriliyor
  - Edge highlighting: %5+ için glowing border + top accent bar
  - Filtre toolbar: Search + Hand + Sort (Edge/K/IP) + Edges Only

**Beklemede:**
- ⚠️ Player Props API → the-odds-api **$30 Starter Plan** gerekiyor (Tyler'ın onayı bekleniyor). API key gelince veriler otomatik dolacak. Kod tamamen hazır.

---

## 🔲 YAPILACAK (M4 Kapsamında Devam)

### Kısa Vadeli (Öncelikli)
- [x] **Tyler'ın Geri Bildirimi 1 — Pitcher VIP Consensus Edges (Top 3 Edges)**: "Pitcher Projections" sekmesi aktifken sayfanın üstündeki "VIP Consensus Edges" bölümünde maç sonuçları yerine günlük en yüksek edge yüzdesine sahip ilk 3 atıcı prop (K veya Outs) edge'inin dinamik gösterilmesi ve kartlara tıklandığında yumuşak geçişle ilgili atıcının kartına kaydırılıp vurgulanması.
- [x] **Tyler'ın Geri Bildirimi 2 — Model Sabermetrik Açıklama Metni**: UI üzerindeki model açıklamasının revize edilmesi. Modelin sadece basit bir CSW/SwStr ayarı değil; atıcı iç/dış saha K%, rakip lineup'ın LHP/RHP splitleri, rakip iç/dış saha K% splitleri, beklenen Batters Faced (BF) hacmi ve hava sıcaklığı katsayılarını harmanlayan çok faktörlü bir sabermetrik motor olduğunun belirtilmesi.
- [x] **Bizim Bulduğumuz Düzeltme A — Pitcher Ev/Deplasman Dinamik Durumu (`is_home`)**: `pitcher_props_engine.py`'daki hardcode `is_home = False` atamasının kaldırılıp `prediction_runner.py`'dan atıcının gerçekten ev sahibi (`side == "home"`) veya deplasman olup olmadığının dinamik geçirilmesi.
- [x] **Bizim Bulduğumuz Düzeltme B — Rakip Lineup LHP/RHP Splitlerinin Aktarılması**: `team_splits.json`'daki `vs_LHP` ve `vs_RHP` takımsal K% splitlerinin `prediction_runner.py`'da atıcının fırlatış eline (L/R) göre seçilip `opp_lineup_avg` parametresi üzerinden K Model'e beslenmesi (şu an split verileri gitmediği için model genel `k_pct` fallback'ini kullanıyor).
- [x] **Opposing team K rank** → Her kart üzerinde "Opp K Rank: #3 vs RHP" badge'i (veri zaten mevcut)
- [x] **Matchup grade / Confidence score** → Edge % + proj vs line farkı + opp K rank kombinasyonu → A+/A/A-/B/C/D/F veya 1-100
- [x] **Pitcher last 3-5 K** → MLB StatsAPI game log endpoint ile son maçların K sayıları
- [x] **K / IP filter → tek metrik göster** → Filtre seçilince diğer prop bölümü gizleniyor
- [x] **Takıma göre filter** → Opponent dropdown ile belirli takıma karşı pitching yapanları listele

### Kısa Vadeli (Öncelikli — Tyler'ın Yeni Talepleri)
- [x] **Tyler'ın Geri Bildirimi 3 — Atıcı Kartlarına Son 5 Maç Başarı Oranı (Hit Rate)**: Atıcı kartındaki "Last 5 Ks" başlığının yanına, mevcut bookmaker K çizgisine göre atıcının son 5 maçta çizgiyi geçme (veya altında kalma) yüzdesini dinamik ekleme. Örn: `Last 5 Ks (80% Over)` veya `Last 5 Ks (100% Under)`.
- [x] **Tyler'ın Geri Bildirimi 4 — NRFI VIP Consensus Edges (Top 3 Edges)**: "NRFI Model" sekmesi aktifken sayfanın üstündeki banner'da günün en yüksek avantaja sahip ilk 3 NRFI veya YRFI edge'inin dinamik listelenmesi ve tıklandığında ilgili NRFI maç satırına yumuşak geçişle kaydırılıp vurgulanması.
- [ ] **Daily Model Ek Verileri Doğrulaması**: Günlük model için henüz entegre edilmemiş olan ek sabermetrik verilerin (Bullpen SIERA, HFA, Sonny Moore) orta vadeli yol haritası kapsamında geliştirilmeye devam etmesi.

### Orta Vadeli
- [x] **Bullpen SIERA entegrasyonu** → Covers.com veri kaynağı ve SIERA proxy hesabı ile dinamik entegrasyon (Tamamlandı)
- [x] **HFA dinamik stadyum katsayısı** → Park bazlı tarihsel ev/deplasman diferansiyeli (Tamamlandı)
- [x] **Sonny Moore Power Rankings** → Haftalık/Günlük güncelleme mekanizması (Tamamlandı)

---

## Versiyon Geçmişi

| Versiyon | Tarih | Değişiklik |
|---|---|---|
| v1.0 | ~28 May 2026 | M4 ilk çıktı: hamburger menü, lineup scraper, K model, props UI |
| v1.1 | 5 Haz 2026 | Bug fix: pitcher_stats.json backfill, k_pct/avg_ip kayıt sorunu, calculate_pitcher_metrics güncelleme |
| v1.2 | 6 Haz 2026 | Tyler geri bildirimleri (VIP Top 3 Pitchers, Model Tanımı), internal split (is_home, LHP/RHP) ve **ücretli API anahtarı entegrasyonu** (Props + NRFI + F5 Vegas kilitleri açıldı) |
| v1.3 (Planlanan) | 6 Haz 2026 | Tyler yeni talepleri: Son 5 K Hit Rate gösterimi, NRFI VIP Consensus Edges entegrasyonu ve kaydırma efekti |

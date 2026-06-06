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
- [x] **Daily Model Ek Verileri Doğrulaması**: Günlük model için dinamik sabermetrik verilerin (Bullpen SIERA, HFA, Sonny Moore) entegrasyonu başarıyla tamamlandı ve tüm modeller üzerinden doğrulandı.

### Tyler'ın Yeni Talepleri (v1.5 — 6 Haziran 2026)

- [x] **Görev 1 — Pitcher Projections Arayüzüne Üçlü Sıralama Filtresi (`All | Hit Rate | OPP K Rank`)** ✅ *Tamamlandı — 6 Haziran 2026*:
  * **Yapılacak Değişiklik**: "Edges Only" butonunun hemen üstüne yatay buton grubu (`All | Hit Rate | OPP K Rank`) eklenecektir. Butonlar aktif filtre durumuna göre görsel olarak (indigo glow efekti vb.) vurgulanacaktır.
  * **Sıralama Mantığı**:
    * `All`: Varsayılan sıralama (Edge yüzdesine göre veya oyuncu adına göre alfabetik).
    * `Hit Rate`: Pitcher kartlarındaki son 5 maçlık başarı oranını (L5 Hit Rate - örn: %80 Over) hesaplayıp, en yüksek başarı oranından en düşüğe (azalan sırada) sıralar.
    * `OPP K Rank`: Rakip takımın K% (strikeout) disiplin sıralamasına göre sıralar. K-disiplini en zayıf olan (en çok strikeout yapan, yani atıcı için en avantajlı olan) takım en üstte olacak şekilde sıralama yapılacaktır.
  * **Etkilenen Dosyalar**: 
    * [PitcherProjections.jsx](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/frontend/src/components/PitcherProjections.jsx) (UI entegrasyonu, State yönetimi ve Client-side sıralama algoritmaları).
  * **Zorluk Derecesi**: Kolay. (Veriler zaten props verisinde mevcut olduğundan frontend tarafında sıralama mantığının eklenmesi yeterlidir).

- [x] **Görev 2 — Hava Durumu Etki Modelinin Kalibrasyonu** ✅ *Tamamlandı — 6 Haziran 2026*:
  * **Yapılacak Değişiklik**: Wrigley Field örneğinde olduğu gibi (SSW yönünde esen 15 mph rüzgarda Runs +32%, HR +58% gösterilmesi gerekirken modelimizin +2.4% ve +5.6% göstermesi), rüzgar hızı ve yönünün stadyum yapısına göre (örneğin rüzgarın dışarı doğru esmesi - wind blowing out) çarpıcı etkilerini daha agresif katsayılarla modelleyen kalibrasyon formülünün güncellenmesi.
  * **Uygulanan Değişiklikler**:
    * **Kök sebep bulundu ve düzeltildi**: Open-Meteo API `"SSW to NNE"` formatında TO yönü veriyor (doğru). Weather.gov ise `"SSW"` formatında FROM yönü (meteorolojik standart) veriyor. Motor ikisini de TO yönü olarak yorumlayarak hatalı hesaplıyordu. `already_to_direction` bayrağı ile tek cardinal yön 180° çevrilerek doğru vektör hesabı sağlandı.
    * **Stadyum bazlı `park_wind_scale` sözlüğü eklendi**: Chi Cubs=1.8, SF Giants=1.4, Boston=1.3, Pittsburgh=1.2, Colorado=0.75 gibi gerçek aerodinamik özellikler yansıtıldı.
    * **Katsayılar kalibre edildi**: `runs_impact = total_carry * 0.75`, `hr_impact = total_carry * 1.37` → Wrigley 15mph SSW: **Runs +31.8%, HR +58.1%** (hedef: +32%/+58% ✅)
    * **Güvenlik sınırları eklendi**: runs max ±35-45%, hr max ±55-70%
  * **Etkilenen Dosyalar**: 
    * [mlb_unified_engine.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/services/mlb_unified_engine.py) (`calculate_weather_impact` metodu: ~90 satır değişiklik)
  * **Zorluk Derecesi**: Orta. (Kök sebep tespiti ve kalibrasyonu gerektirdi; unit testlerle doğrulandı).

- [ ] **Görev 3 — Konsensüs Spread Seçim Mantığının Düzeltilmesi (Consensus Spread Pick Alignment)**:
  * **Yapılacak Değişiklik**: Modelin galip tahmin ettiği veya desteklediği takımın (+1.5 veya -1.5) spread seçeneğini göstermek yerine, rakip takımın spread'ini çelişkili bir şekilde önermesi sorunu giderilecektir. Örneğin model Pittsburgh'un kazanacağını öngörürken (PIT ML), spread olarak `ATL +1.5` göstermesi yerine, modelin lehine olan ve daha yüksek odds/olasılık sunan `PIT +1.5` seçeneğini gösterecektir.
  * **Sorunun Kaynağı & Çözüm Mantığı**:
    * Bahis verisi gelmediğinde veya spread çizgisi tanımsız olduğunda uygulanan fallback mantığının (`awayScore > homeScore ? -1.5 : 1.5`) hatalı bir şekilde deplasmanı favori (-1.5) olarak varsayması ve bu durumun ev sahibini underdog (+1.5) yaparak çelişkili spread pick'ler üretmesi.
    * Spread pick belirleme mantığının sadece favori/underdog olasılıklarına göre değil, modelin doğrudan galip gördüğü (Moneyline kazananı) takıma göre hizalanması (`alignment`). Eğer model A takımının kazanacağını düşünüyorsa, spread pick olarak A takımının spread çizgisi (A -1.5 veya A +1.5) seçilmeli ve olasılığı buna göre hesaplanmalıdır.
  * **Etkilenen Dosyalar**: 
    * [prediction_runner.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/services/prediction_runner.py) (Konsensüs spread edge hesaplama algoritması ve fallback spread belirleme mantığı).
    * [MatchupCard.jsx](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/frontend/src/components/MatchupCard.jsx) (Kart içi consensus picks render hesabı ve fallback mantığı).
    * [App.jsx](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/frontend/src/App.jsx) (Ana sayfa üst barındaki spread edge hesaplamaları).
  * **Zorluk Derecesi**: Orta. (Farklı 3 dosyada yer alan spread hesaplama ve cover olasılık CDF mantıklarının birbiriyle ve model kazananıyla senkronize edilmesi gerekmektedir).

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
| v1.3 | 6 Haz 2026 | Tyler yeni talepleri: Son 5 K Hit Rate gösterimi, NRFI VIP Consensus Edges entegrasyonu ve kaydırma efekti |
| v1.4 | 6 Haz 2026 | Daily Model Sabermetrik Güçlendirmeleri: Dinamik Bullpen SIERA, Simetrik Stadium HFA, Ballpark Factor düzeltmesi ve Dinamik Sonny Moore PR entegrasyonları. |
| v1.5 | 6 Haz 2026 | Tyler'ın yeni talepleri: **Üçlü sıralama filtresi tamamlandı** (getHitRate + sortSubFilter + Sort Priority UI); **Hava durumu modeli kalibre edildi** (FROM/TO direction bug düzeltmesi, park_wind_scale dict, katsayı optimizasyonu → Wrigley 15mph: Runs +32%, HR +58%); spread düzeltmesi beklemede |

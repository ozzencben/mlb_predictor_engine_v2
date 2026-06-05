# MLB Predictor Engine - Milestone 4 Güncellenmiş Yol Haritası ve Son Durum

Tyler'ın 120$'lık yeni mikro yükseltme (small upgrade) planını onaylamasının ve paylaştığı el yazısı notların ardından, geliştirme kapsamı ve yol haritası güncellenmiştir.

Sitedeki tüm görsel grafikler, hava durumu kartları ve bildirim botları **Milestone 5**'e devredilmiş; Milestone 4 ise tamamen Tyler'ın ilettiği **Atıcı Özel Projeksiyon Modeli (Strikeouts & Outs)**, **Kadro (Lineup) Harmanlama ve Ana Model İyileştirmelerine** odaklanmıştır. Ayrıca bu yeni sayfanın ana ekranı kirletmemesi için navigasyonu sadeleştirecek **Hamburger Menü** de M4 kapsamına alınmıştır.

---

## 🏁 M4: Core Model Extensions & Pitcher Props ML Engine
**Bütçe:** $120  
**Odak:** Hamburger Navigasyon Menüsü, 5 Yeni Model İstatistiği + Kadro Bazlı wRC+/wOBA Harmanlama, Atıcı Projeksiyon ML Modeli, Kadro (Lineup) Kazıma ve Oran Entegrasyonu.

---

## 📊 Genel Tamamlanma Durumu

| Görev | Kapsam | Durum |
|---|---|---|
| Görev 1 | Hamburger / Dropdown Navigasyon Menüsü | ✅ TAMAMLANDI |
| Görev 2 | Günlük Kadro Veri Toplayıcı | ✅ TAMAMLANDI |
| Görev 3 | Ana Model Güçlendirmesi (5 yeni istatistik + Lineup blend) | 🟡 KISMI |
| Görev 4 | Atıcı Props ML Motoru (Strikeouts & Outs) | ✅ TAMAMLANDI |
| Görev 5 | Bahis Oranları Entegrasyonu & Props Tablosu UI | ✅ TAMAMLANDI |

---

## Görev Detayları

---

### ✅ Görev 1 — TAMAMLANDI: Header Dropdown / Hamburger Navigasyon Menüsü

**İmplementasyon:**
- `frontend/src/components/DropdownNavigation.jsx` → Modern hamburger menü bileşeni oluşturuldu.
- `frontend/src/App.jsx` → Yatay sekmeler kaldırıldı, hamburger menü entegre edildi.
- **"Pitcher Projections"** sekmesi menüye eklendi.
- Mobil uyumlu animasyonlar ve backdrop blur efekti uygulandı.

---

### ✅ Görev 2 — TAMAMLANDI: Günlük Kadro Veri Toplayıcı (Confirmed Lineups Scraper)

**İmplementasyon:**
- `backend/app/services/prediction_runner.py` → `get_lineup_for_game()` ve `fetch_last_completed_game_pk()` metodları yazıldı.
- MLB StatsAPI `/api/v1/game/{gamePk}/boxscore` endpointi ile günlük 9 kişilik başlangıç kadrosu çekiliyor.
- Resmi kadro açıklanmamışsa son tamamlanan maçtaki kadro **fallback** olarak kullanılıyor.
- Kadro verisi `lineups_cache.json` üzerinde tarih bazlı cache'leniyor; resmi kadrolar `is_official: true` ile işaretlenip günde bir kez fetch yapılıyor.
- Her oyuncunun bireysel vurma istatistikleri (hitting) MLB StatsAPI'den paralel olarak çekiliyor.
- `away_lineup_hydrated` / `home_lineup_hydrated` + `away_lineup_avg` / `home_lineup_avg` alanları game_dict'e eklenerek engine'e besleniyor.

---

### 🟡 Görev 3 — KISMİ TAMAMLANDI: Ana Model Güçlendirmesi ve Kadro Harmanlama

**Tamamlanan Alt Görevler:**

#### ✅ Pitcher Expected Stats (xERA, xFIP) — TAMAMLANDI
- `backend/app/services/pitcher_scraper.py` → `xfip` ve `xera` değerleri ESPN / StatsAPI'den çekilerek `pitcher_stats.json`'a ekleniyor.
- `prediction_runner.py` → `calculate_pitcher_metrics()` içinde `xfip`, `xera` hesaplanıp atıcı feature vektörüne dahil ediliyor.
- `pitcher_props_engine.py` → Outs projeksiyonunda `xfip` kullanılıyor.

#### ✅ Teams Hitting Stats vs Handedness (LHP/RHP Splits) — TAMAMLANDI
- `prediction_runner.py` → `fetch_team_splits_async()` metodu ile tüm takımların LHP/RHP split istatistikleri (avg, obp, slg, ops, k_pct) MLB StatsAPI'den çekiliyor.
- `mlb_unified_engine.py` → `predict_matchup()` imzasına `away_splits` ve `home_splits` parametreleri eklendi.
- Splits verisi game döngüsünde engine'e besleniyor.

#### ✅ Lineup wRC+ & wOBA Harmanlaması — TAMAMLANDI
- `prediction_runner.py` → Kadrodaki 9 oyuncunun bireysel wRC+, wOBA, K%, BB%, Pitches/PA, SwStr%, CSW%, Whiff%, Oswing%, Swing% ortalaması alınıyor.
- `mlb_unified_engine.py` → `away_lineup_avg` ve `home_lineup_avg` parametreleri ile engine günlük kadro bazlı dinamik analiz yapabiliyor.

#### 🔴 Bullpen SIERA — YAPILMADI
- Gereksinim: Rölyef atıcıların beceriye dayalı ERA değerleri (SIERA).
- Mevcut durum: Bu veri ne StatsAPI'de ne de mevcut scraper'larda bulunuyor.
- Blokaj: FanGraphs API erişimi veya CSV upload gerektirir; M5'e ertelendi.

#### 🔴 HFA (Home Field Advantage) Dinamik Katsayı — YAPILMADI
- Gereksinim: Stadyum bazlı dinamik ev sahibi avantajı çarpanı.
- Mevcut durum: Ana modelde sabit bir genel HFA var (`ballpark_stats.json` park factor kullanılıyor) ancak Tyler'ın istediği gibi **dinamik** ve **stadyum bazlı esneme** henüz uygulanmadı.
- Blokaj: Stadyum-spesifik tarihsel veri gerektirir.

#### 🔴 Power Ranking (Sonny Moore) Diferansiyeli — YAPILMADI
- Gereksinim: Sonny Moore güç sıralaması farkına göre çarpan.
- Mevcut durum: Statik veri kaynağı yok; web scraping gerektiriyor.
- Blokaj: Dış kaynak scraping + weekly güncelleme mekanizması gerektirir.

---

### ✅ Görev 4 — TAMAMLANDI: Atıcı Props ML Motoru (Strikeouts & Total Outs)

**İmplementasyon:**

#### `backend/app/models/pitcher_k_model.py` [YENİ]
- Tyler'ın el yazısı `K Model.ods` dosyasından tersine mühendislikle çözülen matematiksel model Python'a aktarıldı.
- **Pydantic Şemaları:** `PitcherStats`, `LineupAvg`, `ProjectionResult` oluşturuldu.
- **Hesaplama Motoru:** `PitcherKModel.calculate_projection()` metodu:
  - Home/Away K% ağırlıklı Expected K% hesabı (Pitcher: %65, Opponent: %45)
  - CSW% ve SwStr% lig ortalaması farklarının K% üzerine eklenmesi (%35'er ağırlık)
  - Baseball notasyonunu (5.2 IP) gerçek matematiksel değere (5.667) çeviren `baseball_ip_to_math_ip()`
  - Volume bazlı Projected K ve Projected Outs hesabı
  - ODS dosyasındaki "volume squaring" ve "relative reference" hataları düzeltildi

#### `backend/app/services/pitcher_props_engine.py` [GÜNCELLENDI]
- **K projeksiyonu** → `PitcherKModel`'e devredildi (CSW/SwStr lig ortalaması ayarlı)
- **Outs projeksiyonu** → xFIP × wRC+ regresyon modeli (değiştirilmedi)
- Arayüz değişmedi: `prediction_runner.py`'de sıfır değişiklik

#### `backend/test_pitcher_k_model.py` [YENİ]
- 3 test sınıfı: Pydantic validasyon + IP dönüşümü + Giolito mock matchup
- Tüm testler geçiyor

---

### ✅ Görev 5 — TAMAMLANDI: Bahis Oranları Entegrasyonu & Props Tablosu UI

**İmplementasyon:**

#### Backend — `backend/app/services/odds_provider.py`
- `fetch_player_props_for_games_async()` → the-odds-api `pitcher_strikeouts` ve `pitcher_outs` market verilerini paralel olarak çekiyor.
- `parse_pitcher_props_odds()` → Pitcher ismi eşleşmesi (fuzzy), Over/Under odds ayrıştırma, birincil kitapçılar (DK, FD, BetMGM, Caesars, Bovada) öncelikli.
- Cache mekanizması: `player_props_odds.json` fallback olarak kullanılıyor.
- **Not:** The-odds-api'nin `pitcher_strikeouts` / `pitcher_outs` market endpointleri $30 Starter Plan gerektiriyor. API key mevcut ancak plan yükseltilmediyse veriler boş geliyor (model yine de hata vermeden çalışıyor).

#### Backend — `prediction_runner.py`
- Props engine döngüye dahil edildi: Her başlangıç atıcısı için `proj_k`, `proj_outs`, `k_line`, `k_choice`, `k_edge`, `outs_line`, `outs_choice`, `outs_edge` hesaplanıyor.
- Poisson CDF (K için) ve Normal CDF (Outs için) ile model olasılığı → book implied olasılığı farkı (Edge) hesabı yapılıyor.
- `pitcher_projections` listesi `todays_predictions.json`'a ekleniyor.

#### Frontend — `frontend/src/components/PitcherProjections.jsx` [YENİ / YENİDEN TASARLANDI]
Tyler'ın el yazısı tablosunu tam karşılayan mobil-öncelikli card grid tasarımı:
- **Mobile-first:** Tek sütun (mobil) → 2 sütun (tablet ve üzeri)
- **Kompakt pitch header:** Pitcher ismi + handedness badge + "TEX vs HOU" matchup tek satırda
- **PropSection:** Her prop (K ve Outs) için görsel progress bar (model proj vs book line karşılaştırması)
- **Over ve Under odds** her iki taraf için ayrı ayrı gösteriliyor
- **Edge highlighting:** %5+ edge olan kartlar glowing border + top accent bar ile vurgulanıyor
- **Filtre toolbar:** Search + Hand (All/RHP/LHP) + Sort (Edge/K/IP) + Edges Only toggle
- **Özet pills:** Toplam pitcher sayısı + bulunan edge sayısı

**Tablo kolonları (Tyler'ın şemasıyla birebir):**
> `Pitcher | Book's K Line | Proj K's | O/U/Pass | Outs Book Line | Outs Proj | O/U/Pass | Edge`

---

## 📋 Milestone 4 Özet Değerlendirmesi

### Tamamlanan (%83)
1. ✅ Hamburger navigasyon menüsü
2. ✅ Günlük kadro veri toplayıcı (StatsAPI, fallback, cache)
3. ✅ xERA/xFIP pitcher expected stats
4. ✅ LHP/RHP team hitting splits
5. ✅ Lineup wRC+ / wOBA harmanlama
6. ✅ `PitcherKModel` (K Model.ods tersine mühendislik)
7. ✅ `PitcherPropsEngine` (xFIP × wRC+ outs, PitcherKModel K)
8. ✅ Player props odds API entegrasyonu (pitcher_strikeouts, pitcher_outs)
9. ✅ `PitcherProjections.jsx` UI (mobile-first card grid)

### Eksik Kalan (%17)
- 🔴 Bullpen SIERA → M5'e ertelendi (dış veri kaynağı gerekiyor)
- 🔴 HFA dinamik katsayı → M5'e ertelendi (stadyum bazlı tarihsel veri gerekiyor)
- 🔴 Sonny Moore Power Rankings → M5'e ertelendi (web scraping gerekiyor)
- ⚠️ Player Props API aktivasyonu → The-odds-api $30 Starter Plan gerekiyor (Tyler'ın onayı bekleniyor)

---

## 🏁 M5: Interactive Ballistics, Graphs & Alerts
**Bütçe:** Sonra Konuşulacak  
**Odak:** weathermlb.com Tarzı Genişleyen Kompakt Liste, Kapanabilir Recharts Stadyum Karşılaştırma Grafikleri, DraftKings -1 Spread Formülü, Telegram & SMS Bildirim Servisi, Canlı Edges, Bullpen SIERA, Dinamik HFA, Sonny Moore Power Rankings.

# MLB Predictor Engine - Milestone 4 & 5 Güncellenmiş Yol Haritası ve Mimarisi

Tyler'ın 120$'lık yeni mikro yükseltme (small upgrade) planını onaylamasının ve paylaştığı el yazısı notların ardından, geliştirme kapsamı ve yol haritası güncellenmiştir. 

Sitedeki tüm görsel grafikler, hava durumu kartları ve bildirim botları **Milestone 5**'e devredilmiş; Milestone 4 ise tamamen Tyler'ın ilettiği **Atıcı Özel Projeksiyon Modeli (Strikeouts & Outs)** ve **Ana Model İyileştirmelerine** odaklanmıştır. Ayrıca bu yeni sayfanın ana ekranı kirletmemesi için navigasyonu sadeleştirecek **Hamburger Menü** de M4 kapsamına alınmıştır.

---

## 🏁 M4: Core Model Extensions & Pitcher Props ML Engine
**Önerilen Bütçe:** $120  
**Tahmini Süre:** 6-8 Gün  
**Odak:** Hamburger Navigasyon Menüsü, 5 Yeni Model İstatistiği, Atıcı Projeksiyon ML Modeli (XGBoost/Random Forest), Kadro (Lineup) Kazıma ve Oran Entegrasyonu.

### Görev 1: Header Dropdown/Hamburger Navigasyon Menüsü
* **Zorluk**: 🟡 **ORTA (UI/UX Tasarımı)**
* **Bileşen**: `DropdownNavigation.jsx` [NEW], `App.jsx`
* **Hedef**: Yatay sekmeleri kaldırıp hamburger menü navigasyonuna geçmek. Yeni açılacak "Pitcher Projections" sayfasını bu menüde gizleyerek ana sayfanın kalabalıklaşmasını önlemek.

### Görev 2: Ana Model Güçlendirmesi (5 Yeni İstatistik)
* **Zorluk**: 🟡 **ORTA (Veri Kazıma & Algoritma Ağırlık Güncellemesi)**
* **Bileşen**: `mlb_unified_engine.py`, `prediction_runner.py`
* **Hedef**: Ana modelin tahmin başarısını artırmak için Tyler'ın belirttiği şu 5 temel veriyi formüle entegre etmek:
  1. **Bullpen SIERA:** Rölyef atıcıların beceriye dayalı bağımsız ERA değerleri.
  2. **HFA (Home Field Advantage):** Ev sahibi takıma verilecek küçük bir avantaj puanı.
  3. **Power Ranking (Sonny Moore) Diferansiyeli:** Sonny Moore güç sıralaması farkına göre küçük bir çarpan artışı.
  4. **Pitchers Expected Stats (xERA, xFIP):** Başlangıç atıcılarının şanstan arındırılmış beklenen ERA ve FIP değerleri.
  5. **Teams Hitting Stats vs Handedness of SP:** Takımların maça çıkacak atıcının el tercihine (Solak/Sağlak) göre tarihsel vuruş istatistikleri (LHP/RHP splits).

### Görev 3: Atıcı Projeksiyon Makine Öğrenmesi Modeli (Strikeouts & Total Outs)
* **Zorluk**: 🔴 **ZOR (Veri Bilimi, XGBoost/Random Forest & Lineup Scraper)**
* **Bileşen**: `pitcher_props_engine.py` [NEW], `prediction_runner.py`
* **Hedef**: Tyler'ın el yazısı parametre listesine göre geçmiş 3 yıllık verilerle eğitilecek bir XGBoost veya Random Forest modeli kurmak:
  * **Atıcı Özellikleri (Pitcher):** Home/Away K%, CSW%, SwStr%, K-BB%, Putaway%, BB%, Pitches per PA, Avg Batters Faced/Game, Avg Innings Pitched/Game, Whiff%.
  * **Kadro Özellikleri (Lineup):** Günlük teyitli başlama kadrolarını (Lineup) MLB StatsAPI üzerinden anlık çekeceğiz. Kadrodaki vurucuların Home/Away K%, vs LHP/RHP K%, Pitches per PA, Oswing%, SwStr%, CSW%, In Zone Contact%, Whiff%, Swing%, BB% değerleri.
  * **Çevre Koşulları:** Ballpark pusulası ve stadyum rüzgar/hava durumu balistik verileri.

### Görev 4: Atıcı Özel Bahisleri Paneli ve Tablosu (Pitcher Projections)
* **Zorluk**: 🟡 **ORTA (React Arayüzü & Oran Birleştirme)**
* **Bileşen**: `PitcherPropsSheet.jsx` [NEW], `api.py`
* **Hedef**: Tyler'ın $30'lık ücretli plana geçerek aktif edeceği `the-odds-api.com` anahtarından oyuncu strikeout ve outs limitlerini/oranlarını çekmek. Hamburger menüye bağlı sayfada el yazısı şablondaki tabloyu oluşturmak:
  `Pitcher | Book's K line | Proj K's | O/U/Pass | Total Outs Book line | Total Outs Proj | O/U/Pass | Edge`

---

## 🏁 M5: Interactive Ballistics, Graphs & Alerts
**Önerilen Bütçe:** Sonra Konuşulacak  
**Odak:** weathermlb.com Tarzı Genişleyen Kompakt Liste, Kapanabilir Recharts Stadyum Karşılaştırma Grafikleri, DraftKings -1 Spread Formülü, Telegram & SMS Bildirim Servisi ve Canlı Edges.

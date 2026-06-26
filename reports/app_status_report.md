# Legends Sports Predictor Engine V2 - Genel Proje Durum Raporu

Bu rapor; **MLB (Beyzbol)**, **Tenis** ve **WNBA (Basketbol)** modellerinin mevcut durumunu, çalışma prensiplerini, aralarındaki yapısal/görsel uyumsuzlukları, unutulmuş/eksik kalmış maddeleri ve geleceğe yönelik geliştirme önerilerini detaylandırmaktadır.

---

## 1. Modellerin Mevcut Durumu ve Çalışma Sistemleri

### 🏀 WNBA (Kadınlar Basketbolu)
* **Mevcut Durum**: 
  - MLB stiline uygun olarak güncellenmiş yan yana (side-by-side) takım yerleşimi ve Covers.com stili son 10 maç geçmişi (Win/Loss, ATS, Over/Under logoları ve trend ikonlarıyla) aktiftir.
  - Zayıf (underdog) takımların kazanma olasılığı düşük olduğunda, kafa karışıklığını önlemek adına "Model-Implied Value Plays" kısmında underdog Moneyline (ML) bahis önerileri gizlenmekte; kullanıcılar bunun yerine Spread veya Alt/Üst seçeneklerine yönlendirilmektedir.
  - Röntgen detaylarının altına, tıklandığında paneli kapatıp pürüzsüz bir şekilde karta geri odaklanan (smooth scroll) "Collapse Details" butonu eklenmiştir.
  - AI analizlerinde Groq/Gemini sağlayıcıları yedekli (fallback) çalışmakta ve model kazanan tahmini değiştiğinde AI analizini otomatik yenileyen önbellek geçersiz kılma mekanizması bulunmaktadır.
* **Çalışma Sistemi**: 
  - Günlük pipeline (`pipeline_runner.py`) ESPN üzerinden fikstürü çeker, The Odds API'den oranları alır, ESPN injury API'sinden sakatlık durumlarını çeker. 
  - Dünün biten maçlarını veri tabanına (`team_game_logs.json`) ekler ve ELO verilerini günceller.
  - ELO, son 5 maç form grafikleri (PPG, Net Rating, TS%, Pace vb.) üzerinden tahmin üreterek `today_predictions.json` dosyasını günceller.

### ⚾ MLB (Major League Baseball)
* **Mevcut Durum**: 
  - Projenin en olgun, en karmaşık ve en yüksek isabet oranına sahip amiral gemisi modelidir.
  - Takım bazlı değil, **kadro bazlı (lineup-based)** modelleme yapar. StatsAPI üzerinden her iki takımın 1-9 arası vurucu kadrolarını ve başlangıç pitcher'larını anlık sorgular. Resmi kadrolar açıklanmamışsa önceki maçın kadrosunu "fallback" olarak devreye sokar.
  - Hava durumu (sıcaklık, nem, rüzgar hızı ve yönünün topun uçuş yönüne etkisi) ve ballpark (stadyum boyutları, rakım ve tarihsel sayı üretme çarpanları) etkileri matematiksel olarak simülasyona dahildir.
  - Bullpen kalitesini ölçmek için **SIERA** metriğini kullanır ve vurucuların solak/sağlak pitcher'lara (LHP/RHP) karşı olan splits istatistiklerini işler.
  - Maç sonucunun yanı sıra **İlk 5 Inning (F5)**, **İlk Inning Sayı Olmaz (NRFI)** ve **Pitcher Strikeouts (K) / Outs Projeksiyonları** (Poisson olasılık dağılımı ile) gibi alt pazarlarda tahmin üretir.
* **Çalışma Sistemi**: 
  - Günlük scheduler veya `run_daily_pipelines.py` ile ET saatiyle 00:00 ve 12:00'de (TSİ 07:00 ve 19:00) çalışır.
  - Vurucu/pitcher istatistiklerini, hava durumunu, sakatlıkları ve oranları toplayıp `MLBUnifiedEngine` üzerinde simüle eder. Günün en iyi bahis avantajlarını belirleyip "Consensus Edges" olarak kilitler.

### 🎾 Tenis (ATP & WTA)
* **Mevcut Durum**: 
  - ATP ve WTA turnuvalarını kapsayan, erkek ve kadın maçları için ELO bazlı çalışan bir modeldir.
  - ~34MB boyutunda devasa bir geçmiş maç veritabanı (`dataset.json`) ve ~3MB boyutunda eğitilmiş bir olasılık motoru (`tennis_brain.json`) kullanır.
  - Arayüzde o gün oynanan aktif turnuvaları (Wimbledon, Eastbourne, Mallorca vb.) listeler ve turnuvaya göre filtreleme sunar.
  - Geçtiğimiz günlerde, verilerin eksik veya NaN döndüğü durumlarda arayüzü çökerten `toFixed` crash hatası tamamen düzeltilmiş ve korumaya alınmıştır.
* **Çalışma Sistemi**:
  - `TennisPipelineRunner` üzerinden çalışır. `full` modda çalıştırıldığında dünün tamamlanan maçlarını oyuncu profillerine işler, oyuncuların ELO puanlarını artımlı olarak günceller, bugünün fikstürünü çeker, eksik oyuncu geçmişlerini Playwright ile tamamlar ve tahminleri üretir.

---

## 2. Uyumsuzluklar ve Düzensizlikler (Inconsistencies)

Sistemdeki üç model farklı dönemlerde geliştirildiği için mimari ve görsel açıdan bazı uyumsuzluklar barındırmaktadır:

| Özellik / Katman | MLB (Beyzbol) | WNBA (Basketbol) | Tenis |
| :--- | :--- | :--- | :--- |
| **Modelleme Temeli** | Kadro ve Oyuncu Bazlı (Lineup, SP, LHP/RHP Splits, SIERA) | Takım ve ELO Bazlı (Team Logs, ELO, L5 stats) | Oyuncu ve ELO Bazlı (Player ELO, ATP/WTA Ranks) |
| **Dış Etken Entegrasyonu** | Hava Durumu (Rüzgar/Sıcaklık), Ballpark Özellikleri | Yok | Yok (Zemin türü ELO'ya etki etmiyor) |
| **Bahis Verisi Kaynağı** | `OddsProvider` (Özel kazıma ve karmaşık veri tabanı) | `The Odds API` | `live_odds_tennis.json` |
| **Sözel AI Analizi** | Mevcut (Gecikmeli sıralı API istekleri ve SP bazlı cache) | Mevcut (Winner bazlı cache ve force override) | **Yok** (Yorum desteği eklenmemiş) |
| **Detay Kapatma (Collapse)** | Yok (Sadece ok tuşu var) | **Mevcut** (Collapse butonu + smooth scroll) | Yok |
| **Terimler Sözlüğü (Glossary)**| Yok | **Mevcut** (ATS, O/U açıklayan interaktif panel) | Yok |
| **Consensus Picks Kutusu** | Mevcut | Mevcut | **Yok** |

---

## 3. Unutulanlar ve Eksik Kalanlar (Forgotten / Missing Items)

1. **WNBA 1. Yarı (1st Half) ve 1. Çeyrek (1st Quarter) Modellemeleri**:
   - Tyler'ın ilk taleplerinden biri olan, 1. Yarı ve 1. Çeyrek skor/oran tahminleri henüz sisteme entegre edilmedi. Model şu an sadece tüm maçı (Full Time) tahmin etmektedir.
2. **WNBA Kadro Tabanlı (Lineup-based) Modelleme**:
   - WNBA modeli şu anda sadece takım istatistiklerine ve ELO'ya dayanıyor. Sakatlıklar arayüzde gösterilse de, MLB'deki gibi ilk 5 oyuncunun (Starting Lineup) değişmesinin simülasyona doğrudan etkisi bulunmamaktadır.
3. **Tenis Turnuva Dropdown Güncelliği**:
   - Günlük fikstür çekilirken turnuva isimlerindeki uyumsuzluklar veya turnuva başlangıç saatlerindeki oynamalar sebebiyle dropdown menüsünde zaman zaman aktif olmayan turnuvalar kalabilmektedir.
4. **MLB Kartlarında Arayüz Eksikleri**:
   - WNBA kartlarına eklenen "Betting Terms" (ATS, O/U sözlüğü) ve "Collapse Details" (yumuşak kaydırmalı kapatma butonu) gibi kullanıcı deneyimini artıran özellikler MLB kartlarına henüz uyarlanmamıştır.

---

## 4. Geliştirilmesi Gerekenler ve Öneriler (Roadmap)

### Kısa Vadeli Geliştirmeler (Quick Wins)
* **Arayüz Standardizasyonu**: WNBA dashboard'una eklediğimiz premium "Betting Terms" ve "Collapse Details" buton yapısını MLB ve Tenis dashboard'larına da giydirerek tüm sitede UX birliği sağlamak.
* **Tenis İçin AI Analiz Desteği**: Tenis maç kartlarının altına da Groq/Gemini entegrasyonu ile oyuncuların son form durumunu özetleyen mini sözel analizler (AI Edge Insight) eklemek.
* **Tenis Zemin ELO'su**: Tenis ELO hesaplamasına oyuncunun çim, toprak veya sert korttaki tarihsel başarısını yansıtacak katsayılar eklemek (Örn: Çim kortta Nadal ile Djokovic arasındaki ELO farkının zemine göre değişmesi).

### Orta Vadeli Geliştirmeler
* **WNBA 1. Yarı / 1. Çeyrek Tahminleri**: Lig ortalamaları ve takım periyot eğilimlerini modelleyerek WNBA kartlarına 1. Yarı ve 1. Çeyrek handikap (spread) ve Alt/Üst (Total) tahmin satırlarını eklemek.
* **Ortak Odds Servisi**: `OddsProvider`, `The Odds API` ve tenis oranlarını tek bir soyutlama katmanı (Abstract Odds Service) altında birleştirmek. Bu sayede oran çekme hataları minimuma iner.

### Uzun Vadeli Geliştirmeler
* **WNBA Kadro Tabanlı Simülasyon (Lineup Upgrade)**: WNBA oyuncularının bireysel PER (Player Efficiency Rating), WAR (Wins Above Replacement) veya ortalama sayı/ribaunt/asist katkılarını hesaplayan bir veri tabanı kurarak, o gün sahaya çıkacak 5 oyuncuya göre dynamically güncellenen bir basketbol simülasyon motoru yazmak.

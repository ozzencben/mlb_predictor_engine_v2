# ⚾ MLB Predictor Engine v2: Veritabanı & Hafıza Katmanı Röntgen Raporu

Bu rapor, **MLB Predictor Engine v2** sisteminin mevcut "dosya tabanlı ve belleksiz (stateless)" veri işleme mimarisini analiz etmek, sistemi "uzun vadeli hafızaya (stateful)" kavuşturmak ve analitik doğruluğu artırmak amacıyla hazırlanmış kapsamlı bir mimari entegrasyon planıdır.

---

## 1. Giriş ve Mevcut Durum Analizi (Mevcut Röntgen)

Projenin mevcut veri toplama ve işleme boru hattı (pipeline) incelendiğinde, verilerin geçici disk dosyalarında saklandığı görülmektedir:

*   **Veri Akışı:** Scraper servisleri (`DataCollector`, `PitcherScraper`, `MatchupScraper`, `WeatherScraper`, `OddlySpecificScraper` vb.) verileri çeker, işler ve `backend/app/data/` klasörü altındaki `live_stats.json`, `pitcher_stats.json` gibi statik dosyalara kaydeder.
*   **Tahmin Motoru:** `PredictionRunner` bu JSON dosyalarını okur, modelleri çalıştırır, Gemini API ile AI analizi ekler ve nihai sonucu tek bir devasa `todays_predictions.json` dosyasına yazar.
*   **Geçmiş Takibi:** `backend/app/data/history/` klasöründe her güne özel `YYYY-MM-DD_stats.json` ve `YYYY-MM-DD_pitchers.json` dosyaları saklansa da bu veriler üzerinde sorgulama yapmak, geçmişe yönelik performans analizi gerçekleştirmek veya dinamik atıcı form durumu hesaplamak imkansızdır.

### Mevcut Mimari Eksiklikleri ve Riskler

> [!WARNING]
> **Render Geçici Disk Alanı (Ephemeral Storage Risk):**  
> Render'ın ücretsiz veya standart web servisleri "stateless" (geçici) konteynerler kullanır. Sunucu 15 dakika inaktif kaldığında uyku moduna geçer ve her yeniden başladığında diskteki geçici dosyalar (JSON verileri ve günlük geçmiş) silinir. Bu durum, veri kaybına ve her cold-start sonrasında sistemi sıfırdan kazımaya zorlayarak yüksek gecikmelere sebep olur.

> [!CAUTION]
> **Geri Besleme (Feedback Loop) Yokluğu:**  
> Mevcut sistemde dün yapılan tahminlerin tutup tutmadığını takip eden otomatik bir mekanizma yoktur. Hangi modelin (NRFI, F5, Full) hangi koşullarda daha başarılı olduğu ölçülemez. Bu durum, sistemin kendini kalibre etmesini ve optimizasyon yapılmasını engeller.

---

## 2. Hangi İstatistikler Toplanmalı? (Veri Katmanı Röntgeni)

Hafızalı bir sistemde sadece anlık durumlar değil, **zaman serisi (time-series)** verileri ve **maç sonuçları** da depolanmalıdır.

| Veri Kategorisi | Mevcut Durum (Dosya Tabanlı) | Hedeflenen Durum (Veritabanı Tabanlı) | Sağlayacağı Analitik Avantaj |
| :--- | :--- | :--- | :--- |
| **Atıcı (Pitcher) İstatistikleri** | Sadece günün başlangıç atıcısının (SP) o anki genel sezon istatistikleri (`ERA`, `FIP`, `K-BB%`). | Atıcının her güne ait istatistik snapshot'ları, sezonluk kümülatif verileri ve sakatlık/dinlenme durumları. | Atıcının zamana bağlı performans grafiği, yükselen veya düşen FIP trendlerinin tespiti (Pitcher Momentum). |
| **Takım İstatistikleri** | O anki genel RPG Offense/Defense, Batting Average ve wRC+ değerleri. | Günlük bazda güncellenen takım metrikleri, iç saha/dış saha performansı kırılımları. | Takımların form grafiklerinin (Son 5/10 maç) modele dinamik ağırlık olarak eklenmesi. |
| **Hava Durumu & Stadyum** | O güne özel anlık sıcaklık ve rüzgar hızı/yönü. | Maçın oynandığı saatteki hava durumu verilerinin maç sonucu ile ilişkili olarak arşivlenmesi. | Rüzgar ve sıcaklığın, toplam sayı (Over/Under) modellerindeki isabet oranına olan tarihsel etkisinin analizi. |
| **Bahis Oranları (Odds)** | Anlık çekilen en iyi oranlar. | Oranların açılış (Opening) ve kapanış (Closing) değerleri arasındaki tüm hareketler (Line Movement). | Profesyonel oyuncuların (Sharp Money) hangi yöne para yatırdığının tespiti ve Kapanış Oran Avantajı (CLV) hesabı. |
| **Maç Sonuçları (Outcomes)** | **Hiç toplanmıyor.** | Dün oynanan maçların nihai skorları, ilk inning (NRFI/YRFI) sonuçları, ilk 5 inning (F5) skorları. | **En Kritik Eksiklik:** Modellerin geriye dönük başarı oranlarının (Win Rate, ROI, Brier Score) otomatik hesaplanması. |

---

## 3. Ne Tür Bir Veritabanı Kullanılmalı? (Mimari Karar)

Bu sistem için en uygun çözüm **PostgreSQL (İlişkisel Veritabanı)** sistemidir.

### Neden PostgreSQL?
1. **İlişkisel Veri Yapısı:** Beyzbol verileri doğası gereği oldukça ilişkilidir. Takımlar oyuncuları, oyuncular istatistikleri, maçlar takımları ve atıcıları barındırır. Bu ilişkileri korumak ve karmaşık SQL sorguları (JOIN işlemleri) ile analiz yapmak PostgreSQL ile son derece kolaydır.
2. **Gelişmiş Analitik Sorgular (Window Functions):** Atıcının son 5 maçtaki hareketli FIP ortalamasını bulmak veya takımların son 10 maçtaki sayı ortalamalarını hesaplamak için PostgreSQL'in pencere fonksiyonları (Window Functions) biçilmiş kaftandır.
3. **Bulut Entegrasyonu:** Render üzerinde kolayca yönetilen (Managed) PostgreSQL veritabanı kurulabilir veya Neon, Supabase gibi harici modern serverless Postgres servisleri ücretsiz/düşük maliyetle entegre edilebilir.

### Önerilen İlişkisel Veritabanı Şeması (ERD)

Aşağıdaki şemada, sistemin hafızasını oluşturacak ana tablolar ve aralarındaki ilişkiler tanımlanmıştır:

```mermaid
erDiagram
    TEAMS ||--o{ GAMES : "ev_sahibi / deplasman olarak katılır"
    PITCHERS ||--o{ GAMES : "baslangic_aticisi olarak oynar"
    PITCHERS ||--o{ PITCHER_HISTORICAL_STATS : "gunluk snapshot barindirir"
    GAMES ||--|| PREDICTIONS : "tahmin sonucu uretilir"
    GAMES ||--o{ ODDS : "canli oran kayitlari tutulur"
    GAMES ||--|| GAME_RESULTS : "mac sonucu ile sonuclanir"

    TEAMS {
        int id PK
        string name "Örn: Cleveland Guardians"
        string abbreviation "Örn: CLE"
        string teamrankings_name "Scraper eşleşme adı"
        string mlb_api_id "MLB resmi API ID'si"
    }

    PITCHERS {
        int id PK
        string mlb_id "Resmi MLB ID"
        string name "Adı Soyadı"
        string throw_hand "R/L"
        int wins
        int losses
        float current_fip
        float current_era
    }

    PITCHER_HISTORICAL_STATS {
        int id PK
        int pitcher_id FK
        date record_date
        float era
        float fip
        float k_bb_pct
        float innings_pitched
    }

    GAMES {
        int id PK
        date game_date
        int home_team_id FK
        int away_team_id FK
        int home_pitcher_id FK
        int away_pitcher_id FK
        string status "TBD / SCHEDULED / COMPLETED"
        string game_time
        float weather_temp
        float weather_wind_speed
        string weather_wind_direction
    }

    PREDICTIONS {
        int id PK
        int game_id FK "Unique"
        datetime prediction_time
        float nrfi_prob "Model NRFI olasılığı"
        float yrfi_prob "Model YRFI olasılığı"
        string nrfi_pick "NRFI / YRFI"
        float f5_away_prob
        float f5_home_prob
        float full_away_prob
        float full_home_prob
        float predicted_total_runs
        string value_alerts "JSON String / Array"
    }

    ODDS {
        int id PK
        int game_id FK
        datetime record_time
        string bookmaker "Örn: DraftKings"
        float home_win_odds
        float away_win_odds
        float nrfi_odds
        float yrfi_odds
        float over_under_total
        float over_odds
        float under_odds
    }

    GAME_RESULTS {
        int id PK
        int game_id FK "Unique"
        int final_home_score
        int final_away_score
        int f5_home_score
        int f5_away_score
        int first_inning_home_runs
        int first_inning_away_runs
        string nrfi_outcome "NRFI / YRFI"
        datetime updated_at
    }
```

---

## 4. Toplanan Verilerle Ne Gibi Hesaplamalar Yapabiliriz? (Analitik Röntgen)

Hafıza katmanının kurulması, tahmin motorumuzun zekasını katbekat artıracaktır. İşte yapılabilecek yeni nesil sabermetrik hesaplamalar:

### A. Otomatik Backtesting & Model Kalibrasyonu (Brier Score)
*   **Brier Skoru:** Olasılık tahminlerinin ne kadar başarılı olduğunu ölçen formüldür:
    $$BS = \frac{1}{N} \sum_{t=1}^{N} (f_t - o_t)^2$$
    *(Burada $f_t$ modelin verdiği olasılık, $o_t$ ise gerçekleşen durumdur (1 veya 0)).* Veritabanı sayesinde NRFI olasılıklarımızın doğruluğunu günlük olarak ölçüp modellerimizin matematiksel ağırlıklarını dinamik olarak optimize edebiliriz.
*   **Edge Performans Analizi:** Oranlara karşı bulduğumuz örneğin `%5 Edge` tahminlerinin tarihsel olarak ne kadar kazandırdığını (ROI - Return on Investment) raporlayabiliriz. Böylece sadece en karlı "Edge" aralıklarına bahis yapılmasını sağlayabiliriz.

### B. Dinamik Atıcı Form Durumu (Pitcher Momentum Coefficient)
*   Mevcut sistemde atıcının sezonluk genel FIP değeri kullanılmaktadır. Oysa beyzbolda atıcı form durumları çok değişkendir.
*   Veritabanı sayesinde atıcının **son 3 maç FIP ortalaması** ile **sezonluk FIP ortalaması** karşılaştırılarak bir **Atıcı Momentum Katsayısı (PMC)** hesaplanabilir:
    $$PMC = FIP_{season} - FIP_{last3}$$
    * PMC > 0 ise atıcı son günlerde sezona göre daha formdadır ve bu durum NRFI olasılığına pozitif etki yapar.

### C. Gelişmiş Hava Durumu ve Rüzgar Regresyonu
*   Wrigley Field veya Fenway Park gibi stadyumlarda rüzgarın esiş yönü ve sıcaklık, toplam sayı bahislerini dramatik şekilde etkiler.
*   Tarihsel veriler biriktiğinde, *"X stadyumunda sıcaklık 25 derecenin üzerindeyken ve rüzgar dışarıya doğru saatte 15 milden hızlı esiyorken oynanan maçlarda ortalama sayı beklentisi modele %12 eklenmelidir"* gibi istatistiksel düzeltmeleri otomatik hale getirebiliriz.

---

## 5. Hangi Dosyalarda Ne Tür Değişiklikler Yapılmalı? (Değişiklik Yol Haritası)

Veritabanı entegrasyonu için backend projesinde izlenmesi gereken somut adımlar ve etkilenecek dosyalar aşağıda listelenmiştir:

### 1. Bağımlılıkların Eklenmesi
*   **Etkilenecek Dosya:** [`backend/pyproject.toml`](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/pyproject.toml)
*   **Yapılacak Değişiklik:** Asenkron veritabanı işlemleri için `SQLAlchemy` ve PostgreSQL sürücüsü olan `asyncpg` kütüphaneleri projeye eklenmelidir. Ayrıca veritabanı migrasyonları için `alembic` entegre edilmelidir.

```toml
[dependencies]
sqlalchemy = "^2.0.0"
asyncpg = "^0.29.0"
alembic = "^1.13.0"
```

### 2. Çevresel Değişkenlerin ve Ayarların Güncellenmesi
*   **Etkilenecek Dosyalar:** [`backend/.env.example`](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/.env.example) ve `backend/app/core/config.py`
*   **Yapılacak Değişiklik:** `DATABASE_URL` değişkeni tanımlanmalı ve Config sınıfına dahil edilmelidir.

```ini
# .env.example eklemesi
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/mlb_predictor
```

### 3. Veritabanı Modellerinin ve Bağlantı Havuzunun Kurulması
*   **Yeni Dosyalar:**
    *   `backend/app/db/session.py` (SQLAlchemy asenkron motorunun ve session nesnesinin oluşturulması)
    *   `backend/app/db/models.py` (Yukarıda ERD şemasında verilen tabloların SQLAlchemy ORM sınıfları olarak tanımlanması)
*   **Etkilenecek Dosya:** `backend/app/core/lifespan.py` (FastAPI açılışında veritabanı bağlantı havuzunun initialize edilmesi)

### 4. Sonuç Takip Servisinin Yazılması (Geri Besleme Katmanı)
*   **Yeni Dosya:** `backend/app/services/result_tracker.py`
*   **Açıklama:** Her gün gece yarısı veya sabah saatlerinde çalışıp, dün oynanan maçların skorlarını resmi MLB API'sinden çekerek `game_results` tablosuna işleyen ve tahminlerin tutup tutmadığını (NRFI/YRFI, F5, Full Game) belirleyen yeni bir asenkron servis yazılmalıdır.

```python
# app/services/result_tracker.py (Örnek Taslak)
class ResultTracker:
    async def track_yesterdays_results(self, db_session):
        # 1. Dünün tamamlanmış maçlarını veritabanından bul
        # 2. MLB API (statsapi.mlb.com) ile dünün nihai skorlarını çek
        # 3. game_results tablosuna kaydet
        # 4. Tahminlerin kazandı/kaybetti durumunu güncelle
        pass
```

### 5. PredictionRunner'ın Güncellenmesi
*   **Etkilenecek Dosya:** [`backend/app/services/prediction_runner.py`](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/services/prediction_runner.py)
*   **Yapılacak Değişiklik:** Artık verileri çekerken ve tahminleri üretirken her şeyi JSON dosyalarına yazmak yerine veritabanına `INSERT / UPDATE` sorgularıyla kaydetmelidir.
*   **Hibrit Çözüm Önerisi:** Hız ve mevcut frontend uyumluluğu açısından, veritabanına kayıt işlemi yapıldıktan sonra günün tahmin verisi yine de bir önbellek (Cache) katmanı gibi `todays_predictions.json` dosyasına yazılmaya devam edebilir (Böylece frontend tarafında büyük değişiklikler yapılması gerekmez).

### 6. API Katmanının ve Uç Noktaların Güncellenmesi
*   **Etkilenecek Dosya:** [`backend/app/api/v1/api.py`](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/api/v1/api.py)
*   **Yapılacak Değişiklikler:**
    *   `/predictions` uç noktası veriyi JSON dosyasından okumak yerine veritabanından çekmelidir.
    *   **Yeni Uç Noktalar:**
        *   `GET /api/v1/analytics/performance`: Tarihsel kazanma oranlarını, ROI değerini ve Brier skorlarını döndüren analiz endpoint'i.
        *   `GET /api/v1/predictions/history`: Kullanıcıların geçmiş tahminleri tarih bazlı filtreleyebileceği endpoint.

---

## 6. Sonuç ve Öneriler (Rapor Özeti)

> [!NOTE]
> Projeye bir ilişkisel veritabanı eklenmesi, sistemi basit bir "veri kazıma ve tahmin etme scripti" olmaktan çıkarıp, gerçek anlamda **öğrenen, kendi kendini test eden ve tarihsel veri gücünü kullanan kurumsal bir yapay zeka/tahmin motoruna** dönüştürecektir.

### Yol Haritası Önerisi:
1. **1. Faz (Altyapı):** Render veya Neon üzerinde PostgreSQL kurulumunun yapılması, SQLAlchemy modellerinin kodlanması ve verilerin eş zamanlı hem DB'ye hem JSON'a yazılması (Safe-fallback).
2. **2. Faz (Geri Besleme):** `ResultTracker` servisinin yazılıp dünün maç sonuçlarının otomatik çekilmesi ve başarı istatistiklerinin biriktirilmeye başlanması.
3. **3. Faz (Dashboard):** Frontend projesine yeni bir "Başarı Analitiği (ROI/Win-Rate)" sayfasının eklenerek kullanıcıya modelin gücünün şeffaf şekilde gösterilmesi.

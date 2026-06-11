# Milestone 5 - Çoklu Spor Genişlemesi, Hitter Center ve Telegram Botu Yol Haritası (M5 Roadmap)

Bu yol haritası, Tyler'ın talep ettiği yeni tenis tahmin motoru, çoklu spor arayüzü, hamburger menü altına eklenecek "Hitter Center" (Vurucu Merkezi), Fantasy Info Central otomatik kazıyıcısı, FantasyPros CSV yükleme portalı ve geçmişte bahsettiği **VIP Telegram Bildirim Botu** isteklerini mimari açıdan planlamaktadır.

Ayrıca raporun en altında, mevcut projenin teknik bir "Röntgeni" (mimari denetim ve eksiklikler analizi) çekilerek gelecekte yapılması gereken kritik güncellemeler listelenmiştir.

---

## 🗺️ Mimari Genel Bakış ve Entegrasyon Stratejisi

Çoklu spor yapısına geçişte sitenin performansını korumak ve Tyler'ın tüm tahmin modellerini (MLB, Tenis, yakında NFL ve NBA) tek bir çatı altında birleştirmek için aşağıdaki mimariyi uygulayacağız:

```mermaid
graph TD
    subgraph Frontend [React Multi-Sport Frontend]
        Navbar[Hamburger & Sport Selector] --> Home[Multi-Sport Homepage]
        Home --> MLBTab[MLB Center]
        Home --> TennisTab[Tennis Center]
        Navbar --> HitterCenter[Hitter Center Page]
        HitterCenter --> BvP[BvP Sub-tab & Sliders]
        HitterCenter --> FP7[FantasyPros Last 7 Days]
        HitterCenter --> FPProj[FantasyPros Projections]
        HitterCenter --> FICPicks[FIC Hit/HR Scraped Picks]
        Navbar --> Admin[Admin Portal: CSV Upload]
    end

    subgraph Backend [FastAPI Multi-Sport Backend]
        API[api.py] --> MLBRoutes[/api/v1/mlb/*]
        API --> TennisRoutes[/api/v1/tennis/*]
        API --> AdminRoutes[/api/v1/admin/upload]
        
        AdminRoutes --> Parser[CSV Parser Service]
        Parser --> JSONDB[(JSON / Local Storage DB)]
        
        MLBRoutes --> MLBEngine[MLB Unified Engine]
        TennisRoutes --> TennisEngine[Tennis Prediction Engine]
        
        TennisEngine --> TennisScraper[Tennis Daily Scraper]
        FICScraper[FIC Hit/HR Scraper] --> JSONDB
    end

    subgraph Notifications [Alerting & Notifications]
        Cron[APScheduler / Cron] --> TelegramBot[Telegram Alert Bot]
        JSONDB --> TelegramBot
        TelegramBot --> Users[VIP Telegram Channel]
    end
```

---

## 📊 M5 Yol Haritası: Görev Sınıflandırması ve Teknik Detaylar

### Görev 1: Çoklu Spor Seçicili Homepage & Vercel Dağıtımı
> **Zorluk**: 🟡 **ORTA (Frontend & Yönlendirme)**  
> **Bileşen**: Frontend (`App.jsx`, `DropdownNavigation.jsx`, yeni `SportSelector.jsx`)

* **Hedef**: Sitenin doğrudan sadece MLB tahminlerini açması yerine, kullanıcıyı şık bir karşılama ekranı (Homepage) ile karşılaması veya üst barda yer alan spor seçici (dropdown veya yatay butonlar) ile **MLB** ve **Tenis** (ve gelecekte NFL/NBA) arasında hızlı geçiş yapabilmesi.
* **Teknik Plan**:
  * React tarafında bir spor durum state'i (`activeSport = 'MLB' | 'TENNIS'`) tanımlamak.
  * Seçilen spora göre ana ekran bileşenlerini dinamik render etmek veya React Router kullanarak `/mlb` ve `/tennis` rotalarını ayırmak.
  * Vercel üzerinde tek bir URL (adres) altında iki modelin de sıfır gecikmeyle çalışmasını sağlamak.
  * Mobil uyumlu, modern geçiş animasyonları eklemek.

---

### Görev 2: Tenis Tahmin Motoru & Günlük Scraper'lar
> **Zorluk**: 🔴 **ZOR (Veri Kazıma & İstatistiksel Model)**  
> **Bileşen**: Backend (yeni `tennis_engine.py`, `tennis_scraper.py`, `api.py` tenis rotaları)

* **Hedef**: ATP ve WTA tenis maçları için günlük programı, oyuncu istatistiklerini (servis kazanma %, kırılma puanları vb.) ve bahis oranlarını çekip, maç kazananı ve set handikapı tahminlerini üreten bağımsız bir tenis motoru kurmak.
* **Teknik Plan**:
  * **Veri Kaynağı**: Ücretsiz ve stabil olan tenis veri sitelerinden veya resmi ATP/WTA API'lerinden günlük maç programlarını kazıyan `tennis_scraper.py` modülü yazmak.
  * **Model**: Oyuncuların yüzey (toprak, çim, sert kort) bazlı tarihsel başarı oranlarını, son 10 maç form durumlarını ve kafa kafaya (H2H) maç geçmişlerini ağırlıklandıran bir olasılık algoritması kodlamak.
  * **Oranlar**: The Odds API üzerinden tenis maç oranlarını çekmek ve model olasılıklarıyla kıyaslayıp tenis bahis avantajlarını (edges) hesaplamak.

---

### Görev 3: Hamburger Menü Altında "Hitter Center" (Vurucu Projeksiyonları) Sayfası
> **Zorluk**: 🟡 **ORTA (Arayüz & API Entegrasyonu)**  
> **Bileşen**: Frontend (`HitterCenter.jsx`), Backend (`api.py` hitter rotaları)

* **Hedef**: Hamburger menüye "Hitter Center" adında yeni bir sayfa eklemek. Bu sayfa içinde 3 farklı alt sekme (`BvP` | `Last 7 Days` | `Today's Projections`) sunarak vurucu analizlerini tek merkezde toplamak.
* **Teknik Plan**:
  * React tarafında `HitterCenter.jsx` adında zengin bir tablo bileşeni geliştirmek.
  * Üç sekmeli yatay navigasyon çubuğu tasarlamak.
  * Backend tarafında bu tabloları besleyecek `/hitter/bvp`, `/hitter/stats-7d` ve `/hitter/projections` rotalarını açmak.

---

### Görev 4: BvP (Batter vs Pitcher) Dinamik Filtre Slider'ları
> **Zorluk**: 🟢 **KOLAY (Arayüz Mantığı)**  
> **Bileşen**: Frontend (`HitterCenter.jsx` BvP sekmesi)

* **Hedef**: Rotowire'ın sunduğu parametrik filtreleri (Minimum At-Bats, Minimum AVG, Minimum OPS vb.) kullanıcıların kendi istediği gibi ayarlayabileceği dinamik arayüz kontrolleri (slider'lar veya sayı alanları) eklemek.
* **Teknik Plan**:
  * Tablonun üzerine `Min AB`, `Min AVG`, `Min OPS` için React slider state'leri yerleştirmek.
  * Kullanıcı slider'ı oynattığında frontend tarafındaki veri dizisini (array) anlık olarak süzmek (client-side filtering). Bu sayede sayfa yenilenmeden, saniyeler içinde binlerce satır arasından sadece hedeflenen vurucuların listelenmesini sağlamak.

---

### Görev 5: FantasyPros CSV Yükleme Admin Paneli (Admin Portal)
> **Zorluk**: 🟡 **ORTA (Dosya İşleme & Güvenlik)**  
> **Bileşen**: Backend (`csv_uploader.py`, admin API rotaları), Frontend (`AdminPortal.jsx`)

* **Hedef**: FantasyPros gibi Cloudflare korumalı ve kazınması zor sitelerin verilerini Tyler'ın manuel indirip sitemize tek tıkla yükleyebileceği şık ve güvenli bir admin yükleme ekranı tasarlamak.
* **Teknik Plan**:
  * `/admin/upload-csv` adında dosya kabul eden bir FastAPI POST rotası yazmak.
  * Python `pandas` kütüphanesi kullanarak FantasyPros'tan indirilen CSV şablonlarını parse etmek ve backend veritabanına (`hitters_7d.json` vb.) kaydetmek.
  * Admin ekranı için sürükle-bırak (Drag and Drop) özellikli, dosya yükleme ilerlemesini gösteren şık bir UI tasarlamak. Tyler'a özel basit bir şifre koruması (Admin Auth) eklemek.

---

### Görev 6: Fantasy Info Central (FIC) Hit & HR Tahminleri Scraper'ı
> **Zorluk**: 🟡 **ORTA (Veri Kazıma & Entegrasyon)**  
> **Bileşen**: Backend (`fic_scraper.py`, günlük entegrasyon)

* **Hedef**: Tyler'ın çok beğendiği `fantasyinfocentral.com` adresindeki günlük Hit ve HR (Home Run) olasılık tahminlerini otomatik olarak kazıyıp sitemizdeki "Hitter Center" sekmesinde listelemek.
* **Teknik Plan**:
  * Yaptığımız ön araştırmada sitenin tabloları dinamik Javascript veya iframe yerine **sunucu tarafında düzgün HTML** ile bastığını doğruladık.
  * Python `BeautifulSoup` veya `lxml` kütüphanelerini kullanarak `/betting/mlb/hit-predictions` ve `/betting/mlb/hr-predictions` sayfalarını günlük olarak tarayan botu kodlamak.
  * Çekilen oyuncu adlarını ve tahmin yüzdelerini (örneğin %78 Hit olasılığı) alıp sitemizdeki BvP/Hit projeksiyon kartlarında bir sütun veya rozet olarak göstermek.

---

### Görev 7: VIP Telegram Alarm Botu (Telegram Notification Bot)
> **Zorluk**: 🔴 **ZOR (Mesajlaşma Kuyrukları & Bot API Entegrasyonu)**  
> **Bileşen**: Backend (`telegram_bot.py`), Veri Takip Servisi

* **Hedef**: Modelin günlük tahminleri tamamlandığında, onaylanmış kadrolar (official lineups) girildiğinde veya günün en yüksek avantaja (75%+) sahip premium bahis edges (Moneyline, NRFI veya Pitcher Props) yakalandığında VIP Telegram kanalına otomatik olarak görsel bahis kuponu formatında bildirim göndermek.
* **Teknik Plan**:
  * Telegram Bot API entegrasyonu için backend tarafında bağımsız bir bot modülü oluşturmak.
  * **Alarm Tetikleyicileri (Triggers)**:
    1. Günlük tahminler sabah ilk kez hesaplandığında (Günün en iyi 3 Edge'i).
    2. Maç öncesi resmi kadrolar açıklandığında ve model bu yeni kadroyla tahmini güncelleyip büyük bir avantaj farkı bulduğunda.
    3. Atıcı prop oranlarında (K / IP) Poisson modeline göre %8+ sapma tespit edildiğinde.
  * Mesajları sade metin yerine parlayan emojiler, kalın başlıklar ve temiz bir hizalamayla (HTML/Markdown parse modu kullanarak) okunması son derece keyifli bir "Bahis Paylaşım Kartı" formatında tasarlamak.

---

## 🩺 Sitenin Röntgeni: Teknik Borçlar ve İyileştirme Fırsatları

Mevcut MLB Predictor projesi hızlıca prototip üretmek ve stabil çalışmak için harika bir şekilde tasarlanmış olsa da, büyüyen veri hacmi ve Tyler'ın sürekli eklenen yeni spor talepleri karşısında **mimari bazı kısıtlamalara** sahiptir. Projenin uzun vadeli sağlığı için şu iyileştirmelerin yapılması gerekmektedir:

### 1. JSON Tabanlı "Yapay Veritabanı" Problemi (Database Bottleneck)
*   **Mevcut Durum**: Backend; `pitcher_stats.json`, `live_odds.json`, `live_weather.json` ve günlük `predictions_YYYY-MM-DD.json` gibi dosyaları disk üzerinde JSON olarak okuyup yazıyor.
*   **Risk**: Aynı anda birden fazla istek geldiğinde (Concurrency), veri kazıcı çalışırken kullanıcının siteyi yenilemesi durumunda dosya kilitlenmesi (File Locking), yarış durumları (Race Conditions) veya dosyanın bozulması (Corrupted JSON) riski vardır. Ayrıca binlerce oyuncunun verisini belleğe yüklemek yavaştır.
*   **Röntgen Çözümü**: Projenin veri katmanının **PostgreSQL** (canlı ortam için) veya en azından **SQLite** (hafif ve yerel bir SQL veritabanı) ile değiştirilmesi gerekir. SQLAlchemy ORM kullanılarak tüm oyuncu istatistikleri ve geçmiş tahminler ilişkisel veritabanında tutulmalıdır.

### 2. Loglama ve Hata İzleme Sisteminin Eksikliği (No Production Logging)
*   **Mevcut Durum**: Backend içerisindeki hatalar ve süreçler sadece `print()` komutlarıyla konsola yazılıyor. Docker konteyneri kapandığında veya sunucu yeniden başladığında tüm geçmiş hata izleri kayboluyor. Canlıda bir api isteği çöktüğünde sebebini bulmak samanlıkta iğne aramaya benziyor.
*   **Röntgen Çözümü**: Python standart `logging` kütüphanesine geçilerek hatalar günlük log dosyalarına yazılmalı ve dönen hataları anlık olarak takip etmek için ücretsiz bir **Sentry** entegrasyonu yapılmalıdır.

### 3. Görev Yönetimi ve Zamanlayıcı Eksikliği (Job Scheduling)
*   **Mevcut Durum**: Veri kazıma işlemleri muhtemelen işletim sistemi seviyesinde manuel cron'lar veya dışarıdan gelen tetiklemelerle çalışıyor. Kazıcı çöktüğünde otomatik yeniden deneme (retry) veya hata bildirimi gönderme mekanizması yok.
*   **Röntgen Çözümü**: FastAPI içine entegre çalışan asenkron bir görev zamanlayıcı (**APScheduler**) veya daha profesyonel bir kuyruk sistemi (**Celery + Redis**) kurularak veri kazıma, veri doğrulama ve Telegram bot gönderimleri izlenebilir, kuyruğa alınabilir görevler haline getirilmelidir.

### 4. API Güvenliği ve CORS Zafiyetleri (API Security)
*   **Mevcut Durum**: Backend API uçları tamamen açık durumdadır. Herhangi bir kişi sitenin API adresini tarayıcısına yazarak tüm değerli tahmin verilerini, model çıktılarımızı ve kazınmış odds verilerini doğrudan çekebilir (Scrape edebilir). Ayrıca CORS ayarlarında yerel adresler doğrudan izinli olsa da api seviyesinde bir sınırlandırma yoktur.
*   **Röntgen Çözümü**:
    *   API uçları için bir **API Key** veya JWT tabanlı **üye/istemci doğrulama** (Auth) mekanizması eklemek.
    *   Sadece kendi domain adresimizden gelen isteklere izin verecek CORS sıkılaştırması yapmak.
    *   IP başına istek limiti koyan bir **Rate-Limiting** (FastAPI-Limiter / Slowapi) eklemek.

### 5. Frontend State Management ve Veri Önbellekleme (React Query Caching)
*   **Mevcut Durum**: React tarafında veriler standart `fetch`/`axios` ile çekilip doğrudan local state'lere yazılıyor. Kullanıcı sekmeler arasında her geçiş yaptığında veya sayfayı her yenilediğinde API'ye tekrar tekrar istek gidiyor. Bu durum sunucuyu yoruyor ve kullanıcı deneyimini (yüklenme gecikmeleri) olumsuz etkiliyor.
*   **Röntgen Çözümü**: Frontend'de **TanStack Query (React Query)** entegrasyonu yapılmalıdır. Bu sayede çekilen veriler istemci tarafında akıllıca önbelleğe alınır, kullanıcı sekmeler arasında gezinirken anında veri gelir ve arka planda sessizce veri güncelliği kontrol edilir (Stale-While-Revalidate).

### 6. Test Altyapısının Zayıflığı (Test Coverage)
*   **Mevcut Durum**: Sadece `test_pitcher_k_model.py` gibi birkaç temel birim testi bulunuyor.
*   **Röntgen Çözümü**: Tahmin motorunun girdilerini ve çıktılarını doğrulayan entegrasyon testleri (Integration Tests) yazılmalı ve kod GitHub'a her yüklendiğinde otomatik olarak testleri çalıştıran bir **CI/CD pipeline (GitHub Actions)** kurulmalıdır.

---

## 📈 Milestone 5 & 6 Yol Haritası Değerlendirmesi

| Görev / İyileştirme | Bileşen | Zorluk | Tahmini Süre | Öncelik |
|---|---|---|---|---|
| **M5-G1: Spor Seçici Arayüzü & Homepage** | Frontend | 🟡 Orta | 2 Gün | YÜKSEK |
| **M5-G2: Tenis Tahmin Motoru & Scraper** | Backend | 🔴 Zor | 5 Gün | YÜKSEK |
| **M5-G3: Hamburger Menü: Hitter Center** | Frontend | 🟡 Orta | 3 Gün | ORTA |
| **M5-G4: BvP Dinamik Arayüz Slider'ları** | Frontend | 🟢 Kolay | 1 Gün | ORTA |
| **M5-G5: FantasyPros CSV Yükleme Paneli** | Backend/UI | 🟡 Orta | 2 Gün | ORTA |
| **M5-G6: FIC Hit & HR Scraper** | Backend | 🟡 Orta | 2 Gün | ORTA |
| **M5-G7: VIP Telegram Alarm Botu** | Backend | 🔴 Zor | 4 Gün | DÜŞÜK (İsteğe Bağlı) |
| **Röntgen-1: SQLite / PostgreSQL Geçişi** | Backend | 🔴 Zor | 4 Gün | UZUN VADE |
| **Röntgen-4: API Güvenliği & Rate-Limiting** | Backend | 🟡 Orta | 2 Gün | UZUN VADE |

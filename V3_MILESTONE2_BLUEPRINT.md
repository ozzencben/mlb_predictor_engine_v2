# MLB Tahmin Motoru - V1 Stabilizasyon Onayı ve V3 (Milestone 2) Mimari Geçiş Planı

*Hazırlayan: Senior Full-Stack & AI Architect*

---

## 1. Veri Sözleşmesi (Contract) Doğrulaması: BİRİNCİ SINIF 🛡️

Backend'in Pydantic v2 zırhından geçerek ürettiği zengin JSON payload (özellikle `is_fallback` ve `model_anomalies`), frontend tarafında **tam performanslı ve eksiksiz** bir şekilde karşılanmaktadır. 

`MatchupCard.jsx` içerisindeki özel `arePropsEqual` mantığı sayesinde, React bu derin objeleri seri hale getirip (deep comparison) karşılaştırıyor. Bu mimari, ağır verinin arayüzde "DOM Thrashing" yaratmasını engellerken, uyarı rozetlerinin ve fallback metinlerinin anında ve hatasız render edilmesini garanti altına almıştır. 

**Durum:** V1 Veri Sözleşmesi ve performans metrikleri %100 stabilize edilmiştir.

---

## 2. Milestone 2 (V3) Mimari Geçiş Planı (Blueprint)

V3 fazı, projeyi statik bir analiz aracından **"Canlı, Yapay Zeka Destekli ve Yüksek Frekanslı Bir Tahmin Motoruna"** dönüştürecektir. İşte adım adım modül ve klasör bazlı entegrasyon rotası:

### FAZ 1: Veri Derinliği ve AI Zekası (Backend Odaklı)
İlk adımda, tahmin gücünü artıracak verileri asenkron olarak toplayıp AI ile yorumlatacağız.

#### A. `oddlyspecificstats.com` NRFI/YRFI Serileri (Scraper Entegrasyonu)
*   **Yeni Dosya:** `backend/app/services/scrapers/oddlyspecific_scraper.py`
    *   *İşlev:* `httpx` ve `BeautifulSoup` kullanarak güncel seri/streak verilerini asenkron kazıyacak.
*   **Güncellenecek Dosyalar:** `backend/app/models/schemas.py` ve `backend/app/services/mlb_unified_engine.py`
    *   *İşlev:* Pydantic şemalarına `nrfi_streak` eklenecek ve `MLBUnifiedEngine` bu veriyi `NRFI.confidence` yüzdesini (+/-) kalibre etmek için bir çarpan (modifier) olarak kullanacak.

#### B. Gemini AI "Betting Insight" Üretimi
*   **Yeni Dosya:** `backend/app/services/gemini_service.py`
    *   *İşlev:* Hesaplanmış maç JSON'ını (oranlar, hava durumu, fallback atıcı uyarıları) bir prompt bağlamı olarak Gemini'a sunup, 2-3 cümlelik "Yatırım Değeri / Edge" özeti üretecek.
*   **Yeni Endpoint:** `backend/app/api/v1/api.py` içerisine `/predictions/{game_id}/insight` eklenecek. 
    *   *Mimari Karar:* AI üretimi maliyetli ve yavaş olduğundan, bu veri ana payload ile değil, frontend'den talep edildiğinde (Lazy Loading) üretilecek.

---

### FAZ 2: Yüksek Frekanslı Veri Altyapısı (Backend -> Frontend Köprüsü)
Gerçek zamanlı maç verisinin sisteme akıtılması.

#### C. FastAPI WebSockets ile Canlı Skor Akışı
*   **Yeni Dosya:** `backend/app/api/v1/websockets.py` 
    *   *İşlev:* WebSocket Connection Manager olarak görev yapacak. İstemcileri yönetecek ve yayın (broadcast) yapacak.
*   **Yeni Dosya:** `backend/app/services/live_score_ticker.py`
    *   *İşlev:* `asyncio` arka plan görevi olarak çalışıp her 5-10 saniyede bir canlı skorları çekecek ve aktif WebSocket istemcilerine `{"type": "SCORE_UPDATE", "payload": {...}}` formatında diff (fark) paketleri yayınlayacak.

---

### FAZ 3: State Optimizasyonu ve Dinamik UI (Frontend Odaklı)
Backend'den akan sürekli veriyi, React render'ını boğmadan yöneteceğimiz katman.

#### D. Zustand Global State Manager
*   **Yeni Dosya:** `frontend/src/store/useGameStore.js`
    *   *İşlev:* `App.jsx`'teki mevcut `useState/usePredictions` yapısı değiştirilecek. Zustand; uygulamanın ilk yüklemesini (Axios GET) yapacak, ardından WebSocket'e bağlanacak. Gelen canlı skorları, tüm listeyi değil, **sadece ilgili maçın objesini mutate ederek** güncelleyecek.
*   **Güncellenecek Dosya:** `frontend/src/App.jsx`
    *   *İşlev:* Yalnızca Zustand store'unu okuyacak bir "Routing Shell" bileşenine dönüştürülecek.

#### E. AI ve Canlı UI Bileşenleri
*   **Yeni Dosya:** `frontend/src/components/GeminiInsightPanel.jsx`
    *   *İşlev:* Kullanıcı `MatchupCard`'ı genişlettiğinde (expand), ilgili AI analizini backend'den çekecek ve UI'da animasyonlu bir daktilo efektiyle yazdıracak.
*   **Güncellenecek Dosya:** `frontend/src/components/MatchupCard.jsx`
    *   *İşlev:* `React.memo` entegrasyonu tamamlandı; Zustand'dan gelen canlı skor proplarını aldığında, diğer kartları etkilemeden sadece kendi içindeki `LIVE` bayrağını ve skor board'unu saniyede bir titreşimsiz olarak güncelleyecek.

---

### 🚀 Mimari Bağımlılık ve Yürütme Sırası (Execution Plan)

1.  **Veri Toplama:** Önce `oddlyspecific_scraper.py` yazılır ve Pydantic şemaları genişletilir (Bağımlılık Yok).
2.  **AI Katmanı:** Gemini servis ve endpoint'i oluşturulur (Bağımlılık Yok).
3.  **Gerçek Zamanlı İletişim:** FastAPI WebSocket Manager ve background task ayağa kaldırılır.
4.  **State Değişimi:** Frontend tarafında `useGameStore.js` (Zustand) yazılarak WebSocket dinlemeye başlar.
5.  **UI Tüketimi:** Yeni komponentler (`GeminiInsightPanel.jsx`) ve skor güncellemeleri arayüze bağlanır.

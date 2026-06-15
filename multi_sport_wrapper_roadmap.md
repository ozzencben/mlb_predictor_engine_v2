# 🗺️ Çoklu Spor Branşları Wrapper Mimarisi ve Tenis Entegrasyon Yol Haritası (Roadmap)

Bu yol haritası, mevcut beyzbol (MLB) odaklı monolitik backend yapımızı, gelecekte eklenecek tüm spor dallarının (Tenis, Basketbol, Futbol vb.) bağımsız birer tahmin motoru olarak çalışabileceği modüler bir **"Project Wrapper"** yapısına geçirme planıdır.

---

## 🎯 Mimari Vizyon ve Temel İlke
Her spor dalının veri kaynakları (scrapers), matematiksel formülleri veya yapay zeka modelleri (ML/DL) tamamen farklıdır. 
* **MLB:** Sabermetrik formüller, Pythagorean beklentisi ve hava durumu simülasyonları odaklı bir kural motoru kullanır.
* **Tenis:** Tarihsel oyuncu istatistikleri, zemin bazlı ELO verileri ve XGBoost sınıflandırıcı modelini kullanan bir Makine Öğrenmesi (ML) motoru kullanır.

Bu iki motorun ve gelecekteki basketbol/futbol motorlarının kod, veri toplama ve API katmanlarını tamamen izole ederek; bir spor branşında geliştirme yaparken diğerlerini bozma riskini sıfıra indirmeyi hedefliyoruz.

---

## 📂 Önerilen Wrapper Klasör Düzeni

```
backend/
├── app/
│   ├── core/                  # Paylaşılan ortak ayarlar (config, DB oturumları, global logger)
│   │
│   ├── api/                   # API Giriş Noktası
│   │   ├── deps.py            # Global API bağımlılıkları
│   │   └── v1/
│   │       ├── router.py      # Spor branşlarının router'larını bağlayan ana router
│   │       ├── mlb.py         # MLB API uç noktaları
│   │       └── tennis.py      # Tenis API uç noktaları
│   │
│   ├── sports/                # Ana Wrapper Klasörü (Bütün Spor Modülleri Burada Yaşar)
│   │   ├── mlb/               # MLB Modülü (Tamamen İzole)
│   │   │   ├── models/        # mlb_model.py, nrfi_model.py, schemas.py
│   │   │   ├── services/      # pitcher_scraper.py, weather_scraper.py, unified_engine.py
│   │   │   ├── runner.py      # Günlük MLB tahmin koşturucusu (PredictionRunner)
│   │   │   └── data/          # MLB'ye özel statik veri tabanları ve dosyalar
│   │   │
│   │   └── tennis/            # Tenis Modülü (Tamamen İzole)
│   │       ├── models/        # predict.py, train_model.py, schemas.py
│   │       ├── services/      # fetch_matches.py, feature_builder.py, elo_calculator.py
│   │       ├── runner.py      # Günlük Tenis tahmin koşturucusu (TennisRunner)
│   │       └── data/          # ATP/WTA sıralamaları, player_elo.json, tennis_brain.json
│   │
│   └── shared/                # Farklı sporların ortak kullanabileceği kazıma (HTTP helper vb.) yardımcı kodları
```

---

## 🗓️ Adım Adım Entegrasyon Yol Haritası (Roadmap)

### Faz 1: Mimari Altyapının Hazırlanması (Wrapper Klasör Yapısı & Bağımlılıklar)
* **Hedef:** Spor motorlarını izole edecek klasör yapısını kurmak ve tenis kütüphanelerini backend ortamına eklemek.
1. **Modül Klasörlerinin Oluşturulması:** `backend/app/sports/mlb/` ve `backend/app/sports/tennis/` dizinlerinin hazırlanması.
2. **Bağımsız Çalışma Prensibi:** Sporlar arasında ortak bir arayüz sınıfı (örneğin bir `BaseSportRunner` miras alma yapısı) **kurulmayacaktır**. Her iki spor dalı kendi özel atıcı/atlet mantığıyla bağımsız birer alt modül olarak çalışacaktır.
3. **Paket Bağımlılıklarının Birleştirilmesi:** `backend/pyproject.toml` veya gereksinimler dosyasına tenis modelinin ihtiyaç duyduğu `xgboost`, `optuna` gibi kütüphanelerin eklenmesi ve sanal ortamın güncellenmesi.

---

### Faz 2: MLB Kodlarının Modüler Yapıya Taşınması (Refactoring MLB)
* **Hedef:** Şu anda `app/` altında dağınık olan MLB dosyalarını projenin genel işleyişini bozmadan `app/sports/mlb/` altına taşımak.
1. **Modüllerin Taşınması:**
   * `backend/app/models/` altındaki `mlb_model.py`, `nrfi_model.py`, `f5_model.py` ve `schemas.py` dosyaları `backend/app/sports/mlb/models/` altına taşınacak.
   * `backend/app/services/` altındaki `pitcher_scraper.py`, `weather_scraper.py`, `mlb_unified_engine.py` vb. dosyalar `backend/app/sports/mlb/services/` altına taşınacak.
   * [prediction_runner.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/services/prediction_runner.py) dosyası `backend/app/sports/mlb/runner.py` olarak taşınacak ve kendi iç mantığıyla bağımsız bir şekilde çalışmaya devam edecektir.
2. **Import ve Bağımlılıkların Güncellenmesi:** Taşınan tüm MLB dosyalarındaki import yolları absolute import yapısına geçirilecek.
3. **API Router Ayrıştırması:** [api.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/api/v1/api.py) dosyasındaki MLB yönlendirmeleri `backend/app/api/v1/mlb.py` dosyasına taşınacak.

---

### Faz 3: Tenis Modelinin Entegre Edilmesi (Integrating Tennis)
* **Hedef:** Bağımsız duran `tennis_modal` projesini `app/sports/tennis/` modülü olarak backend'e kazandırmak.
1. **Dosya Transferleri:**
   * [predict.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/tennis_modal/app/models/predict.py) ve [train_model.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/tennis_modal/app/models/train_model.py) -> `backend/app/sports/tennis/models/` altına.
   * [feature_builder.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/tennis_modal/app/scripts/feature_builder.py), `fetch_matches.py` vb. scriptler -> `backend/app/sports/tennis/services/` altına.
   * ELO ve ATP/WTA sıralama JSON dosyaları ile eğitilmiş XGBoost modeli `tennis_brain.json` -> `backend/app/sports/tennis/data/` altına taşınacak.
2. **Kodların FastAPI/Async Yapısına Uyarlanması:**
   * Tenis veri kazıma (scraping) ve tahmin scriptlerinde bulunan `sys.path.append` gibi kodların temizlenmesi ve relative importların backend yapısına uyarlanması.
   * `predict.py` içindeki konsola çıktı veren tahmin fonksiyonunun revize edilerek, veri yapılarını (tahmin yüzdeleri, oyuncu elo ve momentum detayları) API için nesne formatında geri dönmesi.
3. **TennisRunner Geliştirilmesi:**
   * Tenis için günlük programı kontrol eden, oyuncu veri tabanını güncelleyen ve tahmin üreten `runner.py` (TennisRunner) yazılacak.

---

### Faz 4: API Katmanının Modüler Olarak Tasarlanması
* **Hedef:** Ön yüzün her spor dalına ait tahminleri bağımsız ve temiz URL'lerden çekebilmesini sağlamak.
1. **Endpoints Yapılandırması:**
   * **MLB API (`backend/app/api/v1/mlb.py`):**
     * `GET /api/v1/mlb/predictions`: MLB tahminlerini döner.
     * `POST /api/v1/mlb/refresh-data`: MLB kazıcı ve motorunu çalıştırır.
   * **Tenis API (`backend/app/api/v1/tennis.py`):**
     * `GET /api/v1/tennis/predictions`: Tenis tahminlerini döner.
     * `POST /api/v1/tennis/refresh-data`: Tenis veri çekme ve tahmin motorunu çalıştırır.
2. **Ana Router Bağlantısı (`backend/app/api/v1/router.py`):**
   * Spor modüllerinin yönlendiricileri ana API router'ına dahil edilecek:
     ```python
     api_router.include_router(mlb_router, prefix="/mlb", tags=["MLB"])
     api_router.include_router(tennis_router, prefix="/tennis", tags=["Tennis"])
     ```

---

### Faz 5: Zamanlayıcı (Scheduler) ve Arka Plan Görevleri
* **Hedef:** Her spor branşının veri güncelleme sıklığını ve zamanını bağımsız yönetmek.
1. **Zamanlama Planı:**
   * **MLB:** Günde iki kez (00:00 ve 12:00 ET) çalışacak şekilde kalacak (çünkü kadrolar ve maç saatleri dinamiktir).
   * **Tenis:** Günde 1 kez gece yarısı (veya turnuva maç programları açıklandığında) çalışacak şekilde zamanlanacak (turnuva sıralamaları ve oyuncu geçmişleri çok sık değişmez).
2. **Scheduler Ayrıştırması:** Zamanlayıcı (lifespan veya scheduler.py) her spor dalının kendi `Runner` sınıfını çağıracak şekilde güncellenecek.

---

### Faz 6: Test ve DevOps (Model Eğitimi & Sürüm Kontrolü)
* **Hedef:** Sistem kararlılığını sağlamak ve modellerin performansını izlemek.
1. **Uçtan Uca Doğrulama Testi:**
   * Refactoring sonrasında MLB tahminlerinin önceki versiyonla uyuştuğunu doğrulayan regresyon testleri çalıştırılacak.
   * Tenis veri çekme sisteminin ve tahmin çıktısının doğru çalıştığını test eden entegrasyon testleri eklenecek.
2. **Model Eğitimi (Retraining) Tetikleyicisi:**
   * `train_model.py` dosyasının projenin bir parçası olarak çalışabilmesi için backend üzerinden tetiklenebilecek bir komut veya API endpoint'i (isteğe bağlı ve güvenli) eklenecek. Böylece yeni maçlar eklendikçe tenis modeli otomatik veya yarı-manuel olarak yeniden eğitilip `tennis_brain.json` güncellenebilecek.

---

## 🧐 Karar Verilen Noktalar ve Durum
* **Veri Saklama Yöntemi (Veritabanı Kararı):** Her iki spor dalı da veritabanı refactoring'i gündeme gelene kadar kendi JSON dosyaları (örn: `todays_predictions.json`, `player_elo.json`, `tennis_brain.json`) üzerinden okuma/yazma yapmaya bağımsız bir şekilde devam edecektir.
* **Oranlar (Odds) Entegrasyonu:** Tenis modeli için Odds sağlayıcısı entegrasyonu ilk aşamada gerçekleştirilmeyecektir. Model şimdilik saf istatistiksel olasılık çıktıları ile entegre edilecektir; oran analizi mimari oturduktan sonraki aşamalarda eklenecektir.

---

Bu güncellenmiş yol haritasına göre, spor dalları projenin ortak bir üst sınıfına (base class) veya çalışma yapısına zorlanmadan, tamamen kendi özel akışlarında çalışmaya devam edeceklerdir.


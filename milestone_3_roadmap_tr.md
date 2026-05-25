# Milestone 3 - Teknik Uygulama Yol Haritası ve Mimarisi (Roadmap)

MLB Tahmin Motoru modernizasyonunun **Milestone 3 (M3)** aşamasına hoş geldiniz! Bu yol haritası, Tyler'ın talep ettiği **7 Lansman Özelliğini** hayata geçirmek için gereken mimari değişiklikleri, veritabanı eşlemelerini, matematiksel formülleri ve görsel tasarımları detaylandırmaktadır.

Tüm bu özellikleri **0 TL devam eden API maliyetiyle**, yerel matematiksel/fiziksel hesaplamaları ve mevcut ücretsiz veri toplama altyapımızı kullanarak hayata geçirecek akıllı bir strateji tasarladık.

---

## 🗺️ Mimari Genel Bakış ve Servis Analizi

### 1. Yeni arka plan servislerine veya ücretli API'lere ihtiyacımız var mı?
**Hayır, yeni hiçbir üçüncü taraf ücretli servise veya API'ye ihtiyaç yoktur.** Mevcut altyapımız tüm gereksinimleri karşılamak için fazlasıyla yeterlidir:
* **Hava Durumu ve Pusulalar (M3-1)**: `WeatherScraper.py` içinde **Open-Meteo API (Ücretsiz)** üzerinden gerçek zamanlı saatlik hava durumunu (sıcaklık, rüzgar hızı, rüzgar yönü, nem) zaten çekiyoruz. Bu verileri yerel bir fiziksel balistik modeliyle işleyerek topun havada süzülme mesafesini ve skora etkisini yerel olarak hesaplayacağız.
* **Spread Olasılığı (M3-6)**: Modelin skor farkı tahminlerine ve geçmiş standart sapma değerlerine dayanan kümülatif normal dağılım eğrileri kullanılarak tamamen backend üzerinde matematiksel olarak hesaplanacaktır.
* **Takvim ve Geçmiş Veriler (M3-7)**: Herhangi bir tarih için maçları, muhtemel atıcıları ve gerçek nihai skorları çekebilen, tamamen ücretsiz ve sınırsız olan resmi **MLB StatsAPI Schedule** (`https://statsapi.mlb.com/api/v1/schedule`) servisi sorgulanarak çözülecektir.

### 2. Dosya Modülerliği ve Güncellenecek Kod Kütüphaneleri

```mermaid
graph TD
    subgraph Frontend [React Frontend]
        App[App.jsx] --> Calendar[Takvim Navigasyon Barı]
        App --> Edges[Günün En İyi Avantajları Banner'ı]
        App --> Matchup[MatchupCard.jsx]
        Matchup --> Header[Modern Başlık Tasarımı]
        Matchup --> BestAngle[En İyi Açı Rozeti]
        Matchup --> Covers[Covers Tarzı Tahmin Kutusu]
        Matchup --> Ballpark[Hava Durumu & Stadyum Widget'ı]
    end

    subgraph Backend [FastAPI Backend]
        API[api.py] --> Predictions[Tarih Bazlı Tahmin Motoru]
        Predictions --> Runner[PredictionRunner.py]
        Runner --> Weather[WeatherScraper.py]
        Runner --> Engine[mlb_unified_engine.py]
        Engine --> MLBModel[mlb_model.py]
    end
```

* **Güncellenecek Backend Dosyaları**:
  * [api.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/api/v1/api.py): `/predictions?date=YYYY-MM-DD` sorgu yollarını açmak ve geçmiş tarih önbellek (cache) yönetimini gerçekleştirmek.
  * [prediction_runner.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/services/prediction_runner.py): Herhangi bir tarih için tahminlerin dinamik olarak çalıştırılmasını desteklemek ve hava durumu faktörlerini tahmin motoruna beslemek.
  * [mlb_unified_engine.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/services/mlb_unified_engine.py): Hava durumu metriklerini skor tahminlerine enjekte etmek ve Spread Olasılığı hesaplamalarını çalıştırmak.
  * [mlb_model.py](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/backend/app/models/mlb_model.py): Balistik top taşıma mesafesi katsayılarını hesaplamak; runs, HR ve K beklentilerini ayarlamak.
* **Güncellenecek Frontend Dosyaları**:
  * [App.jsx](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/frontend/src/App.jsx): En üste kaydırılabilir Takvim Navigasyon barını eklemek, tarih bazlı veri çekmeyi tetiklemek ve Günün En İyi Avantajları (Daily Edges) Banner'ını yerleştirmek.
  * [usePredictions.js](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/frontend/src/hooks/usePredictions.js): Seçilen tarihleri dinamik olarak çekmek için isteğe bağlı bir `date` parametresi kabul etmek.
  * [MatchupCard.jsx](file:///c:/Users/ozzenc/Desktop/mlb_predictor_engine_v2/frontend/src/components/MatchupCard.jsx): Standout Headliner, En İyi Açı Rozeti, Covers Tarzı Kutu ve etkileşimli Hava Durumu Stadyum Pusulasını uygulamak.

---

## 📊 M3 Yol Haritası: Görev Sınıflandırması ve Teknik Detaylar

Tüm 7 lansman görevini **En Kolaydan (Görsel/CSS)** **En Zora (Karmaşık Matematik & Tarih Rotaları)** doğru sınıflandırdık:

---
(YAPILDI)
### Görev 1: Standout Headliner Redesign (Modern Başlık Tasarımı)
> **Zorluk**: 🟢 **KOLAY (Görsel / CSS)**  
> **Bileşen**: `MatchupCard.jsx` (Header bölümü)

* **Hedef**: Mevcut sade maç başlığı çubuğunu, her iki takım logosunu, isimlerini ve maç durumunu zarif, mobil uyumlu ve yüksek kontrastlı bir tasarımla vurgulayan şık bir banner ile değiştirmek.
* **UI/UX Geliştirmeleri**:
  * İnce metalik sınırlara sahip parlak cam morfizmi arka planı (`border-slate-700/80 bg-slate-900/60`).
  * Takımların renklerini temsil eden şık, parlayan neon çizgiler.
  * Net maç durumu göstergeleri (örn. dinamik canlı yanıp sönen yeşil ışık veya tamamlanmış maç skoru rozeti).
  * `320px` kadar dar ekranlarda bile elemanların kaymasını önleyen ve okunabilirliği koruyan mobil uyumlu ızgara (grid) yerleşimi.

---
(YAPILDI)
### Görev 2: Best Angle Indicator (En İyi Açı Rozeti)
> **Zorluk**: 🟢 **KOLAY (Veri Mantığı)**  
> **Bileşen**: `MatchupCard.jsx` & `mlb_unified_engine.py`

* **Hedef**: Bir maç için tüm bahis pazarlarını taramak, bahis bürosu oranlarına kıyasla en yüksek mutlak avantaja (edge) sahip olan seçeneği belirlemek ve kartın üzerine özel bir hedef rozeti basmak (örn. `BEST ANGLE: NRFI (%68 Güven)` veya `BEST ANGLE: Away ML (+155, %6.2 Edge)`).
* **Teknik Plan**:
  * Moneyline avantajlarını (`away_edge_pct`, `home_edge_pct`), F5 avantajlarını, Over/Under avantajlarını ve NRFI/YRFI güven seviyelerini karşılaştırın.
  * Bahis bürosuna kıyasla en yüksek pozitif avantaja sahip olan veya en yüksek matematiksel güveni veren (örn. yüksek olasılıklı NRFI) pazarı seçin.
  * Kullanıcının gözünü anında yakalamak için bu öneriyi her maç kartının sağ üst köşesindeki parlayan neon bir hedef kutusunun içinde gösterin.

---
(YAPILDI)
### Görev 3: Covers-Style Predictions Box (Covers Tarzı Tahmin Kutusu)
> **Zorluk**: 🟡 **ORTA (Mantık ve Çeviri)**  
> **Bileşen**: `MatchupCard.jsx` (Özet alanı)

* **Hedef**: Ondalık skor tahminlerinin yarattığı zihinsel yükü ortadan kaldırmak ve modelin nihai konsensüs seçimlerini profesyonel bahis sitelerinde (Covers veya Action Network gibi) kullanılan standart bahis formatında sunmak.
* **UI/UX Tasarımı**:
  * 3 sütunlu yapılandırılmış bir kutu sunun:
    1. **Moneyline Konsensüsü**: Örn., `CHC ML` (öngörülen kazanma ihtimaliyle birlikte, örn. `%58`).
    2. **Spread Seçimi**: Örn., `HOU +1.5` (öngörülen spread kapama ihtimaliyle birlikte, örn. `%64`).
    3. **Total (Over/Under)**: Örn., `OVER 8.5` (öngörülen toplam sayı beklentisiyle birlikte, örn. `9.8 Runs`).
  * Kalın kontrastlı sayılar ve renkli göstergeler kullanın (ana tercihler için Yeşil, ikincil eğilimler için Mavi).

---

(YAPILDI)
### Görev 4: Board / Daily Edges Banner (Günün En İyi Avantajları Banner'ı)
> **Zorluk**: 🟡 **ORTA (Agregasyon & Arayüz)**  
> **Bileşen**: `App.jsx` (Hero alanı)

* **Hedef**: Günün tüm maç listesini taramak ve tüm fikstür genelindeki en yüksek değerli 3 tahmini anasayfanın en üstünde yatay parıldayan bir şerit halinde vurgulamak.
* **Teknik Plan**:
  * **En İyi Moneyline Avantajı**: `max(away_edge_pct, home_edge_pct)` değerine sahip en yüksek maç.
  * **En İyi Spread Avantajı**: En yüksek spread kapama olasılığına sahip maç.
  * **En İyi Total (O/U) Avantajı**: Modelin toplam sayı tahmini ile bahis bürosunun limiti arasında en yüksek farka sahip olan maç.
  * **Arayüz**: Bunları en üstte, Tyler'ın "VIP / En İyi Seçimler" vitrini olarak hizmet veren üç yüksek kontrastlı parlayan mikro kart olarak görüntüleyin.

---

(YAPILDI)
### Görev 5: Spread Probability Formula (Spread Olasılık Formülü)
> **Zorluk**: 🟡 **ORTA (Matematik)**  
> **Bileşen**: `mlb_unified_engine.py` & `mlb_model.py`

* **Hedef**: Standart bir $\pm 1.5$ sayı spreadinin kapama olasılığını kesin matematiksel yüzde olarak hesaplayacak backend güncellemesini yapmak.
* **Matematiksel Formül**:
  * Beyzbol skor farkları yaklaşık olarak bir Normal Dağılım izler: $X \sim \mathcal{N}(\mu, \sigma^2)$ burada $\mu = \text{Ev Sahibi Skor} - \text{Deplasman Skor}$ ve modern MLB skorlama standart sapması $\sigma \approx 4.0$ runs'dır.
  * Ev sahibinin 2 veya daha fazla sayı farkla kazanma (sayı handikapı -1.5 kapama) olasılığı:
    $$P(X \ge 1.5) = 1 - \Phi\left(\frac{1.5 - \mu}{4.0}\right)$$
  * Ev sahibinin +1.5 spread kapama (1 sayıyla kaybetme, berabere bitme veya kazanma) olasılığı:
    $$P(X \ge -1.5) = 1 - \Phi\left(\frac{-1.5 - \mu}{4.0}\right)$$
  * Bu formülü Python'un `math.erf` fonksiyonunu kullanarak **Kümülatif Dağılım Fonksiyonunu** ($\Phi$) ağır paketlere (scipy vb.) ihtiyaç duymadan hesaplayacağız:
    ```python
    def standard_normal_cdf(x: float) -> float:
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    ```
  * Hesaplanan yüzdeler (örn. `%62.5`) API verisiyle taşınacak ve arayüzde CountUp ile canlandırılacaktır.
---

(YAPILDI)
### Görev 6: Weather Impact Engine & UI (Hava Durumu Etki Motoru)
> **Zorluk**: 🔴 **ZOR (Fizik Modeli & Grafikler)**  
> **Bileşen**: `mlb_model.py` (Fizik formülleri) & `MatchupCard.jsx` (Stadyum Arayüzü)

* **Hedef**: Ballistik top süzülme mesafesi fizik modelini kurarak, stadyum rakımı, sıcaklık, nem ve rüzgar yönü vektörlerine göre runs, HR ve K beklentilerini **0 TL API maliyetiyle** yerel olarak modifiye etmek.
* **Fizik Formülleri**:
  * **Hava Yoğunluğu ($\rho$) Etkisi**: Hava yoğunluğu irtifa, yüksek sıcaklık ve yüksek nem ile azalır; bu da top üzerindeki aerodinamik sürtünmeyi (drag) azaltır.
    * Temel Havada Süzülme Mesafesi Katsayısı:
      $$\text{Süzülme}_{\text{temel}} = (\text{Temp} - 72) \cdot 0.35 + (\text{Stadyum Rakımı}) \cdot 0.005 - (\text{Nem} - 50) \cdot 0.05$$
  * **Rüzgar Vektörünün İzdüşümü**: Rüzgar hızını ($W$), rüzgar yönü ($\theta_w$) ve stadyumun merkez saha açısına ($\theta_c$) göre izdüşürün:
    * Karşı Rüzgar / Arka Rüzgar Bileşeni:
      $$W_{\text{out}} = W \cdot \cos(\theta_w - \theta_c)$$
    * Yan Rüzgar Bileşeni:
      $$W_{\text{cross}} = W \cdot \sin(\theta_w - \theta_c)$$
  * **Birleşik Havada Süzülme Mesafesi Değişimi**:
      $$\Delta \text{Mesafe (ft)} = \text{Süzülme}_{\text{temel}} + W_{\text{out}} \cdot 1.8$$
  * **Skor Çarpanları**:
    * Runs Çarpanı: $1.0 + (\Delta \text{Mesafe}) \cdot 0.003$
    * HR Çarpanı: $1.0 + (\Delta \text{Mesafe}) \cdot 0.007$
    * Strikeout Çarpanı: Yüksek rüzgar ve soğuk parmak tutuşunu zorlaştırarak spin oranını azaltır; nem breaking ball hareketini sönümler.
* **Premium UI**:
  * Rüzgar vektörünün beyzbol sahasına nasıl çarptığını gösteren etkileşimli bir **Stadyum Pusulası (SVG)**.
  * Dijital telemetri ekranı:
    * `⚾ Top Taşıma: +14.2 ft (Güçlü Arka Rüzgar)`
    * `🔥 Home Runs: +%11 HR Olasılığı`
    * `📉 Atıcı Tutuşu: -%4 K (Yüksek Nem)`

---

### Görev 7: Historical Match Results & Calendar Navigation (Tarihsel Sonuçlar ve Takvim)
> **Zorluk**: 🔴 **ZOR (Karmaşık Rotalar, Önbellekleme & StatsAPI Entegrasyonu)**  
> **Bileşen**: `api.py`, `prediction_runner.py`, `App.jsx`

* **Hedef**: Anasayfanın en üstünde, kullanıcıların Dün, Bugün veya Yarın'ı seçmelerine olanak tanıyan, dünkü skor sonuçlarını ve yarının projeksiyonlarını anında gösteren yatay bir takvim barı oluşturmak.
* **Teknik & Önbellek Planı**:
  * Backend API rotasını `/predictions?date=YYYY-MM-DD` parametresini destekleyecek şekilde genişletmek.
  * Geçmiş bir tarih (Dün) istendiğinde:
    1. `backend/data` klasöründe `predictions_YYYY-MM-DD.json` dosyasını arayın.
    2. Eğer **önbellekte yoksa**:
       * StatsAPI schedule servisini o tarih için çağırın: `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=YYYY-MM-DD&hydrate=probablePitcher`.
       * Bu servis hem dünkü maçları, atıcıları hem de **gerçek tamamlanmış final skorlarını** (örn. CHC 5, HOU 2) dönecektir.
       * Matematik motorumuzu (`MLBUnifiedEngine`) bu maçlar üzerinde çalıştırıp tahminleri anında hesaplayın ($<100\text{ms}$ sürer).
       * Tahminlerimiz ile StatsAPI'den gelen gerçek skorları eşleştirin.
       * Bir sonraki yüklemede anında açılması için `predictions_YYYY-MM-DD.json` olarak diske kaydedin.
  * Gelecek bir tarih (Yarın) istendiğinde: Fikstürü çekin, tohumlu bahis oranları ve matematik motoruyla tahminleri üretip diske kaydedin.
* **Arayüz Özellikleri**:
  * Yatay takvim şeridi: `[ DÜN (24 Mayıs) ]  [ BUGÜN (25 Mayıs) ]  [ YARIN (26 Mısıs) ]`.
  * Dünün tamamlanan maçları için **Model vs Gerçek Sonuç Karşılaştırma rozetleri**:
    * Tahmin: `4.5 - 3.2` | Gerçek Skor: `5 - 3` ➔ Rozet: `✅ Tahmini Kazanan İsabetli!`
    * Tahmin: `OVER 7.5` | Gerçek Toplam: `8 Runs` ➔ Rozet: `✅ Toplam Sayı (Over) İsabetli!`
    * Bu, modelin başarısını ve doğruluğunu görsel olarak kanıtlayacak en büyük **güven/prestij unsuru** olacaktır.

---

## 🏁 Uygulama ve Faz Planı

Onayınızın ardından geliştirmeyi aşamalı olarak başlatacağız:
1. **Aşama 1: Backend Fizik & Matematik Entegrasyonu** (Görev 5, 6). Balistik rüzgar taşıma mesafesi ve normal CDF spread olasılık kodlamalarının yazılması.
2. **Aşama 2: Tarih Rotaları ve Geçmiş Önbellek** (Görev 7). `/predictions?date=` ve StatsAPI nihai maç sonuç eşleştiricilerinin yazılması.
3. **Aşama 3: Arayüz Düzeni ve Tasarımlar** (Görev 1, 2, 3, 4). Günün En İyi Seçimleri banner'ı, headliner, Covers tahmin kutuları ve en iyi açı rozetlerinin görselleştirilmesi.
4. **Aşama 4: Stadyum SVG Pusulası** (Görev 1). Rüzgar telemetrisi ve SVG beyzbol diamond çiziminin etkileşimli hale getirilmesi.
5. **Aşama 5: Yerel Test ve Üretim Raporu**. Uygulamanın derlenmesi, yerel olarak test edilip onayınıza sunulması.

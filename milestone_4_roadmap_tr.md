# MLB Predictor Engine - Milestone 4 & 5 Güncellenmiş Yol Haritası ve Mimarisi

Tyler ile yapılan görüşmeler doğrultusunda, geliştirme süreci ve kapsamı yeniden aşamalandırılmıştır. Sitedeki tüm görsel, arayüz, balistik ve model iyileştirme özellikleri Milestone 4 kapsamına dahil edilmiş; Telegram/SMS bildirim botları ve canlı edge uyarıları ise bir sonraki aşama (Milestone 5) olarak ayrılmıştır.

---

## 🏁 M4: Interactive Dashboard & Core Model Engine (Arayüz, Görsellik ve Model Güncellemeleri)
**Önerilen Bütçe:** $200  
**Tahmini Süre:** 7-9 Gün  
**Odak:** Navigasyon Menüsü, Kompakt Akordeon Listeler, Kapanabilir Recharts Grafikleri, DraftKings -1 Alternatif Spreadi, Atıcı Projeksiyon Excel Entegrasyonu ve Model Güçlendirmesi.

### Görev 1: Header Dropdown/Hamburger Navigasyon Menüsü
* **Zorluk**: 🟡 **ORTA (UI/UX Tasarımı)**
* **Hedef**: Yatay sekmeleri kaldırıp hamburger menü navigasyonuna geçmek; Daily Games, NRFI Model, Weather Cards, Edge Board, Snapshot ve Pitcher Projections sekmelerini bu menüye bağlamak.

### Görev 2: Kompakt & Açılabilir Hava Durumu Listesi (Weather Rows)
* **Zorluk**: 🟡 **ORTA (CSS Animasyonu & Akordeon)**
* **Hedef**: `weathermlb.com` tarzı ince satır hava durumu listesi oluşturmak. Satıra tıklandığında açılan alt kartta ballpark ve pitcher HR/Strikeout istatistiklerini listelemek.

### Görev 3: Kapanabilir Ballpark Projections Grafiği
* **Zorluk**: 🟡 **ORTA (Recharts & Accordion UI)**
* **Hedef**: Günün stadyum projeksiyonlarını kıyaslayan interaktif Recharts sütun grafiğini ana sayfanın en üstünde açılıp kapanan (collapsible) bir panele yerleştirmek.

### Görev 4: DraftKings -1 Spread Odds & Edge Entegrasyonu
* **Zorluk**: 🟡 **ORTA (Matematiksel CDF Olasılığı)**
* **Hedef**: DraftKings'in sunduğu `-1` spread seçeneği için normal dağılım iade (push) ihtimalini de modele katarak avantaj (edge) hesaplamasını siteye eklemek.

### Görev 5: "Stay Away" Badges & Weather Risk Integration
* **Zorluk**: 🟢 **KOLAY (Görsel Uyarılar)**
* **Hedef**: Hava durumu riski yüksek (şiddetli yağmur veya rüzgar) olan maçlara kırmızı uyarı rozetleri eklemek.

### Görev 6: Pitcher Projections Model Entegrasyonu (Atıcı Strikeout & Outs Modeli)
* **Zorluk**: 🔴 **ZOR (Excel-to-Python & Veri Eşleme)**
* **Hedef**: Tyler'ın ilettiği SharePoint Excel modelindeki Strikeout ve Toplam Out tahmin algoritmalarını çözüp Python backend'e entegre etmek. Günlük atıcı geçmişlerini StatsAPI'den çekerek bu modeli çalıştırmak ve arayüzde listelemek.
* **Excel Kaynağı**: [SharePoint Excel Model Link](https://mtwky1-my.sharepoint.com/:x:/g/personal/tfarmer_mtwky_org/IQCjoy-pkDGZT60RtX_7eqpkAWfcQkx7a-igav_JoFgTrpI?e=KKW09H)

### Görev 7: Model İyileştirmeleri (More Stats Integration)
* **Zorluk**: 🟡 **ORTA (Veri Kazıma & Ağırlık Güncellemesi)**
* **Hedef**: Ana modelin tahmin doğruluğunu artırmak için yeni istatistiksel katmanlar eklemek:
  * Atıcı el tercihine göre vuruş yüzdeleri (LHP/RHP splits).
  * Bullpen (Rölyef atıcıları) güç ve ERA sıralamaları.
  * Home Field Advantage (HFA) stadyum bazlı ağırlık katsayıları.

---

## 🏁 M5: Live Alerts & Notification Bot (Canlı Uyarılar ve Bildirim Modülü)
**Önerilen Bütçe:** Sonra Değerlendirilecek  
**Odak:** Telegram Bot API Entegrasyonu, Twilio SMS Gateway, Kullanıcı Tercihleri Yönetimi ve Canlı Maç İçi Live Edge Bildirimleri.

### Görev 1: Telegram & SMS Bildirim Altyapısı
* **Hedef**: Telegram ve Twilio üzerinden, kullanıcıların kendi tercihlerine göre filtreleyebilecekleri günlük otomatik VIP pick bildirimlerini göndermek.

### Görev 2: Canlı Maç İçi Edge Bildirimleri (Live Edge Mid-Game Alerts)
* **Hedef**: Canlı maç skorlarını takip ederek simülasyonda "Live Edge" avantajı doğduğunda aboneye anlık bildirim iletmek.

# Milestone 5 - Çoklu Spor Portalı & Arayüz Mimari Yol Haritası (UI/UX Planlama Raporu)

Bu rapor, Legends Sports platformunu tek sporlu (sadece MLB) bir tahmin sayfasından, gelecekte eklenecek yeni spor dallarına (Tenis, Basketbol, Futbol vb.) tam uyumlu, modern navigasyon yapısına sahip profesyonel bir **Çoklu Spor Tahmin Portalı**'na dönüştürme planını sunar.

Koda geçiş yapılmadan önce arayüz mimarisinin, navigasyon hiyerarşisinin ve ölçeklenebilirlik altyapısının planlanması hedeflenmiştir.

---

## 🗺️ 1. Genel Mimari Vizyon: Tek Sayfadan Portala Geçiş

Mevcut MLB tahmin sayfamız tek bir amaca hizmet eden şık bir "landing page" görünümündedir. Siteyi gerçek bir spor portalına dönüştürmek için **3 Katmanlı Hiyerarşi** kuracağız:

```mermaid
graph TD
    subgraph GlobalLayout [Global Düzen]
        Navbar[Global Üst Navigasyon Barı] --> Sidebar[Sol Menü / Drawer Navigation]
    end

    subgraph Views [Sayfa Görünümleri]
        Sidebar --> HomeView[Central Hub / Karşılama Sayfası]
        Sidebar --> MLBView[MLB Tahmin Merkezi]
        Sidebar --> TennisView[Tenis Tahmin Merkezi]
        Sidebar --> BasketView[NBA/NCAA - BETA]
        Sidebar --> SoccerView[Futbol - COMING SOON]
    end

    subgraph InfoModals [Bilgi & Güvenlik Katmanı]
        Navbar --> About[Hakkımızda Modalı / Sayfası]
        Navbar --> Contact[İletişim Modalı / Sayfası]
        Navbar --> Disclaimer[Sorumluluk Reddi & Şartlar]
    end
```

---

## 🧭 2. Navigasyon ve Spor Seçim Arayüzü Tasarımı

Gelecekte sisteme 4-5 farklı spor dalı ekleneceği için üst barda yatay sekmeler kullanmak mobil ekranlarda taşmalara neden olacaktır. Bu yüzden aşağıdaki navigasyon sistemini uygulayacağız:

### A. Global Header & Üst Navigasyon Barı (Global Navbar)
Sitede sürekli sabit kalacak (Sticky) üst bar şu bileşenleri içerecektir:
1.  **Sol Bölüm**: Marka Logosu (Legends Sports) ve tıklanabilir "Home" yönlendirmesi.
2.  **Orta Bölüm (Masaüstü)**: Ana sekmeler (Home, MLB, Tennis, NBA `BETA`).
3.  **Sağ Bölüm**: 
    *   **Canlı Sistem Durumu (System Status)**: API bağlantısını ve son veri güncelleme zamanını gösteren minik neon nokta.
    *   **Bilgi Menüsü (Info Menu)**: "About" (Hakkımızda), "Contact" (İletişim) ve "Disclaimers" (Yasal Uyarı) alanlarına hızlı erişim sağlayan bir buton grubu.
    *   **Mobil Menü (Hamburger)**: Mobil cihazlarda tüm bu sekmeleri ve bilgi sayfalarını dikey açılır bir çekmecede (Drawer) toplayacak buton.

### B. Mobil Öncelikli Hamburger Menü (Drawer / Sidebar)
Mobil ekranda hamburger menüye tıklandığında ekranın sağından kayarak açılan şık bir dikey menü tasarlanacaktır:
*   **Aktif Sporlar**: MLB, Tennis (Yanlarında yeşil neon ikonlar).
*   **Beta/Yolda Olan Sporlar**: NBA/NCAA (`BETA` rozetli), NFL, Soccer (`COMING SOON` rozetli, tıklanamaz).
*   **Alt Menü Linkleri**: About, Contact Us, Terms & Disclaimers.

---

## 🏠 3. Mock Ana Sayfa (Central Hub / Karşılama Sayfası) Yapısı

Kullanıcı siteye girdiğinde doğrudan MLB maçlarını görmek yerine, platformun genel kapasitesini ve o günkü en önemli fırsatları sunan bir **Central Hub** ile karşılaşacaktır. 

Bu mock ana sayfa şu dikey bloklardan oluşacaktır:

### Blok 1: Spotlight (Featured Edge of the Day)
*   **Tasarım**: Covers.com tarzında, o gün tüm aktif sporlar (MLB, Tenis vb.) genelinde modelin yakaladığı en yüksek Edge (bahis bürosuna kıyasla en büyük matematiksel avantaj) oranına sahip tek bir maç, sayfanın en üstünde parlayan devasa bir banner kart olarak gösterilir.
*   **Amacı**: Bahisçinin siteye girdiğinde "bugünün en güvendiğimiz seçimi bu" mesajını ilk saniyede alması.

### Blok 2: Yesterday's Scoreboard Ribbon (Dünün Sonuçları Şeridi)
*   **Tasarım**: Yatayda kaydırılabilir (horizontal scroll), dünün tamamlanan maçlarını ve periyot/set skorlarını içeren kompakt bir şerit.
*   **Güven Unsuru**: Modelin dün yaptığı tahminlerin tutup tutmadığını gösteren parlayan rozetler yer alacaktır (örn: `✅ Moneyline Hit!`, `✅ NRFI Hit!`). Bu, modelin başarısını şeffaf şekilde kanıtlar.

### Blok 3: Active Sports Dashboard (Spor Branş Girişleri)
*   **Tasarım**: Yan yana duran premium cam morfizmi (glassmorphic) büyük kartlar.
    *   **MLB Kartı**: "⚾ MLB Predictor - 15 Games Today (Model Updated)" yazar, tıklandığında MLB tahmin ekranına yönlendirir.
    *   **Tenis Kartı (Mock)**: "🎾 Tennis Predictor - 8 Matches Today (Mock Mode)" yazar, tıklandığında Tenis tahmin ekranına yönlendirir.
    *   **NBA Kartı (Beta/Mock)**: "🏀 NBA Predictor - Model is warming up for next season (BETA)" yazar.

### Blok 4: Model Architecture & Sabermetrics
*   **Tasarım**: MLB modelinin altından ana sayfaya taşıyacağımız, sistemin arka plandaki matematiksel gücünü (stadyum balistik etki motoru, normal CDF olasılık dağılımları ve tenis Markov zinciri modelleri) açıklayan premium mini infografik kartları.

---

## 📈 4. Diğer Sporlar İçin Ölçeklenebilirlik (Scalability) Altyapısı

Gelecekte yeni sporlar (Basketbol, Futbol) eklenirken React kodunu tamamen baştan yazmamak için **Config-Driven (Konfigürasyon Tabanlı)** bir yapı kuracağız:

### A. Frontend Konfigürasyonu (`sports_config.js`)
Her spor dalını bir config objesi olarak tanımlayacağız:
```javascript
export const SPORTS_CONFIG = {
  MLB: {
    id: 'mlb',
    name: 'MLB',
    icon: '⚾',
    status: 'ACTIVE',
    models: ['Full Game', 'NRFI Model', 'Pitchers']
  },
  TENNIS: {
    id: 'tennis',
    name: 'Tennis',
    icon: '🎾',
    status: 'ACTIVE',
    models: ['Match Projections']
  },
  NBA: {
    id: 'nba',
    name: 'NBA',
    icon: '🏀',
    status: 'BETA',
    models: ['Full Game', '1st Quarter']
  },
  SOCCER: {
    id: 'soccer',
    name: 'Soccer',
    icon: '⚽',
    status: 'COMING_SOON',
    models: []
  }
};
```
Bu konfigürasyon sayesinde navigasyon barı, hamburger menü ve ana sayfadaki kartlar otomatik olarak üretilecek; yeni bir spor eklemek sadece bu dosyaya 5 satır kod eklemek anlamına gelecektir.

### B. Dinamik Backend API Rotaları
Backend rotalarını `/api/v1/{sport}/predictions` formatında esnek tasarlayarak her spor için bağımsız veri çekimini (polling) destekleyeceğiz.

---

## 📄 5. Yardımcı Sayfalar (About Us, Contact Us, Disclaimers)

Siteyi profesyonel bir bahis danışmanlık portalına çevirmek için şu yardımcı alanları konumlandıracağız:

1.  **About Us (Hakkımızda)**: 
    *   *Nasıl Konumlandırılmalı?*: Ayrı bir sayfa yerine, kullanıcı deneyimini bozmamak adına şık, blur arka planlı ve geçiş animasyonlu bir **Modal** (açılır pencere) olarak tasarlanması önerilir. 
    *   *İçerik*: Platformun veri odaklı felsefesi, yapay zeka ve sabermetrik analizlerin gücü vurgulanacaktır.
2.  **Contact Us (İletişim)**:
    *   *Nasıl Konumlandırılmalı?*: Yine bir **Modal** veya ana sayfanın en altına entegre, basit ve premium bir iletişim formu (Ad-Soyad, Mesaj, Gönder butonu).
    *   *İçerik*: Tyler'a geri bildirim veya iş birliği için ulaşılabilecek temiz bir alan.
3.  **Yasal Uyarı & Şartlar (Terms & Disclaimers)**:
    *   *Nasıl Konumlandırılmalı?*: Sayfanın en altındaki (Footer) küçük linkler üzerinden açılan bir modal veya alt bilgi alanı.
    *   *İçerik*: Tyler'ın en çok önem verdiği sorumluluk reddi metinleri ("Bu bir finansal tavsiye değildir", "Kayıplardan sitemiz sorumlu tutulamaz") burada yer alacaktır.

---

## 📋 6. İş Kırılımı, Öncelikler ve Zorluk Dereceleri (Roadmap)

Geliştirmeye başlamadan önce işleri önceliklerine göre sıraladık (Koda geçilmeyecek, sadece planlama amaçlıdır):

| Öncelik | İş Kodu | Görev Tanımı | Zorluk Derecesi | Etkilenecek Alanlar |
|:---:|:---:|:---|:---:|:---|
| **1** | **M5-P1** | Global Navigation & Hamburger Menü (BETA/COMING SOON rozetli spor listesi) | 🟡 Orta | `DropdownNavigation.jsx`, `App.jsx` |
| **2** | **M5-P2** | Central Dashboard (Ana Sayfa) Tasarımı & featured edge alanı | 🟡 Orta | Yeni `CentralDashboard.jsx` |
| **3** | **M5-P3** | Yesterday's Scoreboard Ribbon UI (Dünün Sonuçları Şeridi) | 🟡 Orta | `CentralDashboard.jsx` |
| **4** | **M5-P4** | Tenis Tahmin Ekranı Mock Arayüz Entegrasyonu (Görsel Kartlar) | 🟡 Orta | Yeni `TennisDashboard.jsx` |
| **5** | **M5-P5** | About & Contact Modalları ve Yasal Uyarı Footer Entegrasyonu | 🟢 Kolay | `Footer.jsx`, `App.jsx` |
| **6** | **M5-P6** | MLB Standings (Lig Puan Durumu) Widget UI | 🟢 Kolay | `CentralDashboard.jsx` |
| **7** | **M5-P7** | Konfigürasyon Tabanlı Spor Yönlendirme Altyapısı (`sports_config.js`) | 🟢 Kolay | `App.jsx`, Router |

---

## 💬 Tartışma ve Karar Verme Noktaları (Tyler ile Alignment İçin)

Koda geçmeden önce Tyler ile netleştirilmesinde fayda olan 2 tasarım tercihi:
1.  **Hakkımızda & İletişim Alanları**: Bu sayfaların ayrı birer URL rotası (örn: `/about`, `/contact`) olarak mı açılmasını tercih eder, yoksa ana sayfa üzerinde şık modal pencereler olarak açılması mobil kullanım için daha mı pratiktir? (Benim önerim **Modal** yönündedir).
2.  **Yesterday's Scoreboard Verisi**: Dünün skorlarını otomatik çekmek için backend'e StatsAPI schedule rotalarını bağlayacağız. Ancak ileride tenis entegre edildiğinde, tenis skorlarını çekmek için ek API limitleri harcamak yerine ilk etapta tenis için dünün skorlarını manuel veya statik bir mock veriyle mi besleyelim?

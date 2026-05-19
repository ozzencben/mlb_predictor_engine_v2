# 🚀 Tyler's MLB Predictor - Faz 2 Yol Haritası ve Analiz Raporu

Tyler'ın gönderdiği geri bildirimler ve yeni özellik talepleri (Milestone 2) oldukça net ve projenin profesyonelleşmesi için çok kritik adımlar içeriyor. Mevcut sistem mimarimize göre bu taleplerin analizini ve nasıl uygulanacağını aşağıda kategoriler halinde özetledim:

---

## 1. 🟢 Hemen Yapılabilecekler (Hızlı UI ve Prompt Güncellemeleri)

Bu gruptaki istekler mevcut mimariyi bozmadan, çok kısa sürede arayüz ve yapay zeka prompt güncellemeleriyle çözülecek konulardır:

*   **SP (Pitcher) İstatistiklerinin Kaldırılması:** Kartın sağ tarafında bulunan FIP ve K-BB% gibi detaylı Pitcher istatistikleri tamamen kaldırılıp, F5 (First 5) ve Maç Sonu Total tahminleri daha sade ve büyük bir şekilde bırakılacak.
*   **AI Insight'ın Madde İmleri (Bullet Points) Yapılması:** Yapay zekanın maç yorumu şu an uzun bir paragraf olarak geliyor. Bunu doğrudan 3-4 maddelik (bullet point) kısa ve vurucu analizler haline getireceğiz.
*   **Takımların Home/Away ve L10 Rekorlarının Eklenmesi:** Mevcut tablolara, takımların kendi evlerindeki veya deplasmandaki rekorları eklenecek.

---

## 2. 🟠 Yeni Eklenmesi Gereken Özellikler (Scraper & Data Güncellemeleri)

Tyler'ın görseldeki gibi nokta atışı veriler istemesi, veri toplama (scraper) botlarımıza bazı yeni özellikler eklememizi gerektiriyor:

*   **Takım NRFI Rekorları:** Sadece atıcıların değil, takımların da hücum anlamındaki NRFI/YRFI (ilk ining sayı atma/atamama) rekorlarını, ev/deplasman ve son 10 maç kırılımlarıyla birlikte çekmemiz gerekecek.
*   **Spesifik Bahis Oranlarının (Odds) Çekilmesi:** Şu an sadece maç sonu (Moneyline) oranlarını çekiyoruz. Sisteme "First 5 (İlk 5 İning)" ve spesifik olarak "NRFI / YRFI" oranlarını (Örn: YRFI -120, NRFI +110) çekecek yeni bir API/Scraper entegrasyonu yapılacak.
*   **Sadece Seçili Bahis Şirketlerinin (Sportsbooks) Filtrelenmesi:** API'den tüm dünyadaki bahis sitelerini çekmek yerine, Tyler'ın istediği gibi sorguyu sadece **FanDuel, DraftKings, Fanatics ve Caesars** ile sınırlandıracağız. Hem sistem hızlanacak hem de API maliyetleri/limitleri optimize edilecek.
*   **Team to Not Score (Takım Bazlı NRFI):** İki takımın da sayı atamaması yerine, sadece tek bir takımın sayı atamaması durumunun analizi sisteme dahil edilecek.

---

## 3. 🔴 Büyük Değişiklik Gerektirenler (Mimari ve Tracking Sistemi)

Bu kısım Milestone 2'nin en büyük iş yükünü oluşturuyor. Projeyi bir "günlük tahmin" motorundan, "geçmişi takip eden analitik bir araca" dönüştürecek adımlar:

*   **Geçmiş Maç Sonuçlarının Takibi (Result Tracking):** Tyler sadece "Elite/Önerilen" bahislerin kazanıp kazanmadığının kaydının tutulmasını istiyor. Mevcut sistem her gün kendini sıfırlıyor. Bunun için:
    1. Her günün tahminlerini ayrı bir dosyada/veritabanında arşivleyecek bir altyapı.
    2. Ertesi sabah çalışıp dün oynanan maçların gerçek skorlarını kontrol eden ve bizim Elite tahminlerimizin **WIN (Kazandı)** veya **LOSS (Kaybetti)** olduğunu işaretleyen yeni bir "Grader Bot" (Sonuçlandırıcı) yazılması gerekecek. (V3)
*   **Tarih Seçici (Date Selector) ve Arayüz Değişimi:** Geçmiş günlerin sonuçlarını (örneğin dünün 8-1'lik rekorunu) görebilmek için anasayfaya bir takvim/tarih kaydırıcısı eklenecek. (V3)

---

## 4. 📁 Yapılacak Güncellemelerin Etkileyeceği Dosyalar

Yukarıdaki yol haritası uygulandığında projede değişecek ana dosyalar şunlardır:

### Frontend (Arayüz)
*   `MatchupCard.jsx`: Pitcher metrikleri (FIP/K-BB) silinecek, Takım NRFI tablosu ve Home/Away rekorları eklenecek.
*   *YENİ DOSYA:* `NrfiListView.jsx` (Tyler'ın istediği liste görünümü için yeni bir bileşen).
*   `App.jsx`: Tarih seçici ve "Daily Games / NRFI" sekmeleri (toggles) eklenecek.

### Backend (Python Mimari)
*   `oddlyspecific_scraper.py`: Takımların hücum NRFI istatistiklerini çekecek şekilde genişletilecek.
*   `odds_scraper.py`: `bookmakers` parametresi ile FanDuel, DraftKings vb. filtrelenecek ve F5/NRFI marketleri (eğer The-Odds-API'de varsa) eklenecek.
*   `groq.py` ve `gemini.py`: AI promptları, "Madde imi (bullet point) kullanarak kısa yanıt ver" şeklinde güncellenecek.
*   `schemas.py`: Yeni oranlar ve NRFI verileri için veri modelleri (Pydantic) güncellenecek.
*   *YENİ DOSYA:* `result_grader.py` (Geçmiş maçların skorlarını kontrol edip W/L durumunu json dosyalarına yazacak olan bot).

**Sonuç:** Sistem bu güncellemelerle birlikte basit bir tahmin aracı olmaktan çıkıp tam teşekküllü, "geçmiş performansını kanıtlayabilen" profesyonel bir bahis yazılımına dönüşecektir. Hazırsak "Hemen Yapılabilecekler" (MatchupCard sadeleştirmesi ve AI bullet-points) kısmından kodlamaya başlayabiliriz!

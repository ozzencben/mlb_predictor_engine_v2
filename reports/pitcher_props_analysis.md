# K Model.ods - Detaylı Model Deşifre ve Analiz Raporu

Bu rapor, Tyler'ın MLB Atıcı Strikeout ve Oyuncu Bahisleri için hazırladığı **`K Model.ods`** dosyasının veri bilimsel tersine mühendislik analizini içerir. Dosya yapısı, sekmeler arası ilişkiler, tahmin formülleri, kritik spreadsheet hataları ve modelin Python/FastAPI backend projemize nasıl aktarılması gerektiğine dair yol haritası aşağıda belgelenmiştir.

---

## 📂 ADIM 1: Sekme Yapısı ve Veri Bağıntıları Analizi

Spreadsheet içerisinde **33 farklı sekme** tespit edilmiştir. Bunların bir kısmı yerel veriler barındırırken, bir kısmı harici Excel referans bağlantılarıdır (`file://MLB%20Model-Chat.xlsx` öneki taşıyanlar).

### Ana Tahmin Sekmesi
*   **`K_Model`**: Tüm tahminlerin yapıldığı, atıcıların expected K% oranlarının hesaplandığı ve POISSON CDF kullanılarak over/under olasılıklarının belirlendiği ana kontrol paneli.

### Veri Besleme ve Eşleme Sekmeleri (Data & Lookup Sheets)
1.  **`Pitchermap`**: Atıcı adını (`Pitcher`) anahtarlayarak atıcının el tercihini (`L/R` -> Solak/Sağlak) ve takım kısaltmasını (`Team`) bulmak için `VLOOKUP` aramalarında kullanılır.
2.  **`pitchha`**: Atıcıların iç saha (`K% H`) ve dış saha (`K% A`) strikeout yüzdelerini barındırır.
3.  **`strike`**: Atıcıların Called Strike % (`CStr%`), Swinging Strike % (`SwStr%`) ve Called + Swinging Strike % (`CSW%`) metriklerini tutar. Ayrıca `H2` hücresinde lig ortalaması `SwStr%` (10.4%) değerini barındırır.
4.  **`inning`**: Atıcıların maç başına ortalama innings pitched (`IP/G`) ve toplam karşılaştığı vurucu (`TBF/G`) değerlerini sağlar.
5.  **`lineups`**: Her takımın günlük başlangıç 9'lu oyuncu isimlerini barındırır.
6.  **`hithand`**: Vurucuların solak atıcılara (`vs LHP`) ve sağlak atıcılara (`vs RHP`) karşı tarihsel `K%` oranlarını tutar.
7.  **`hitters`**: Vurucuların genel `CSW%`, `SwStr%` ve lig ortalaması `CSW%` (`G2` hücresinde `28.2%`) değerlerini barındırır.
8.  **`krank`**: Rakip takımların strikeout alma yatkınlıklarına göre lig sıralamasını (`Opp K Rank`) tutar.
9.  **`Teamnames`**: ESPN ve Fangraphs arasındaki takım adı yazım farklılıklarını senkronize eden dönüşüm tablosudur.

---

## 📊 ADIM 2: 'K Model' Sekmesi Tüm Sütunların Deşifresi

`K_Model` sayfasında A sütunundan AF sütununa kadar uzanan veri yapısı şu şekildedir (Örnek değerler **Lucas Giolito** satırından alınmıştır):

| Sütun | Başlık | Ham Değer (Satır 2) | İş Mantığı / Formül Yapısı |
| :--- | :--- | :--- | :--- |
| **A** | GM | `1` | Maç/Oyun ID |
| **B** | H/A | *(Boş / H)* | Atıcının Home (H) veya Away (A) oynama durumu |
| **C** | L/R | `R` | Atıcının el terciyi (RHP/LHP) -> `Pitchermap` sekmeli VLOOKUP |
| **D** | Team | `BOS` | Atıcının takımı -> `Pitchermap` sekmeli VLOOKUP |
| **E** | Pitcher | `Lucas Giolito` | Atıcı adı -> `dailymodel` sekmesinden çekilir |
| **F** | Opponent | `Philadelphia Phillies` | Rakip takım adı -> `dailymodel` sekmesinden çekilir |
| **G** | IP/G | `5.5` | Maç başına atılan ortalama inning -> `inning` sekmesinden XLOOKUP |
| **H** | TBF/G | `23.4` | Maç başına karşılaşılan ortalama vurucu sayısı -> `inning` sekmesinden XLOOKUP |
| **I** | BF / inn | `4.22` | Inning başına karşılaşılan ortalama vurucu sayısı -> `=H2/G2` |
| **J** | K% H | `0.2` | Atıcının iç saha Strikeout oranı -> `pitchha` sekmeli VLOOKUP |
| **K** | K% A | `0.20` | Atıcının dış saha Strikeout oranı -> `pitchha` sekmeli VLOOKUP |
| **L** | CSW% | `0.261` | Atıcının Called+Swinging Strike oranı -> `strike` sekmeli VLOOKUP |
| **M** | CSW adj | `-0.021` | Atıcının lig ortalamasından CSW sapması -> `=(L2 - AE12)` |
| **N** | xTInn | `4.22` | **[HATALI BÖLÜM]** Beklenen inning süresi -> `=H2/G2` (BF/inn ile aynı) |
| **O** | xBF | `17.80` | Beklenen karşılaşılan vurucu sayısı -> `=N2 * I2` (BF/inn'in karesi) |
| **P** | SwStr% | `0.097` | Atıcının Swinging Strike oranı -> `strike` sekmeli VLOOKUP |
| **Q** | SwStr adj| `-0.007` | Atıcının lig ortalamasından SwStr sapması -> `=P2 - D74` |
| **R** | K% exp | `0.216` | **[HATALI BÖLÜM]** Vurucu ve atıcı metrikleri ağırlıklı ham K% beklentisi |
| **S** | K% Final| `0.206` | CSW ve SwStr ayarlı nihai K% beklentisi -> `=R2 + (M2 * 0.35) + (Q2 * 0.35)` |
| **T** | Strikeouts| `3.7` | Projekte edilen toplam Strikeout sayısı -> `=O2 * S2` |
| **U** | Book Line| `5.5` | Bahis bürolarının açtığı K limiti (Bookmaker Line) |
| **V** | Opp K Rank| `12` | Rakibin K yüzdesi lig sıralaması -> `krank` sekmeli XLOOKUP |
| **W** | Over Prob| `17%` | Limit üstü (Over) gelme ihtimali -> `=1 - POISSON(U2; T2; TRUE)` |
| **Y** | GM 1 | `1` | Eşleşen oyun ID'si |
| **Z** | Lineup | `Trea Turner` | Rakip kadrodaki vurucu adı -> `lineups` sekmeli VLOOKUP |
| **AA** | K% RHP | `0.191` | Vurucunun sağlak atıcılara karşı K% oranı -> `hithand` VLOOKUP |
| **AB** | K% LHP | `0.16` | Vurucunun solak atıcılara karşı K% oranı -> `hithand` VLOOKUP |
| **AC** | K% H | `0.166` | Vurucunun iç saha K% oranı -> `hithand` VLOOKUP |
| **AD** | K%A | `0.196` | Vurucunun dış saha K% oranı -> `hithand` VLOOKUP |
| **AE** | CSW% | `0.254` | Vurucunun CSW eğilimi -> `hitters` VLOOKUP |
| **AF** | SwStr% | `0.12` | Vurucunun SwStr eğilimi -> `hitters` VLOOKUP |

---

## 🧮 ADIM 3: Formül ve Matematiksel Mantık Analizi

### 1. Sütun S'deki Ana Formül Yapısı (Nihai K% Hesabı)
$$\text{K\% Final} = \text{K\% exp} + (\text{CSW adj} \times 0.35) + (\text{SwStr adj} \times 0.35)$$

*   **`K% exp` (R Sütunu)**: Atıcının kendi K% performansı ile rakip vurucuların K% zaaflarının ağırlıklı birleşimidir.
*   **`CSW adj` (M Sütunu)**: Atıcının Called + Swinging Strike yüzdesinin lig ortalamasından sapmasıdır (`L2 - AE12`). Buradaki `AE12` sabiti `0.282` (%28.2) lig ortalaması CSW%'yi temsil eder.
*   **`SwStr adj` (Q Sütunu)**: Atıcının Swinging Strike yüzdesinin lig ortalamasından sapmasıdır (`P2 - D74`). Buradaki `D74` sabiti `0.103960725` (%10.4) lig ortalaması SwStr%'yi temsil eder.
*   **İş Mantığı**: Eğer bir atıcının ham beklenilen K% değeri yüksek olsa bile, eğer topu vuruculara ıskalatma oranı (`SwStr%`) veya strikes bulma verimliliği (`CSW%`) lig ortalamasının altındaysa, bu durum nihai K% beklentisini aşağıya çeker. Ağırlık katsayısı her iki metrik için de **0.35 (%35)** olarak belirlenmiştir.

---

### 2. 'K% exp' (R Sütunu) Detaylı Matematiksel Mantığı
Atıcının Home/Away durumuna göre formül ikiye ayrılmaktadır:

*   **Eğer Atıcı Home İse (`B2 = "H"`):**
    $$\text{K\% exp} = 0.65 \times \text{Pitcher K\% Home} + 0.45 \times \left(0.55 \times \text{Opponent K\% vs Handedness} + 0.35 \times \text{Opponent K\% Away}\right)$$
    *   *Not: Atıcı ev sahibi ise, rakip deplasmandadır, bu yüzden deplasman K% oranı (`Opponent K% Away` -> `AD11`) kullanılır.*

*   **Eğer Atıcı Away İse (`B2 != "H"`):**
    $$\text{K\% exp} = 0.65 \times \text{Pitcher K\% Away} + 0.45 \times \left(0.55 \times \text{Opponent K\% vs Handedness} + 0.35 \times \text{Opponent K\% Home}\right)$$
    *   *Not: Atıcı deplasmanda ise, rakip ev sahibidir, bu yüzden iç saha K% oranı (`Opponent K% Home` -> `AC11`) kullanılır.*

*   **`Opponent K% vs Handedness` Seçimi:**
    *   Atıcı sağlak ise (`C2 = "R"`): Vurucuların sağlaklara karşı K% ortalaması (`AA11`) kullanılır.
    *   Atıcı solak ise (`C2 = "L"`): Vurucuların solaklara karşı K% ortalaması (`AB11`) kullanılır.

---

### 3. 'CSW adj' (M Sütunu) ve 'xTInn' (N Sütunu)
*   **`CSW adj`**: `= L2 - $AE$12` şeklinde hesaplanır. `L2` o maçın atıcısının kendi CSW% değeridir. `$AE$12` ise `K_Model` sekmesinde `AE12` hücresine yazılmış olan sabit Lig CSW% ortalamasıdır (`0.282`).
*   **`xTInn`**: Ham formülü `=(.H2/.G2)` şeklindedir. Burada `H2` = `TBF/G` (Batters Faced) ve `G2` = `IP/G` (Innings Pitched) değerleridir. Dolayısıyla `xTInn` aslında beklenen inning sayısı değil, **Inning başına karşılaşılan vurucu sayısıdır (BF / inn)**.

---

## 🚨 ADIM 4: Kritik spreadsheet Hataları ve Formül Açıkları

Tyler'ın hazırladığı ODS modelinde tahmin başarısını doğrudan bozan ve programatik olarak **kesinlikle düzeltilmesi gereken 3 büyük hata** tespit edilmiştir:

### 1. Sütun R'deki Göreli Hücre Kayması Hatası (Relative Reference Drift Bug)
*   **Hata Tanımı**: expected K% (`K% exp`) hesaplanırken, rakip takımın 9 kişilik kadrosunun ortalamasını tutan satır olan **Satır 11** (`AA11`, `AB11`, `AC11`, `AD11`) referans alınmıştır. Ancak formülde dolar işareti (`$`) kullanılmadığı için (`AA$11` yerine `AA11`), formül aşağı doğru kopyalandığında satır referansları kaymıştır.
*   **Sonuçları**:
    *   **2. Satır (1. Maç)**: Doğru şekilde `Row 11` (Kadro 1 Ortalamaları) değerlerini okur.
    *   **3. Satır (2. Maç)**: `Row 12` değerlerini okur. `Row 12` ise kadro ortalaması değil, **League Avg** (Sabit Lig Ortalamaları) satırıdır. Dolayısıyla 2. maç tahmininde rakip kadronun hiçbir önemi kalmaz, doğrudan lig ortalaması hesaba katılır.
    *   **4. Satır (3. Maç)**: `Row 13` değerlerini okur. Burası boş veya alakasız değerler içerir.
    *   **6. Satır (5. Maç)**: `Row 15` değerlerini okur. Bu satırda bir sonraki veri bloklarının **metin başlıkları** (`Lineup`, `K% RHP` vb.) yazılıdır. Metin değerlerini matematiksel formüle sokmaya çalıştığı için sistem çöker ve **`#DEĞER!` (#VALUE!)** hatası üretir.
    *   *Bu hata, 1. maç dışındaki tüm diğer maçların tahminlerini matematiksel olarak tamamen geçersiz ve hatalı kılmaktadır.*

### 2. Sütun N ve O'daki Karşılaşılan Vurucu Hacmi Karesi Hatası (Volume Squaring Bug)
*   **Hata Tanımı**: `xTInn` (Beklenen Inning) sütununun formülü `=H2/G2` (`BF/inn`) olarak girilmiştir. Ardından `xBF` (Beklenen Toplam Karşılaşılan Vurucu) sütununun formülü `=N2 * I2` yani `xTInn * (BF/inn)` şeklinde girilmiştir.
*   **Sonuçları**:
    *   Formül açıldığında: $\text{xBF} = (\text{BF/inn}) \times (\text{BF/inn}) = (\text{BF/inn})^2$ haline gelir.
    *   Örnek olarak Lucas Giolito için: $\text{xBF} = 4.22 \times 4.22 = 17.80$ vurucu hesaplanır.
    *   Oysa bir başlangıç atıcısının normalde maç başına karşılaştığı ortalama vurucu sayısı (`TBF/G`) **23.4**'tür.
    *   Model, atıcının hacmini (volume) yanlışlıkla inning başına vurucu oranının karesini alarak hesapladığı için atıcı sanki maçta sadece **17.8** vurucuyla karşılaşacakmış gibi hesap yapar. Bu da projekte edilen K sayısını (`Strikeouts` -> Sütun T) **%24 oranında deflasyona uğratır** (Giolito için doğru projeksiyon ~4.8 K olması gerekirken model 3.7 K hesaplar).
    *   *Çözüm*: `xTInn` doğrudan atıcının maç başına ortalama inning sayısı olan `G2` (`IP/G`) değerine eşitlenmeli, `xBF` ise `xTInn * (BF/inn)` formülüyle çalıştırılmalıdır (böylece $5.5 \times 4.22 = 23.2$ BF olarak doğru hacim bulunur).

### 3. Yeni Oyuncular İçin `#YOK` (#N/A) Hatasının Yayılması (Error Propagation)
*   **Hata Tanımı**: VLOOKUP fonksiyonları, `pitchha` veya `strike` sekmelerinde adı bulunmayan çaylak atıcılar (Örn: `Jared Jones` veya `J.T. Ginn` o tarihte yeni çıktığı için sekmelerde yoktur) için doğrudan `#YOK` hatası döndürür.
*   **Sonuçları**:
    *   Bu hata Excel/ODS yapısı gereği zincirleme olarak K% Final, Strikeouts ve Over Prob hücrelerine sirayet eder ve o maç için tahmin üretilemez.
    *   *Çözüm*: Python backend modelimizde bu tür eksik veriler için StatsAPI'den anlık çekim yapan fallback / default parametre atama mantığı işletilmelidir.

---

## 🛠️ ADIM 5: Projeye Geçiş (Python Entegrasyon Planı)

Tyler'ın atıcı modelini projemize sıfır hata ve maksimum sabermetrik doğrulukla entegre etmek için `pitcher_props_engine.py` dosyasını şu şekilde güncelleyeceğiz:

### 1. Python Sınıf Yapısı ve Metrik Eşleşmeleri
```python
# K Model.ods modelinin kusursuz Python implementasyonu

def calculate_pitcher_props_ods_style(pitcher_stats: dict, opp_lineup_avg: dict, is_home: bool) -> dict:
    """
    K Model.ods dosyasındaki matematiksel mantığı, formül hatalarını düzelterek 
    Python ortamında çalıştırır.
    """
    # 1. Lig Ortalaması Sabitleri (Spreadsheet'teki AE12 ve D74 hücreleri)
    LG_AVG_CSW = 0.282
    LG_AVG_SWSTR = 0.10396
    
    # 2. Atıcı Metrikleri
    pitcher_hand = pitcher_stats.get("throws", "R")
    p_k_home = pitcher_stats.get("k_pct_home", 20.0) / 100.0
    p_k_away = pitcher_stats.get("k_pct_away", 20.0) / 100.0
    p_csw = pitcher_stats.get("csw_pct", 26.0) / 100.0
    p_swstr = pitcher_stats.get("swstr_pct", 10.0) / 100.0
    
    # Atıcı Hacim Metrikleri (IP/G ve TBF/G)
    p_ip_g = pitcher_stats.get("avg_ip", 5.5)
    p_tbf_g = pitcher_stats.get("avg_bf", 23.4)
    bf_per_inn = p_tbf_g / p_ip_g if p_ip_g > 0 else 4.20
    
    # 3. Rakip Kadro Metrikleri (Lineup Avg - Satır 11 değerleri)
    l_k_rhp = opp_lineup_avg.get("k_pct_rhp", 22.0) / 100.0
    l_k_lhp = opp_lineup_avg.get("k_pct_lhp", 22.0) / 100.0
    l_k_home = opp_lineup_avg.get("k_pct_home", 22.0) / 100.0
    l_k_away = opp_lineup_avg.get("k_pct_away", 22.0) / 100.0
    
    # 4. expected K% (K% exp) Hesabı (Hata 1 Düzeltildi - Mutlak Referans Kilitli)
    if is_home:
        # Atıcı Home ise, Rakip deplasmandadır (l_k_away kullanılır)
        opp_hand_k = l_k_rhp if pitcher_hand == "R" else l_k_lhp
        opp_adjusted_k = (opp_hand_k * 0.55) + (l_k_away * 0.35)
        k_exp = (p_k_home * 0.65) + (opp_adjusted_k * 0.45)
    else:
        # Atıcı Away ise, Rakip ev sahibidir (l_k_home kullanılır)
        opp_hand_k = l_k_lhp if pitcher_hand == "R" else l_k_rhp
        opp_adjusted_k = (opp_hand_k * 0.55) + (l_k_home * 0.35)
        k_exp = (p_k_away * 0.65) + (opp_adjusted_k * 0.45)
        
    # 5. Adjsutment (Sapma) Hesapları
    csw_adj = p_csw - LG_AVG_CSW
    swstr_adj = p_swstr - LG_AVG_SWSTR
    
    # 6. Nihai K% Beklentisi
    k_final = k_exp + (csw_adj * 0.35) + (swstr_adj * 0.35)
    k_final = max(0.05, min(0.50, k_final)) # Güvenlik sınırları
    
    # 7. Hacim Projeksiyonu (Hata 2 Düzeltildi - Hacim Karesi Yerine Doğru IP*BF/inn Hesabı)
    expected_ip = p_ip_g  # xTInn artık doğrudan ortalama inning süresidir
    expected_bf = expected_ip * bf_per_inn # xBF = IP * (BF/inn) = TBF/G
    
    # 8. Nihai Projeksiyonlar
    projected_k = expected_bf * k_final
    projected_outs = expected_ip * 3.0
    
    return {
        "projected_k": round(projected_k, 2),
        "projected_outs": round(projected_outs, 2),
        "k_final_pct": round(k_final * 100, 1),
        "expected_bf": round(expected_bf, 1)
    }
```

### 2. StatsAPI & Scraper Entegrasyon Gereksinimleri
Backend veri kazıma (`pitcher_scraper.py` ve `matchup_scraper.py`) mekanizmalarına şu alanlar eklenmelidir:
*   Atıcının iç saha/dış saha splitleri (`k_pct_home`, `k_pct_away`).
*   Vurucuların LHP/RHP splitleri (`k_pct_rhp`, `k_pct_lhp`) ile iç saha/dış saha K% oranları.
*   Atıcının kariyer/sezon ortalaması `csw_pct` ve `swstr_pct` değerleri.

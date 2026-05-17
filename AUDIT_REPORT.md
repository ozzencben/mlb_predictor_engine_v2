# MLB Tahmin Motoru Teknik Audit Raporu

Bu rapor, FastAPI tabanlı MLB Tahmin Motoru projesinin kod yapısını, veri pipeline güvenliğini, sabermetrik tutarlılığını ve genişletilebilirliğini detaylı bir şekilde analiz eder.

## 1. MİMARİ VE KOD KALİTESİ DEĞERLENDİRMESİ (SOLID & CLEAN CODE)

### Tip Güvenliği
- `GameInputData` için `pydantic` kullanımı olumlu, ancak bu yalnızca `daily_matchups.json` satırları için geçerli.
- Model girişleri (`team_db`, `pitcher_db`, `ballpark_db`) hâlâ saf `dict` olarak taşınıyor ve bu yapıların shape’i doğrulanmıyor.
- Örnek riskler:
  - `PitcherStats` ve `TeamMLBStats` oluşturulurken `float(p.get(...))` kullanılıyor; `None`, `""`, `"N/A"` veya beklenmeyen stringler `ValueError` üretebilir.
  - `WeatherScraper` ve `OddsProvider` verileri JSON yüklerken schema doğrulaması yok.
- `dataclass` kullanımı doğru; ancak `pydantic` sadece giriş modelinde sınırlı kullanılıyor. Orta/arka uç DB ve scrapper çıktılarına da benzer sert tip kontrol uygulanmalı.

### `prediction_runner.py` Fast Fail ve Hata Yakalama
- `PredictionRunner._run_scrapers()`:
  - `DataCollector` ve `MatchupScraper` için "kritik hata -> durdur" yaklaşımı var: bu iyi.
  - `PitcherScraper`, `OddsProvider`, `WeatherScraper` için ise sadece uyarı verip devam ediliyor. Bu, çıktının bozulmasını önler ama modelin "sessiz şekilde" dejenere olmasına neden olur.
- Genel try/except yapısı:
  - `for game_dict in games:` içinde geniş `except Exception as e` kullanılıyor. Bu, hataları tüketir ve tekrarlayan yanlış veri sorunlarını örtme riski yaratır.
  - Aynı şekilde `_atomic_save` içindeki geniş `except` blokları, temp dosya temizliği yapıyor ama hata türlerini ayırt etmiyor.
- `GameInputData(**game_dict)` küçük ama değerli bir iyileştirme. Ancak modelin kullandığı dış veri kaynakları için benzeri yok.

### `_atomic_save` Değerlendirmesi
- Sağlamlık: doğru. `temp file + os.replace()` ile bozuk yazma riski azaltılmış.
- Performans:
  - Disk I/O: dosya önce temp dosyaya yazılıyor, sonra replace ediliyor => yazma maliyeti iki aşamada, ancak gerçek veri boyutu tek seferde.
  - Bellek: JSON `data` zaten RAM’de, sonra `json.dump` ile seri hale getiriliyor; büyük yüklerde bellek iki kopyaya yaklaşabilir.
- Sonuç: günlük tahmin üretimi için makul. Ancak yüksek frekanslı canlı güncelleme / websocket çıktısı için ölçeklendirilebilir değil.

## 2. MATEMATİKSEL VE SABERMETRİK GÜVENLİK AUDİTİ

### `f5_model.py` ham skor mantığı
- Formül: `4.5 * offense_rating * (1.0 / pitching_defense_strength) * 5/9`
- `pitching_defense_strength = (sp_rating * 0.95) + 0.05`
  - `sp_rating` zaten minimum `0.6` olduğundan `ZeroDivision` riski yok.
  - Ancak `+0.05` eklentisi bir "hack": düşük SP kalitelerini fazladan düzeltir ve formülde sistematik sapma yaratır.
- `PitcherStats.sp_rating`:
  - `rating = (4.20 / max(0.1, fip)) * (1 + (k_bb_pct - 0.14))`
  - Veri tipi/ölçek hatası tehlikesi:
    - `k_bb_pct` eğer yüzde olarak `14` gelirse büyük bir sapma olur, sonra clamp ile maskeleme yaşanır.
    - `fip` negatif veya sıfıra yakınsa `max(0.1, fip)` ile çökme engelleniyor ama bu da model akışını bozar.
- Sabermetrik olarak:
  - `offense_rating` ve `sp_rating` clamping’i (0.7/1.3 ve 0.6/1.4) modelin "aşırı değerleri" saklamasına neden oluyor.
  - Bu, yanlış veri geldiğinde çökme yerine yanlış fakat tutarlı skor üretir.

### `mlb_model.py` ham skor mantığı
- Formül: `4.5 * offense_rating * (1.0 / pitching_defense_strength) * park_f`
- `pitching_defense_strength` = `0.66 * SP + 0.34 * BP`
  - Bu ağırlıklandırma felsefeye uygun; ancak `park_f` normalize edilmesi zayıf:
    - `factor > 10` ise `%` kabul edip `/100`, yoksa olduğu gibi kullanıyor.
    - `park_factor` değeri `0`, negatif veya çok büyük olursa model akışı bozulabilir, sadece sonuç `min(15.0, ...)` ile sınırlanıyor.
- Pythagorean `1.83`:
  - `away_prob = away_score ** 1.83 / (away_score ** 1.83 + home_score ** 1.83)` matematiksel düzeyde kabul edilebilir bir heuristik.
  - Ancak hem full game hem F5’te aynı üs kullanılıyor; bu modelin iki farklı ölçeği aynı mantıkla yorumladığını gösterir.

### `mlb_unified_engine.py` güvenlik kontrolü
- Safety Check: `full_<team> < f5_<team> + 0.5` ise `full_<team> = f5_<team> + 0.5`
- Bu mantık:
  - Bir takımın tam maçta 5 inning skorundan daha az atamayacağına dair basit bir tutarlılık kuralı.
- Risk / leak:
  - Bu işlem `full` model çıktısını sonradan manipüle ediyor.
  - Sonuç: `Full_Game` modelinin hem toplam hem win-prob hesapları artık orijinal model bileşenlerinden bağımsız hale geliyor.
  - Eğer sadece bir taraf düzeltildiyse, bu düzeltme `spread` ve `value_alerts` hesaplarını yapay olarak etkiler.
- Sonuç: bu, F5 ve Full modelleri arasında matematiksel "bilgi sızıntısı"dır. Yani full maç modelinin iç tutarlılığı bozuluyor.

### `nrfi_model.py` Poisson ve normalizasyon
- `clamp_norm(val, base, divisor)`:
  - `max(0.0, min(1.0, (float(val) - base) / divisor))`
  - Şu anki kullanımla doğru çalışıyor.
  - Eksiklik:
    - `divisor == 0` veya negatif değer için koruma yok.
    - `ValueError/TypeError` durumunda `0.5` dönmesi, kötü veriyi gizleyebilir.
- `pNRFI = exp(-fip / 9)`:
  - Burada FIP doğrudan “runs per 9 innings” yerine kullanılıyor; teorik olarak FIP R/9 değildir.
  - Bu, NRFI modeline sabermetrik olarak belirsizlik getiriyor. Yani model yanlış değişkeni Poisson’ya sokuyor.
- Özet:
  - Normalizasyon sınırları doğru, ama temel parametrelerin semantik olarak hatalı kullanımı var.

## 3. VERİ PIPELINE’I VE PARSER GÜVENLİĞİ

### Senkron mimarinin darboğazları
- `PredictionRunner._run_scrapers()` tamamen sıra ile çalışıyor:
  1. TeamRankings
  2. MLB API matchups
  3. PitcherScraper
  4. OddsProvider
  5. WeatherScraper
- En kritik sorunlar:
  - `requests.get(..., timeout=10)` kullanımı iyi ama aynı anda birden çok istek yapılmıyor.
  - `WeatherScraper.fetch_todays_weather()` içindeki her takım için ayrı HTTP çağrısı var; bu da maç sayısı arttıkça gecikmeyi lineer olarak büyütür.
  - `PitcherScraper` her bir SP için önce ID arıyor, sonra istatistik çekiyor; bu iki aşamalı seri süreç çok uzun sürebilir.
- Rate-limit / latency etkileri:
  - Bir servis takılırsa tüm pipeline bekler.
  - Hiçbir retry/backoff veya fallback “bu servis yoksa diğerleri çalışsın” stratejisi yok.
  - Bu yapı, canlı / gerçek zamanlı çalışmada sistem güvenliğini zayıflatır.

### `TBD` pitcher fallback etkisi
- `PitcherScraper`:
  - SP ID bulunamazsa veya stats yoksa lig ortalaması (`league_averages`) atıyor.
- Etki:
  - F5 modelinde SP ağırlığı %95 olduğu için bu fallback, tahmini önemli derecede ortalamalaştırır.
  - `MLBModel` yüzde 66 SP ağırlığı nedeniyle de SP bilgilerinin zayıflaması sonucu “edge” kaybı olur.
  - Bu, modelin yanlış pozitif/negatif edge üretmesine yol açabilir, fakat çıktıda bunun hangi maçta gerçekleştiği görünmüyor.
- Veri tutarlılığı:
  - Orta ve zayıf veri kalitesine karşı koruma var; ama bu koruma “şeffaf değil”.
  - İdeal: fallback bilgisi çıkışa eklenmeli ve risk derecesi raporlanmalı.

## 4. GELECEKTEKİ GENİŞLETİLEBİLİRLİK (MILESTONE 2 - V3 HAZIRLIĞI)

### Yeni özellikler ve mevcut yapı uyumu
- `oddlyspecificstats.com scraper`
- `BvP veri şeması`
- `Gemini AI analiz motoru`
- `WebSockets canlı skor ticker`

### Uygunluk değerlendirmesi
- `MLBUnifiedEngine`:
  - Doğrudan `NRFIModel`, `F5Model`, `MLBModel` ile sıkı bağlı.
  - Yeni bir analiz motoru eklemek için sınıfa yeni alan, yeni payload alanı ve yeni hesaplama adımı eklemek gerekecek.
  - Bu, Open-Closed prensibine uymuyor.
- `PredictionRunner`:
  - Scraper sırası ve veri kaynağı sabit kodlanmış.
  - Yeni bir veri kaynağı veya yeni canlı veri beslemesi eklemek için mevcut metoda müdahale gerekir.
- `OddsProvider`:
  - Tek kaynaklı, The Odds API merkezli. Alternatif kaynak eklemek kodu genişletir.
- `WeatherScraper` / `PitcherScraper`:
  - Henüz plugin mimarisi yok; yeni kaynaklar eklendiğinde bu sınıflar büyüyecek.

### Refactor edilmesi gereken sınıflar
- `MLBUnifiedEngine`
- `PredictionRunner`
- `OddsProvider`
- `PitcherScraper`
- `WeatherScraper`
- Ek olarak `GameInputData` + `live_stats.json`/`pitcher_stats.json`/`ballpark_stats.json` için Pydantic modeller

## 5. KRİTİK REFACTORING TAVSİYELERİ VE AKSİYON LİSTESİ

| Kritik Seviye | Açıklama | Çözüm Kodu Taslağı |
|---|---|---|
| Kritik | `PredictionRunner` tamamen senkron ve dış servis gecikmelerine karşı savunmasız. | `PredictionRunner`’ı async/parallel hale getir: `asyncio.gather` ile `OddsProvider`, `WeatherScraper`, `PitcherScraper` ve API çağrılarını eşzamanlı çalıştır. |
| Kritik | `MLBUnifiedEngine` safety check sonrası `Full_Game` sonuçları model tutarlılığını bozuyor. | Post-hoc düzeltme yerine, full-game modeline `min(full_score, f5_score + 0.5)` veya regularizasyon bazlı bir constraint ekleyerek tutarlılığı sağla. Ayrıca `adjusted` bilgisini payload’a ekle. |
| Kritik | Dış JSON / scrapper verileri için zayıf tip kontrolü. | `live_stats.json`, `pitcher_stats.json`, `daily_matchups.json` için Pydantic schema’ları yaz. Model girişlerine `parse_obj`/`validate` ekle. Hatalı kayıtları erken reddet. |

## Özet Değerlendirme
- Mimari: mantıklı ama katı bağlılıklar var. Mevcut yapı küçük sürümler için yeterli; ancak V3’te yeni istatistik kaynakları hızla karmaşıklaşacak.
- Sabermetrik: temel filozofi yerinde, ama `FIP` ve `NP` kullanımında semantik belirsizlikler var. `nrfi_model.py` Poisson dönüşümü sabit bir FIP/R/9 eşleştirmesi içeriyor; bu daha güçlü bir istatistiksel yeniden değerlendirme gerektirir.
- Güvenlik: veri kaynakları için “pipeline resiliency” eksik. Sürüşü koruyan `atomic_save` iyi, ama servis gecikmesi ve veri formatı riskleri yeterince ele alınmamış.
- Genişletilebilirlik: `MLBUnifiedEngine` ve `PredictionRunner` plugin/strategy pattern olmadan yeni mantıkları kırılmadan eklemez.

> Eğer isterseniz, bu rapordan hemen sonra “V3 refactor planı” çıkarabilir ve `PredictionRunner` + `MLBUnifiedEngine` için sınıf bazlı yeniden tasarım şeması hazırlayabilirim.

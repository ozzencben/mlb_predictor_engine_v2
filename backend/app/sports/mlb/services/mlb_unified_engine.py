import math
from typing import Optional
from pydantic import BaseModel, Field

from app.sports.mlb.models.nrfi_model import NRFIModel
from app.sports.mlb.models.f5_model import F5Model
from app.sports.mlb.models.mlb_model import MLBModel
from app.sports.mlb.models.schemas import NRFITrendSchema, PitcherTrendData


# --- Pydantic Schema --- (FastAPI Endpoint'i için gerekli yapı)
class GameInputData(BaseModel):
    away_team: str
    home_team: str
    away_pitcher: str
    home_pitcher: str
    game_time: str = "TBD"
    status: str = "TBD"
    odds: dict = Field(default_factory=dict)
    away_team_stats: dict = Field(default_factory=dict)
    home_team_stats: dict = Field(default_factory=dict)
    away_team_id: int = None
    home_team_id: int = None
    away_pitcher_id: Optional[int] = None
    home_pitcher_id: Optional[int] = None


# Artık bu sınıfları doğrudan import ediyoruz. (Önceki adımlarda yazdığımız sınıflar)
# from core.models.nrfi import NRFIModel
# from core.models.f5 import F5Model
# from core.models.mlb import MLBModel


class MLBUnifiedEngine:
    """
    The Orchestrator.
    Routes live data to specific models (NRFI, F5, MLB), applies safety logic,
    and returns a unified dictionary ready for the frontend.
    """

    def __init__(
        self,
        team_db: dict,
        pitcher_db: dict,
        ballpark_db: dict = None,
        standings_db: dict = None,
    ):
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        self.ballpark_db = ballpark_db or {}
        self.standings_db = standings_db or {}

        # Modellerin başlatılması
        self.nrfi_model = NRFIModel(pitcher_db, team_db, ballpark_db)
        self.f5_model = F5Model(team_db, pitcher_db)
        self.mlb_model = MLBModel(team_db, pitcher_db, ballpark_db)

    def _recalculate_probabilities(
        self, away_score: float, home_score: float, exponent: float = 1.83
    ) -> tuple[float, float]:
        """Skorlar güvenlik sınırına takılırsa kazanma ihtimallerini yeniden hesaplar."""
        if away_score == 0 and home_score == 0:
            return 0.500, 0.500

        a_pow = away_score**exponent
        h_pow = home_score**exponent
        total_pow = a_pow + h_pow

        return a_pow / total_pow, h_pow / total_pow

    def calculate_weather_impact(self, weather: dict, home_team: str) -> dict:
        """
        Yerel fiziksel model: Rüzgar yönü/hızı, sıcaklık, nem ve rakıma dayalı
        topun havada süzülme mesafesini ve Runs/HR/K etkisini $0 API maliyetiyle hesaplar.
        """
        stadium_metrics = {
            "Colorado": {"altitude": 5200, "bearing": 10},
            "Boston": {"altitude": 20, "bearing": 45},
            "Cincinnati": {"altitude": 480, "bearing": 40},
            "Atlanta": {"altitude": 1050, "bearing": 20},
            "Kansas City": {"altitude": 270, "bearing": 0},
            "LA Dodgers": {"altitude": 270, "bearing": 25},
            "Texas": {"altitude": 500, "bearing": 0},
            "Chi White Sox": {"altitude": 590, "bearing": 35},
            "Philadelphia": {"altitude": 20, "bearing": 15},
            "Arizona": {"altitude": 1080, "bearing": 10},
            "Chi Cubs": {"altitude": 600, "bearing": 55},
            "Houston": {"altitude": 40, "bearing": 0},
            "Miami": {"altitude": 10, "bearing": 0},
            "Milwaukee": {"altitude": 600, "bearing": 0},
            "NY Yankees": {"altitude": 50, "bearing": 55},
            "Pittsburgh": {"altitude": 740, "bearing": 70},
            "Toronto": {"altitude": 250, "bearing": 0},
            "Washington": {"altitude": 25, "bearing": 0},
            "Baltimore": {"altitude": 30, "bearing": 45},
            "Detroit": {"altitude": 600, "bearing": -5},
            "LA Angels": {"altitude": 160, "bearing": 65},
            "Minnesota": {"altitude": 840, "bearing": 55},
            "NY Mets": {"altitude": 15, "bearing": 40},
            "Tampa Bay": {"altitude": 10, "bearing": 0},
            "Cleveland": {"altitude": 650, "bearing": 35},
            "Athletics": {"altitude": 30, "bearing": 30},
            "San Diego": {"altitude": 15, "bearing": 30},
            "SF Giants": {"altitude": 10, "bearing": 45},
            "St Louis": {"altitude": 460, "bearing": -20},
            "Seattle": {"altitude": 10, "bearing": 40}
        }

        # Varsayılanlar
        temp = float(weather.get("temp_f", 72.0))
        wind = float(weather.get("wind_mph", 0.0))
        direction = str(weather.get("wind_direction", "Calm"))
        humidity = float(weather.get("humidity", 50.0))
        
        is_dome = False
        if "calm" in direction.lower() or "dome" in direction.lower() or "roof" in direction.lower() or "closed" in direction.lower():
            is_dome = True
            
        metrics = stadium_metrics.get(home_team, {"altitude": 0, "bearing": 0})
        
        if is_dome:
            return {
                "ball_carry_ft": 0.0,
                "runs_impact_pct": 0.0,
                "hr_impact_pct": 0.0,
                "k_impact_pct": 0.0,
                "wind_out_mph": 0.0,
                "is_dome": True
            }
        
        # 1. Stadyum bazlı rüzgar güçlendirme çarpanı
        # Wrigley gibi açık ve rüzgara duyarlı sahalar için daha yüksek değer.
        park_wind_scale = {
            "Chi Cubs": 1.8,       # Wrigley Field — en açık, rüzgara duyarlı saha
            "SF Giants": 1.4,      # Oracle Park — körfez rüzgarları
            "Boston": 1.3,         # Fenway Park — Green Monster etkisi
            "Pittsburgh": 1.2,     # PNC Park — nehir kenarı rüzgarı
            "Cleveland": 1.15,     # Progressive Field
            "Philadelphia": 1.1,   # Citizens Bank Park
            "NY Yankees": 1.1,     # Yankee Stadium — rüzgar tüneli etkisi
            "Detroit": 1.05,
            "Kansas City": 1.0,
            "Cincinnati": 1.0,
            "Baltimore": 1.0,
            "Washington": 1.0,
            "St Louis": 0.95,
            "Milwaukee": 0.9,
            "Colorado": 0.75,      # Coors Field — yüksek irtifada hava sıkış etkisi azaltır
        }
        wind_scale = park_wind_scale.get(home_team, 1.0)

        # 2. Hava sıcaklığı, nem ve rakım etkisi
        carry_temp = (temp - 72.0) * 0.35
        carry_altitude = metrics["altitude"] * 0.005
        carry_humid = -(humidity - 50.0) * 0.04
        
        # 3. Rüzgar yönü vektör izdüşümü
        to_dir = direction
        already_to_direction = False
        if " TO " in direction.upper():
            parts = direction.upper().split(" TO ")
            if len(parts) > 1:
                to_dir = parts[1].strip()
                already_to_direction = True  # TO yönü zaten verilmiş
        elif "→" in direction:
            parts = direction.split("→")
            if len(parts) > 1:
                to_dir = parts[1].strip()
                already_to_direction = True
                
        mapping = {
            'N': 0.0, 'NNE': 22.5, 'NE': 45.0, 'ENE': 67.5,
            'E': 90.0, 'ESE': 112.5, 'SE': 135.0, 'SSE': 157.5,
            'S': 180.0, 'SSW': 202.5, 'SW': 225.0, 'WSW': 247.5,
            'W': 270.0, 'WNW': 292.5, 'NW': 315.0, 'NNW': 337.5
        }
        
        wind_angle_raw = mapping.get(to_dir.upper(), 0.0)
        
        # Meteorolojik konvansiyon: tek cardinal yön = rüzgarın GELDİĞİ yön (FROM).
        # Vektör hesabı için rüzgarın GİTTİĞİ yön (TO) gerekir → 180° farkı ekle.
        # Eğer "X TO Y" formatı zaten verilmişse TO yönü doğrudur, dönüşüm yapma.
        if not already_to_direction:
            wind_angle = (wind_angle_raw + 180.0) % 360.0
        else:
            wind_angle = wind_angle_raw
        
        stadium_angle = float(metrics["bearing"])
        
        # Vektör farkı radyan cinsinden
        alpha_rad = math.radians(wind_angle - stadium_angle)
        
        # Merkez sahaya esen rüzgar izdüşümü (Outward wind component)
        # Stadyum-spesifik wind_scale ile çarpılarak park etkisi kalibre edilir
        wind_out = wind * math.cos(alpha_rad)
        carry_wind = wind_out * 1.8 * wind_scale
        
        # Toplam süzülme mesafesi değişimi
        total_carry = carry_temp + carry_humid + carry_wind + carry_altitude
        
        # Kalibre edilmiş yüzesel etkiler
        # Wrigley Field 15 mph tailwind -> ~+32% Runs, ~+58% HR (KevinRothWx referansı)
        runs_impact = total_carry * 0.75
        hr_impact = total_carry * 1.37
        k_impact = -total_carry * 0.1
        
        # Güvenlik sınırı: Aşırı uç değerleri önle
        runs_impact = max(-35.0, min(45.0, runs_impact))
        hr_impact = max(-55.0, min(70.0, hr_impact))
        k_impact = max(-10.0, min(10.0, k_impact))
        
        # Aşırı soğuklarda atıcı parmak tutuşu zorluğu
        if temp < 50.0:
            k_impact = max(-10.0, k_impact - 5.0)
            
        return {
            "ball_carry_ft": round(total_carry, 1),
            "runs_impact_pct": round(runs_impact, 1),
            "hr_impact_pct": round(hr_impact, 1),
            "k_impact_pct": round(k_impact, 1),
            "wind_out_mph": round(wind_out, 1),
            "is_dome": False
        }

    def predict_matchup(self, game: GameInputData, trends: NRFITrendSchema = None, weather: dict = None,
                        away_lineup_avg: dict = None, home_lineup_avg: dict = None,
                        away_splits: dict = None, home_splits: dict = None) -> dict:
        """
        Bütün tahmin motorlarını çalıştırır, mantık hatalarını düzeltir (Safety Check)
        ve FastAPI için uygun JSON payload'unu oluşturur.
        """

        # 1. Modellerin Çalıştırılması
        nrfi_result = self.nrfi_model.calculate(
            game.away_team, game.home_team, game.away_pitcher, game.home_pitcher
        )
        
        # --- KALİBRASYON ENJEKSİYONU ---
        if trends and not trends.is_scraper_fallback:
            # Akıllı Streak Çarpanı (Eksiler YRFI gücünü artırır)
            streak_modifier = min(0.05, (trends.away_pitcher.streak_score + trends.home_pitcher.streak_score) * 0.01)
            
            # Momentum Hesaplaması: Sezon + Stadyum (Location) + Son 10 Maç ortalaması alınır
            a_pitcher = trends.away_pitcher
            h_pitcher = trends.home_pitcher
            away_momentum = ((a_pitcher.season_nrfi_pct + a_pitcher.location_nrfi_pct + a_pitcher.last10_nrfi_pct) / 3 - 50.0) / 100.0
            home_momentum = ((h_pitcher.season_nrfi_pct + h_pitcher.location_nrfi_pct + h_pitcher.last10_nrfi_pct) / 3 - 50.0) / 100.0
            
            team_momentum = (away_momentum + home_momentum) * 0.05
            total_bump = round(streak_modifier + team_momentum, 4)
            
            nrfi_result["nrfi_score"] = round(nrfi_result["nrfi_score"] + total_bump, 4)
            nrfi_result["yrfi_score"] = round(nrfi_result["yrfi_score"] - total_bump, 4)

            # --- YENİ M3.5 GELİŞTİRMELERİ ---
            
            # Görev 12: Vegas O/U <= 8.0 NRFI Boost
            book_total = float(game.odds.get("over_under", 0.0))
            if book_total > 0.0 and book_total <= 8.0:
                boost = (8.5 - book_total) * 0.02
                nrfi_result["nrfi_score"] += boost
                nrfi_result["yrfi_score"] -= boost
                print(f"[Vegas O/U Boost] O/U: {book_total} (<= 8.0). NRFI score boosted by +{boost:.4f}")

            # Görev 13: "Weakest-Link Penalty" (David Peterson Zayıf Atıcı Cezalandırması)
            min_l10 = min(a_pitcher.last10_nrfi_pct, h_pitcher.last10_nrfi_pct)
            if min_l10 < 50.0:
                penalty_factor = (50.0 - min_l10) * 0.006
                penalty_pct = penalty_factor * 100
                nrfi_result["nrfi_score"] = round(nrfi_result["nrfi_score"] * (1.0 - penalty_factor), 4)
                print(f"[Weakest-Link Penalty] Weak Pitcher Detected (L10: {min_l10}% < 50%). NRFI score penalized by {penalty_pct:.1f}%")

            # Yeniden normalize et
            nrfi_result["confidence"] = round(max(nrfi_result["nrfi_score"], nrfi_result["yrfi_score"]), 4)
            nrfi_result["pick"] = "NRFI" if nrfi_result["nrfi_score"] >= nrfi_result["yrfi_score"] else "YRFI"

            # Frontend için raw datayı payload'a mühürle
            nrfi_result["scraped_trends"] = {
                "away_pitcher": a_pitcher.model_dump(),
                "home_pitcher": h_pitcher.model_dump(),
                "away_team_nrfi": trends.away_team_nrfi.model_dump(),
                "home_team_nrfi": trends.home_team_nrfi.model_dump(),
                "is_fallback": False
            }
        else:
            _default_trend = PitcherTrendData()
            nrfi_result["scraped_trends"] = {
                "away_pitcher": _default_trend.model_dump(),
                "home_pitcher": _default_trend.model_dump(),
                "away_team_nrfi": _default_trend.model_dump(),
                "home_team_nrfi": _default_trend.model_dump(),
                "is_fallback": True
            }

        f5_result = self.f5_model.calculate(
            game.away_team, game.home_team, game.away_pitcher, game.home_pitcher
        )
        full_result, raw_pitcher_data = self.mlb_model.calculate(
            game.away_team, game.home_team, game.away_pitcher, game.home_pitcher,
            away_lineup_avg=away_lineup_avg, home_lineup_avg=home_lineup_avg,
            away_splits=away_splits, home_splits=home_splits
        )

        # 2. Değişkenlerin Çıkartılması
        f5_away = f5_result["f5_away_score"]
        f5_home = f5_result["f5_home_score"]
        full_away = full_result["full_away_score"]
        full_home = full_result["full_home_score"]

        # Weather Impact Engine
        weather_impact = self.calculate_weather_impact(weather or {}, game.home_team)
        runs_mult = 1.0 + (weather_impact["runs_impact_pct"] / 100.0)
        
        full_away = round(max(0.5, full_away * runs_mult), 1)
        full_home = round(max(0.5, full_home * runs_mult), 1)

        # Recalculate Pythagorean Win Probabilities after weather adjustment
        if full_away == 0 and full_home == 0:
            away_prob, home_prob = 0.5, 0.5
        else:
            away_pow = full_away**self.mlb_model.offExp
            home_pow = full_home**self.mlb_model.offExp
            total_pow = away_pow + home_pow
            away_prob = away_pow / total_pow
            home_prob = home_pow / total_pow

        full_result.update(
            {
                "full_away_score": full_away,
                "full_home_score": full_home,
                "full_total": round(full_away + full_home, 2),
                "full_away_win_prob": round(away_prob, 3),
                "full_home_win_prob": round(home_prob, 3),
                "full_spread_adv": round(abs(full_home - full_away) - 1.5, 2),
            }
        )

        # 3. SABERMETRİK GÜVENLİK KONTROLÜ (INNING-WEIGHTED CONSTRAINT)
        # Mantık: Bir takım maçın tamamında, ilk 5 inning'de attığı sayıdan daha az sayı atmış olamaz.
        # Bullpen (son 4 inning) en kötü senaryoda bile ham skoru %20 kadar artırması beklenir.
        # Bu, Pythagorean Expectation dağılımını korur ve statik 0.5 hakarete uğratmaz.

        adjusted = False
        model_anomalies = []

        # Away takımı için dinamik kısıt
        if full_away < f5_away:
            floor_away = f5_away + (full_away * 0.2)
            if full_away < floor_away:
                full_away = floor_away
                adjusted = True
                model_anomalies.append("Away team: Sabermetric adjustment applied")

        # Home takımı için dinamik kısıt
        if full_home < f5_home:
            floor_home = f5_home + (full_home * 0.2)
            if full_home < floor_home:
                full_home = floor_home
                adjusted = True
                model_anomalies.append("Home team: Sabermetric adjustment applied")

        # Skorlar düzeltildiyse diğer metrikleri güncelle
        if adjusted:
            full_away = round(full_away, 1)
            full_home = round(full_home, 1)
            away_prob, home_prob = self._recalculate_probabilities(full_away, full_home)

            full_result.update(
                {
                    "full_away_score": full_away,
                    "full_home_score": full_home,
                    "full_total": round(full_away + full_home, 2),
                    "full_away_win_prob": round(away_prob, 3),
                    "full_home_win_prob": round(home_prob, 3),
                    "full_spread_adv": round(abs(full_home - full_away) - 1.5, 2),
                }
            )

        # 3.5 Spread Cover Olasılığı Hesaplama (Normal Dağılım ve CDF - Görev 5)
        # Skor farkı X ~ N(mu, sigma^2) standard sapması sigma = 4.0 run
        mu = full_home - full_away
        sigma = 4.0

        def standard_normal_cdf(val: float) -> float:
            return 0.5 * (1.0 + math.erf(val / math.sqrt(2.0)))

        def normal_cdf(x: float, mean: float, std_dev: float) -> float:
            return standard_normal_cdf((x - mean) / std_dev)

        home_cover_minus_1_5 = round((1 - normal_cdf(1.5, mu, sigma)) * 100, 1)
        home_cover_plus_1_5 = round((1 - normal_cdf(-1.5, mu, sigma)) * 100, 1)
        away_cover_minus_1_5 = round(normal_cdf(-1.5, mu, sigma) * 100, 1)
        away_cover_plus_1_5 = round(normal_cdf(1.5, mu, sigma) * 100, 1)

        full_result.update(
            {
                "home_cover_minus_1_5_prob": home_cover_minus_1_5,
                "home_cover_plus_1_5_prob": home_cover_plus_1_5,
                "away_cover_minus_1_5_prob": away_cover_minus_1_5,
                "away_cover_plus_1_5_prob": away_cover_plus_1_5,
            }
        )

        # 4. Value Bet Yakalayıcı (Market Oranlarına Karşı)
        value_alerts = []
        book_total = game.odds.get("over_under", 0)
        if book_total > 0:
            diff = abs(full_result["full_total"] - book_total)
            if diff > 0.7:
                value_alerts.append("🔥 SIGNIFICANT TOTAL EDGE")

        # Extract advanced team metrics for AI analysis
        away_t = self.team_db.get(game.away_team, {})
        home_t = self.team_db.get(game.home_team, {})
        team_analysis = {
            "away": {
                "wrc_plus": away_t.get("advanced_metrics", {}).get("wrc_plus", 100.0),
                "off_current": away_t.get("rpg_offense", {}).get("current", 4.5),
                "off_last3": away_t.get("rpg_offense", {}).get("last_3", 4.5),
                "def_current": away_t.get("rpg_defense", {}).get("current", 4.5),
            },
            "home": {
                "wrc_plus": home_t.get("advanced_metrics", {}).get("wrc_plus", 100.0),
                "off_current": home_t.get("rpg_offense", {}).get("current", 4.5),
                "off_last3": home_t.get("rpg_offense", {}).get("last_3", 4.5),
                "def_current": home_t.get("rpg_defense", {}).get("current", 4.5),
            }
        }

        # 5. Frontend İçin Nihai JSON Payload
        return {
            "matchup": {
                "away_team": game.away_team,
                "home_team": game.home_team,
                "away_pitcher": game.away_pitcher,
                "home_pitcher": game.home_pitcher,
                "game_time": game.game_time,
                "away_stats": game.away_team_stats,
                "home_stats": game.home_team_stats,
                "status": game.status,
            },
            "NRFI": nrfi_result,
            "F5": f5_result,
            "Full_Game": full_result,
            "Details": {
                "pitcher_analysis": raw_pitcher_data,
                "team_analysis": team_analysis,
                "value_alerts": value_alerts,
                "model_anomalies": model_anomalies,
                "weather_impact": weather_impact,
            },
        }

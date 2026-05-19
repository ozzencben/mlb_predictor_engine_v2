import asyncio
import httpx
import json
import os
import tempfile

class WeatherAnalyzer:
    """Hava durumu verilerinden UI için risk uyarıları ve kırmızı bayraklar üretir."""
    
    @staticmethod
    def generate_alerts(temp: float, wind: float, condition: str, is_dome: bool = False) -> dict:
        condition_lower = condition.lower()
        is_red_flag = False
        alert_word = "Clear"

        if is_dome:
            return {"cbs_alert_word": "Ideal (Dome)", "red_flag_alert": False}

        # 1. Yağış/Fırtına Kontrolü (Red Flag)
        if any(keyword in condition_lower for keyword in ["rain", "storm", "thunder", "shower", "snow"]):
            is_red_flag = True
            alert_word = "Nasty Weather"
        
        # 2. Şiddetli Rüzgar Kontrolü
        elif wind >= 15.0:
            is_red_flag = True
            alert_word = "High Wind"
        
        # 3. Aşırı Sıcak/Soğuk
        elif temp <= 45.0:
            alert_word = "Chilly"
        elif temp >= 95.0:
            alert_word = "Hot"
        
        # 4. Kapalı Hava
        elif "overcast" in condition_lower or "cloud" in condition_lower:
            alert_word = "Overcast"

        return {
            "cbs_alert_word": alert_word,
            "red_flag_alert": is_red_flag
        }


class WeatherScraper:
    """
    Maçların oynanacağı stadyumların GPS koordinatlarına göre
    Open-Meteo (Ücretsiz) API'sinden canlı hava durumunu çeker.
    """

    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)
        self.base_url = "https://api.open-meteo.com/v1/forecast"

        # TCP/SSL Handshake maliyetini düşürmek için httpx Client kullanımı
        self.session = httpx.Client()

        ballpark_file = os.path.join(self.data_dir, "ballpark_stats.json")
        try:
            with open(ballpark_file, "r", encoding="utf-8") as f:
                self.ballpark_db = json.load(f)
        except FileNotFoundError:
            print("❌ HATA: ballpark_stats.json bulunamadı.")
            self.ballpark_db = {}

        # Hata durumunda modeli patlatmayacak standart/nötr hava durumu
        self.fallback_weather = {
            "temp_f": 72.0,
            "wind_mph": 0.0,
            "wind_direction": "Calm",
            "humidity": 50,
            "condition": "Unknown",
        }

    def _atomic_save(self, filepath: str, data: dict):
        """Dosyanın bozulmasını önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def get_weather_description(self, weather_code: int) -> str:
        codes = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing Rime Fog", 51: "Light Drizzle",
            53: "Moderate Drizzle", 55: "Dense Drizzle", 61: "Slight Rain",
            63: "Moderate Rain", 65: "Heavy Rain", 71: "Slight Snow",
            73: "Moderate Snow", 75: "Heavy Snow", 95: "Thunderstorm",
            96: "Thunderstorm & Hail", 99: "Heavy Thunderstorm",
        }
        return codes.get(weather_code, "Unknown")

    def get_wind_direction(self, degrees: float) -> str:
        val = int((degrees / 22.5) + 0.5)
        arr = [
            "N to S", "NNE to SSW", "NE to SW", "ENE to WSW", "E to W",
            "ESE to WNW", "SE to NW", "SSE to NNW", "S to N", "SSW to NNE",
            "SW to NE", "WSW to ENE", "W to E", "WNW to ESE", "NW to SE", "NNW to SSE",
        ]
        return arr[(val % 16)]

    def fetch_todays_weather(self, matchups_data: dict) -> dict:
        print("☁️ Stadyumların canlı hava durumu verileri çekiliyor... (Senkron)")

        weather_data = {}
        games = matchups_data if isinstance(matchups_data, list) else matchups_data.get("games", [])

        if not games:
            print("⚠️ Hava durumu çekilecek maç bulunamadı.")
            return {}

        for game in games:
            home_team = game["home_team"]
            park_info = self.ballpark_db.get(home_team)

            if not park_info or "lat" not in park_info:
                print(f"⚠️ {home_team} stadyum koordinatları bulunamadı, varsayılan atanıyor.")
                fallback = self.fallback_weather.copy()
                fallback.update(WeatherAnalyzer.generate_alerts(72.0, 0.0, "Unknown"))
                weather_data[home_team] = fallback
                continue

            roof_type = park_info.get("roof_type", "Open")

            if roof_type == "Dome":
                weather_data[home_team] = {
                    "temp_f": 72.0,
                    "wind_mph": 0.0,
                    "wind_direction": "Calm (Dome)",
                    "humidity": 50,
                    "condition": "Climate Controlled",
                    **WeatherAnalyzer.generate_alerts(72.0, 0.0, "Climate Controlled", is_dome=True)
                }
                continue

            params = {
                "latitude": park_info["lat"],
                "longitude": park_info["lon"],
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto",
            }

            try:
                response = self.session.get(self.base_url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                current = data.get("current", {})
                temp = float(current.get("temperature_2m", 72.0))
                wind_mph = float(current.get("wind_speed_10m", 0.0))
                wind_deg = float(current.get("wind_direction_10m", 0.0))
                humidity = float(current.get("relative_humidity_2m", 50.0))
                w_code = int(current.get("weather_code", 0))

                condition = self.get_weather_description(w_code)
                wind_dir_str = self.get_wind_direction(wind_deg)

                if roof_type == "Retractable" and any(x in condition for x in ["Rain", "Snow", "Thunderstorm"]):
                    condition = f"Roof Closed (Expected {condition})"
                    wind_mph = 0.0
                    wind_dir_str = "Calm (Roof Closed)"
                    alerts = {"cbs_alert_word": "Ideal (Roof Closed)", "red_flag_alert": False}
                else:
                    alerts = WeatherAnalyzer.generate_alerts(temp, wind_mph, condition)

                weather_data[home_team] = {
                    "temp_f": round(temp, 1),
                    "wind_mph": round(wind_mph, 1),
                    "wind_direction": wind_dir_str,
                    "humidity": humidity,
                    "condition": condition,
                    **alerts
                }

            except Exception as e:
                print(f"❌ {home_team} Hava Durumu Hatası: {e}. Varsayılan değer atanıyor.")
                fallback = self.fallback_weather.copy()
                fallback.update(WeatherAnalyzer.generate_alerts(72.0, 0.0, "Unknown"))
                weather_data[home_team] = fallback

        output_path = os.path.join(self.data_dir, "live_weather.json")
        self._atomic_save(output_path, weather_data)

        print(f"🎉 Toplam {len(weather_data)} stadyumun hava durumu başarıyla güncellendi.")
        return weather_data

    async def fetch_todays_weather_async(self, client: httpx.AsyncClient, matchups_data: dict) -> dict:
        print("☁️ Stadyumların canlı hava durumu verileri çekiliyor... (Asenkron)")

        weather_data = {}
        games = matchups_data if isinstance(matchups_data, list) else matchups_data.get("games", [])

        if not games:
            print("⚠️ Hava durumu çekilecek maç bulunamadı.")
            return {}

        for game in games:
            home_team = game["home_team"]
            park_info = self.ballpark_db.get(home_team)

            if not park_info or "lat" not in park_info:
                print(f"⚠️ {home_team} stadyum koordinatları bulunamadı, varsayılan atanıyor.")
                fallback = self.fallback_weather.copy()
                fallback.update(WeatherAnalyzer.generate_alerts(72.0, 0.0, "Unknown"))
                weather_data[home_team] = fallback
                continue

            roof_type = park_info.get("roof_type", "Open")

            if roof_type == "Dome":
                weather_data[home_team] = {
                    "temp_f": 72.0,
                    "wind_mph": 0.0,
                    "wind_direction": "Calm (Dome)",
                    "humidity": 50,
                    "condition": "Climate Controlled",
                    **WeatherAnalyzer.generate_alerts(72.0, 0.0, "Climate Controlled", is_dome=True)
                }
                continue

            params = {
                "latitude": park_info["lat"],
                "longitude": park_info["lon"],
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto",
            }

            try:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()

                current = data.get("current", {})
                temp = float(current.get("temperature_2m", 72.0))
                wind_mph = float(current.get("wind_speed_10m", 0.0))
                wind_deg = float(current.get("wind_direction_10m", 0.0))
                humidity = float(current.get("relative_humidity_2m", 50.0))
                w_code = int(current.get("weather_code", 0))

                condition = self.get_weather_description(w_code)
                wind_dir_str = self.get_wind_direction(wind_deg)

                if roof_type == "Retractable" and any(x in condition for x in ["Rain", "Snow", "Thunderstorm"]):
                    condition = f"Roof Closed (Expected {condition})"
                    wind_mph = 0.0
                    wind_dir_str = "Calm (Roof Closed)"
                    alerts = {"cbs_alert_word": "Ideal (Roof Closed)", "red_flag_alert": False}
                else:
                    alerts = WeatherAnalyzer.generate_alerts(temp, wind_mph, condition)

                weather_data[home_team] = {
                    "temp_f": round(temp, 1),
                    "wind_mph": round(wind_mph, 1),
                    "wind_direction": wind_dir_str,
                    "humidity": humidity,
                    "condition": condition,
                    **alerts
                }

            except Exception as e:
                print(f"❌ {home_team} Hava Durumu Hatası: {e}. Varsayılan değer atanıyor.")
                fallback = self.fallback_weather.copy()
                fallback.update(WeatherAnalyzer.generate_alerts(72.0, 0.0, "Unknown"))
                weather_data[home_team] = fallback

        output_path = os.path.join(self.data_dir, "live_weather.json")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._atomic_save, output_path, weather_data)

        print(f"🎉 Toplam {len(weather_data)} stadyumun hava durumu başarıyla güncellendi.")
        return weather_data
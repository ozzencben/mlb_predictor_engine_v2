import requests
import json
import os
import tempfile

class WeatherScraper:
    """
    Maçların oynanacağı stadyumların GPS koordinatlarına göre
    Open-Meteo (Ücretsiz) API'sinden canlı hava durumunu çeker.
    """
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        
        # TCP bağlantı havuzu (Hız optimizasyonu)
        self.session = requests.Session()
        
        ballpark_file = os.path.join(self.data_dir, 'ballpark_stats.json')
        try:
            with open(ballpark_file, 'r', encoding='utf-8') as f:
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
            "condition": "Unknown"
        }

    def _atomic_save(self, filepath: str, data: dict):
        """Dosyanın bozulmasını önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def get_weather_description(self, weather_code: int) -> str:
        codes = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing Rime Fog",
            51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
            61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            71: "Slight Snow", 73: "Moderate Snow", 75: "Heavy Snow",
            95: "Thunderstorm", 96: "Thunderstorm & Hail", 99: "Heavy Thunderstorm"
        }
        return codes.get(weather_code, "Unknown")

    def get_wind_direction(self, degrees: float) -> str:
        val = int((degrees / 22.5) + .5)
        arr = ["N to S", "NNE to SSW", "NE to SW", "ENE to WSW", 
               "E to W", "ESE to WNW", "SE to NW", "SSE to NNW", 
               "S to N", "SSW to NNE", "SW to NE", "WSW to ENE", 
               "W to E", "WNW to ESE", "NW to SE", "NNW to SSE"]
        return arr[(val % 16)]

    def fetch_todays_weather(self, matchups_data: dict) -> dict:
        print("☁️ Stadyumların canlı hava durumu verileri çekiliyor...")
        
        weather_data = {}
        games = matchups_data.get('games', [])
        
        if not games:
            print("⚠️ Hava durumu çekilecek maç bulunamadı.")
            return {}

        for game in games:
            home_team = game['home_team']
            park_info = self.ballpark_db.get(home_team)
            
            if not park_info or 'lat' not in park_info:
                print(f"⚠️ {home_team} stadyum koordinatları bulunamadı, varsayılan atanıyor.")
                weather_data[home_team] = self.fallback_weather.copy()
                continue
                
            roof_type = park_info.get('roof_type', 'Open')
            
            if roof_type == "Dome":
                weather_data[home_team] = {
                    "temp_f": 72.0,
                    "wind_mph": 0.0,
                    "wind_direction": "Calm (Dome)",
                    "humidity": 50,
                    "condition": "Climate Controlled"
                }
                continue

            params = {
                "latitude": park_info['lat'],
                "longitude": park_info['lon'],
                "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto"
            }
            
            try:
                # Session kullanılarak hız artırıldı
                response = self.session.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                current = data.get('current', {})
                temp = float(current.get('temperature_2m', 72.0))
                wind_mph = float(current.get('wind_speed_10m', 0.0))
                wind_deg = float(current.get('wind_direction_10m', 0.0))
                humidity = float(current.get('relative_humidity_2m', 50.0))
                w_code = int(current.get('weather_code', 0))
                
                condition = self.get_weather_description(w_code)
                wind_dir_str = self.get_wind_direction(wind_deg)
                
                if roof_type == "Retractable" and ("Rain" in condition or "Snow" in condition or "Thunderstorm" in condition):
                    condition = f"Roof Closed (Expected {condition})"
                    wind_mph = 0.0
                    wind_dir_str = "Calm (Roof Closed)"
                        
                weather_data[home_team] = {
                    "temp_f": round(temp, 1),
                    "wind_mph": round(wind_mph, 1),
                    "wind_direction": wind_dir_str,
                    "humidity": humidity,
                    "condition": condition
                }
                
            except Exception as e:
                print(f"❌ {home_team} Hava Durumu Hatası: {e}. Varsayılan değer atanıyor.")
                # Modelin çökmesini engellemek için hata metni yerine sayısal fallback atanıyor
                weather_data[home_team] = self.fallback_weather.copy()

        output_path = os.path.join(self.data_dir, 'live_weather.json')
        self._atomic_save(output_path, weather_data)
            
        print(f"🎉 Toplam {len(weather_data)} stadyumun hava durumu başarıyla güncellendi.")
        return weather_data
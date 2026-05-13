import requests
import json
import os
from datetime import datetime

class WeatherScraper:
    """
    Maçların oynanacağı stadyumların GPS koordinatlarına göre
    Open-Meteo (Ücretsiz) API'sinden maç saatindeki canlı hava durumunu çeker.
    """
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        
        # Stadyum koordinatlarını yükle
        ballpark_file = os.path.join(self.data_dir, 'ballpark_stats.json')
        try:
            with open(ballpark_file, 'r', encoding='utf-8') as f:
                self.ballpark_db = json.load(f)
        except FileNotFoundError:
            print("❌ HATA: ballpark_stats.json bulunamadı. Lütfen stadyum koordinatlarını ekleyin.")
            self.ballpark_db = {}

    def get_weather_description(self, weather_code):
        """WMO (Dünya Meteoroloji Örgütü) kodlarını metne çevirir."""
        codes = {
            0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing Rime Fog",
            51: "Light Drizzle", 53: "Moderate Drizzle", 55: "Dense Drizzle",
            61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            71: "Slight Snow", 73: "Moderate Snow", 75: "Heavy Snow",
            95: "Thunderstorm", 96: "Thunderstorm & Hail", 99: "Heavy Thunderstorm"
        }
        return codes.get(weather_code, "Unknown")

    def get_wind_direction(self, degrees):
        """Rüzgarın derecesini yön metnine (Örn: N to S, SW to NE) çevirir."""
        val = int((degrees / 22.5) + .5)
        arr = ["N to S", "NNE to SSW", "NE to SW", "ENE to WSW", 
               "E to W", "ESE to WNW", "SE to NW", "SSE to NNW", 
               "S to N", "SSW to NNE", "SW to NE", "WSW to ENE", 
               "W to E", "WNW to ESE", "NW to SE", "NNW to SSE"]
        return arr[(val % 16)]

    def fetch_todays_weather(self, matchups_data):
        """Bugünün maç listesini alır ve her stadyum için hava durumunu çeker."""
        print("☁️ Stadyumların canlı hava durumu verileri çekiliyor...")
        
        weather_data = {}
        games = matchups_data.get('games', [])
        
        if not games:
            print("⚠️ Hava durumu çekilecek maç bulunamadı.")
            return {}

        for game in games:
            home_team = game['home_team']
            
            # Stadyum verilerini al
            park_info = self.ballpark_db.get(home_team)
            if not park_info or 'lat' not in park_info:
                print(f"⚠️ {home_team} stadyum koordinatları bulunamadı, atlanıyor.")
                continue
                
            roof_type = park_info.get('roof_type', 'Open')
            
            # Eğer stadyum tamamen kapalıysa (Dome) hava durumunun maça etkisi yoktur
            if roof_type == "Dome":
                weather_data[home_team] = {
                    "temp_f": 72.0, # Standart oda sıcaklığı
                    "wind_mph": 0.0,
                    "wind_direction": "Calm (Dome)",
                    "humidity": 50,
                    "condition": "Climate Controlled"
                }
                print(f"✅ {home_team} (Dome - İklimlendirmeli)")
                continue

            lat = park_info['lat']
            lon = park_info['lon']
            
            # API İstek Parametreleri (Saatlik veri istiyoruz)
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "auto"
            }
            
            try:
                response = requests.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                current = data.get('current', {})
                temp = current.get('temperature_2m', 0)
                wind_mph = current.get('wind_speed_10m', 0)
                wind_deg = current.get('wind_direction_10m', 0)
                humidity = current.get('relative_humidity_2m', 0)
                w_code = current.get('weather_code', 0)
                
                # Açılır kapanır çatı mantığı (Yağmur varsa çatı kapanır)
                condition = self.get_weather_description(w_code)
                wind_dir_str = self.get_wind_direction(wind_deg)
                
                if roof_type == "Retractable":
                    if "Rain" in condition or "Snow" in condition or "Thunderstorm" in condition:
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
                print(f"✅ {home_team} ({weather_data[home_team]['temp_f']}°F, {weather_data[home_team]['wind_mph']} mph {wind_dir_str})")
                
            except Exception as e:
                print(f"❌ {home_team} Hava Durumu Hatası: {e}")
                weather_data[home_team] = {"error": "Veri Çekilemedi"}

        # Veriyi kaydet
        output_path = os.path.join(self.data_dir, 'live_weather.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(weather_data, f, indent=4, ensure_ascii=False)
            
        print(f"🎉 Toplam {len(weather_data)} stadyumun hava durumu live_weather.json dosyasına kaydedildi.")
        return weather_data

if __name__ == "__main__":
    # Test etmek için matchups verisini simüle edelim veya dosyadan okuyalım
    scraper = WeatherScraper()
    matchups_file = os.path.join(scraper.data_dir, 'daily_matchups.json')
    if os.path.exists(matchups_file):
        with open(matchups_file, 'r') as f:
            matchups = json.load(f)
            scraper.fetch_todays_weather(matchups)
    else:
        print("Test için daily_matchups.json gerekiyor.")
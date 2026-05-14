import requests
import json
import os
import tempfile
from dotenv import load_dotenv

load_dotenv()

class OddsProvider:
    """
    The Odds API'den canlı oranları çeker, takımları eşleştirir ve
    modelimiz için "The Edge" (Değer/Avantaj) hesaplaması yapar.
    Ayrıca Tyler'ın istediği Bookie O/U (Alt/Üst) baremlerini çeker.
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY")

        if not self.api_key:
            print("❌ HATA: ODDS_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")

        self.base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        
        mapping_file = os.path.join(self.data_dir, 'team_mappings.json')
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ Uyarı: team_mappings.json bulunamadı.")
            self.mlb_to_tr_map = {}

    def _atomic_save(self, filepath: str, data: list):
        """Dosya kilitleme ve bozulmaları önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def fetch_live_odds(self, regions="us", markets="h2h,totals") -> list:
        """API'den taze oranları çeker, JSON olarak atomik kaydeder."""
        if not self.api_key:
            return []

        print("💰 The Odds API'den canlı bahis oranları (ML) ve Alt/Üst baremleri çekiliyor...")
        
        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': markets, 
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            odds_data = response.json()
            
            if not odds_data:
                 print("ℹ️ Şu an için The Odds API'den veri dönmedi (Maç yok veya Piyasalar kapalı).")
                 return []
            
            output_path = os.path.join(self.data_dir, 'live_odds.json')
            self._atomic_save(output_path, odds_data)
                
            print(f"✅ Başarılı! {len(odds_data)} maçın güncel oranları live_odds.json dosyasına yazıldı.")
            return odds_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Oranlar çekilirken API Hatası: {e}")
            return []

    def get_best_odds_for_game(self, away_team_tr: str, home_team_tr: str, odds_data: list) -> dict:
        """
        Piyasadaki en yüksek taraf (H2H) oranlarını ve genel Alt/Üst (Total) baremini bulur.
        Zaman karmaşıklığı optimize edildi.
        """
        result = {
            "away_odds": 0.0,
            "home_odds": 0.0,
            "over_under": 0.0
        }
        
        if not odds_data:
            return result

        for game in odds_data:
            api_away_tr = self.mlb_to_tr_map.get(game['away_team'], game['away_team'])
            api_home_tr = self.mlb_to_tr_map.get(game['home_team'], game['home_team'])
            
            if api_away_tr == away_team_tr and api_home_tr == home_team_tr:
                bookmakers = game.get('bookmakers', [])
                
                for bookie in bookmakers:
                    for market in bookie.get('markets', []):
                        # 1. Taraf Oranları (Moneyline) - En yükseği bulur
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome['name'], outcome['name'])
                                price = float(outcome.get('price', 0))
                                
                                if outcome_name_tr == away_team_tr and price > result["away_odds"]:
                                    result["away_odds"] = price
                                elif outcome_name_tr == home_team_tr and price > result["home_odds"]:
                                    result["home_odds"] = price
                                    
                        # 2. Alt/Üst (Totals) Baremi - Sadece ilk ana baremi alır
                        elif market['key'] == 'totals' and result["over_under"] == 0.0:
                            for outcome in market['outcomes']:
                                if 'point' in outcome:
                                    result["over_under"] = float(outcome['point'])
                                    break # Ana döngüden değil, sadece bu market'ten çık.
                # Hedef maçı bulduğumuz için diğer maçlara bakmaya gerek yok
                break 
        
        return result

    def convert_decimal_to_prob(self, decimal_odds: float) -> float:
        if decimal_odds <= 1.0: return 0.0
        return round(1.0 / decimal_odds, 3)

    def calculate_edge(self, model_prob: float, market_odds: float) -> float:
        market_prob = self.convert_decimal_to_prob(market_odds)
        if market_prob == 0.0: return 0.0
        return round(model_prob - market_prob, 3)
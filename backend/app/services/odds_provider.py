import requests
import json
import os
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
        
        mapping_file = os.path.join(self.data_dir, 'team_mappings.json')
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ Uyarı: team_mappings.json bulunamadı.")
            self.mlb_to_tr_map = {}

    # DİKKAT: markets parametresine 'totals' eklendi!
    def fetch_live_odds(self, regions="us", markets="h2h,totals"):
        """API'den taze oranları ve baremleri çeker, JSON olarak kaydeder."""
        print("💰 The Odds API'den canlı bahis oranları (ML) ve Alt/Üst baremleri çekiliyor...")
        
        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': markets, 
            'oddsFormat': 'decimal'
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            odds_data = response.json()
            
            output_path = os.path.join(self.data_dir, 'live_odds.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(odds_data, f, indent=4, ensure_ascii=False)
                
            print(f"✅ Başarılı! {len(odds_data)} maçın güncel oranları live_odds.json dosyasına yazıldı.")
            return odds_data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Oranlar çekilirken API Hatası: {e}")
            return []

    def get_best_odds_for_game(self, away_team_tr: str, home_team_tr: str, odds_data: list) -> dict:
        """
        Piyasadaki en yüksek taraf (H2H) oranlarını ve genel Alt/Üst (Total) baremini bulur.
        """
        best_away_odds = 0.0
        best_home_odds = 0.0
        bookie_total = 0.0 # Tyler'ın istediği O/U baremi
        
        for game in odds_data:
            api_away_tr = self.mlb_to_tr_map.get(game['away_team'], game['away_team'])
            api_home_tr = self.mlb_to_tr_map.get(game['home_team'], game['home_team'])
            
            if api_away_tr == away_team_tr and api_home_tr == home_team_tr:
                bookmakers = game.get('bookmakers', [])
                
                for bookie in bookmakers:
                    for market in bookie.get('markets', []):
                        # 1. Taraf Oranları (Moneyline)
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome['name'], outcome['name'])
                                price = float(outcome['price'])
                                
                                if outcome_name_tr == away_team_tr and price > best_away_odds:
                                    best_away_odds = price
                                elif outcome_name_tr == home_team_tr and price > best_home_odds:
                                    best_home_odds = price
                                    
                        # 2. YENİ EKLENDİ: Alt/Üst (Totals) Baremi
                        elif market['key'] == 'totals' and bookie_total == 0.0:
                            # Sadece ilk bulduğumuz ana baremi alıyoruz (Örn: 8.5)
                            for outcome in market['outcomes']:
                                if 'point' in outcome:
                                    bookie_total = float(outcome['point'])
                                    break
                break 
        
        return {
            "away_odds": best_away_odds,
            "home_odds": best_home_odds,
            "over_under": bookie_total # Barem de döndürülüyor
        }

    def convert_decimal_to_prob(self, decimal_odds: float) -> float:
        if decimal_odds <= 1.0: return 0.0
        return round(1.0 / decimal_odds, 3)

    def calculate_edge(self, model_prob: float, market_odds: float) -> float:
        market_prob = self.convert_decimal_to_prob(market_odds)
        if market_prob == 0.0: return 0.0
        return round(model_prob - market_prob, 3)

if __name__ == "__main__":
    provider = OddsProvider()
    provider.fetch_live_odds()
import requests
import json
import os

class OddsProvider:
    """
    The Odds API'den canlı oranları çeker, takımları eşleştirir ve
    modelimiz için "The Edge" (Değer/Avantaj) hesaplaması yapar.
    """
    def __init__(self, api_key: str = "0d0dc3ee89d686ebd81213ac126c9af6"):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        # Mapping dosyasını oku (Odds API tam isim kullanır, TR isimlerine çevirmeliyiz)
        mapping_file = os.path.join(self.data_dir, 'team_mappings.json')
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ Uyarı: team_mappings.json bulunamadı.")
            self.mlb_to_tr_map = {}

    def fetch_live_odds(self, regions="us", markets="h2h"):
        """API'den taze oranları çeker ve JSON olarak kaydeder."""
        print("💰 The Odds API'den canlı bahis oranları (Moneyline) çekiliyor...")
        
        params = {
            'apiKey': self.api_key,
            'regions': regions,      # Sadece Amerika büroları (DraftKings, FanDuel vb.)
            'markets': markets,      # h2h = Head to Head (Maç Sonucu ML)
            'oddsFormat': 'decimal'  # Matematik için en kolay format (Örn: 1.90)
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
        live_odds.json içinden ilgili maçı bulur ve piyasadaki EN YÜKSEK (Best) oranları döndürür.
        """
        best_away_odds = 0.0
        best_home_odds = 0.0
        
        for game in odds_data:
            # API'den gelen tam isimleri bizim TR isimlerine çevir
            api_away_tr = self.mlb_to_tr_map.get(game['away_team'], game['away_team'])
            api_home_tr = self.mlb_to_tr_map.get(game['home_team'], game['home_team'])
            
            # Eşleşme bulundu mu?
            if api_away_tr == away_team_tr and api_home_tr == home_team_tr:
                bookmakers = game.get('bookmakers', [])
                
                for bookie in bookmakers:
                    for market in bookie.get('markets', []):
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome['name'], outcome['name'])
                                price = float(outcome['price'])
                                
                                # Piyasada sunulan en yüksek oranı bul (Line Shopping)
                                if outcome_name_tr == away_team_tr and price > best_away_odds:
                                    best_away_odds = price
                                elif outcome_name_tr == home_team_tr and price > best_home_odds:
                                    best_home_odds = price
                break # Maç bulundu, diğerlerine bakmaya gerek yok
        
        return {
            "away_odds": best_away_odds,
            "home_odds": best_home_odds
        }

    def convert_decimal_to_prob(self, decimal_odds: float) -> float:
        """Büro oranını gizli olasılığa çevirir (Örn: 1.90 oranı -> 0.526 / %52.6)."""
        if decimal_odds <= 1.0:
            return 0.0
        return round(1.0 / decimal_odds, 3)

    def calculate_edge(self, model_prob: float, market_odds: float) -> float:
        """
        Modelin olasılığı ile büronun gizli olasılığı arasındaki farkı (Edge) hesaplar.
        Pozitif değer = Value Bet (Değerli Bahis)
        """
        market_prob = self.convert_decimal_to_prob(market_odds)
        if market_prob == 0.0:
            return 0.0
        
        # Edge'i decimal formda döndür (Örn: 0.05 -> %5 Edge)
        return round(model_prob - market_prob, 3)

if __name__ == "__main__":
    provider = OddsProvider()
    provider.fetch_live_odds()
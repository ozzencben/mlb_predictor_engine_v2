import asyncio
from dotenv import load_dotenv

# .env dosyasındaki değişkenleri yükle
load_dotenv()

from app.services.ai.factory import get_ai_predictor

async def test_ai_layer():
    # Factory üzerinden sağlayıcıyı (Gemini) ayağa kaldır
    ai_service = get_ai_predictor()
    
    # Sistemin motordan çıkardığı gerçek JSON formatı (Mock Data)
    mock_prediction = {
        "matchup": {
            "away_team": "Cleveland",
            "home_team": "Detroit",
            "status": "Scheduled"
        },
        "NRFI": {
            "confidence": 0.604,
            "pick": "NRFI",
            "scraped_trends": {
                "away_pitcher": {
                    "season_nrfi_pct": 78.1,
                    "location_nrfi_pct": 81.5,
                    "last10_nrfi_pct": 60.0,
                    "streak_score": 2
                },
                "home_pitcher": {
                    "season_nrfi_pct": 65.0,
                    "location_nrfi_pct": 73.6,
                    "last10_nrfi_pct": 70.0,
                    "streak_score": 0
                }
            }
        },
        "Full_Game": {
            "full_away_score": 5.6,
            "full_home_score": 3.6,
            "full_total": 9.2,
            "full_away_win_prob": 0.692,
            "full_home_win_prob": 0.308
        },
        "Odds": {
            "over_under": 8.0,
            "away_edge_pct": 25.7,
            "home_edge_pct": -28.0
        },
        "Weather": {
            "temp_f": 87.8,
            "wind_mph": 13.8,
            "wind_direction": "SSW to NNE",
            "condition": "Mainly Clear"
        },
        "Details": {
            "pitcher_analysis": {
                "away": {"fip": 4.91, "k_bb_pct": 0.102},
                "home": {"fip": 3.79, "k_bb_pct": 0.112}
            }
        }
    }

    print("🤖 Yapay Zeka servisi tetikleniyor...\n" + "="*50)
    
    # Asenkron isteği at
    insight = await ai_service.generate_insight_async(mock_prediction)
    
    print("\n📝 [SONUÇ] AI Insight Çıktısı:")
    print("-" * 50)
    print(insight)
    print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_ai_layer())
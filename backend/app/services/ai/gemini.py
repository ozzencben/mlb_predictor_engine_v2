import os
from google import genai
from app.services.ai.base import BaseAIPredictor
from app.core.config import settings

class GeminiPredictor(BaseAIPredictor):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = 'gemini-1.5-flash'
        else:
            self.client = None

    async def generate_insight_async(self, prediction_data: dict) -> str:
        if not self.client:
            return "AI analysis currently unavailable (API Key missing)."

        # Sistemin JSON yapısına (todays_predictions.json) sadık kalarak veri çekimi
        matchup = prediction_data.get("matchup", {})
        full = prediction_data.get("Full_Game", {})
        odds = prediction_data.get("Odds", {})
        nrfi = prediction_data.get("NRFI", {})
        weather = prediction_data.get("Weather", {})
        
        # Trend verileri için güvenli çekim (fallback durumu göz önüne alınarak)
        trends = nrfi.get("scraped_trends", {})
        is_fallback = trends.get("is_fallback", True)
        
        # Trend verileri varsa al, yoksa N/A ata
        a_pitcher = trends.get("away_pitcher", {}) if not is_fallback else {"location_nrfi_pct": "N/A", "streak_score": "N/A", "season_record": "N/A", "location_record": "N/A", "last10_record": "N/A", "streak_emoji": ""}
        h_pitcher = trends.get("home_pitcher", {}) if not is_fallback else {"location_nrfi_pct": "N/A", "streak_score": "N/A", "season_record": "N/A", "location_record": "N/A", "last10_record": "N/A", "streak_emoji": ""}
        a_team_nrfi = trends.get("away_team_nrfi", {}) if not is_fallback else {"season_nrfi_pct": "N/A", "season_record": "N/A"}
        h_team_nrfi = trends.get("home_team_nrfi", {}) if not is_fallback else {"season_nrfi_pct": "N/A", "season_record": "N/A"}

        # LLM için Rafine Bağlam (Context) Paketi
        context = (
            f"Matchup: {matchup.get('away_team')} vs {matchup.get('home_team')}\n"
            f"Full Game Proj: {full.get('full_away_score')}-{full.get('full_home_score')} (Total: {full.get('full_total')}).\n"
            f"Vegas Lines: O/U {odds.get('over_under', 'N/A')}. Away ML Edge: {odds.get('away_edge_pct', '0')}%, Home ML Edge: {odds.get('home_edge_pct', '0')}%.\n"
            f"NRFI Confidence: {nrfi.get('confidence')} (Pick: {nrfi.get('pick')}).\n"
            f"Away SP: Loc NRFI {a_pitcher.get('location_nrfi_pct')}% ({a_pitcher.get('location_record')}), Season Record: {a_pitcher.get('season_record')}, L10: {a_pitcher.get('last10_record')}, Streak: {a_pitcher.get('streak_score')} {a_pitcher.get('streak_emoji')}.\n"
            f"Home SP: Loc NRFI {h_pitcher.get('location_nrfi_pct')}% ({h_pitcher.get('location_record')}), Season Record: {h_pitcher.get('season_record')}, L10: {h_pitcher.get('last10_record')}, Streak: {h_pitcher.get('streak_score')} {h_pitcher.get('streak_emoji')}.\n"
            f"Away Team Offense NRFI: {a_team_nrfi.get('season_nrfi_pct')}% ({a_team_nrfi.get('season_record')}).\n"
            f"Home Team Offense NRFI: {h_team_nrfi.get('season_nrfi_pct')}% ({h_team_nrfi.get('season_record')}).\n"
            f"Weather: {weather.get('temp_f', 'N/A')}F, Wind {weather.get('wind_mph', 'N/A')}mph {weather.get('wind_direction', 'N/A')}. Alert: {weather.get('cbs_alert_word', 'None')} (Red Flag: {weather.get('red_flag_alert', False)})."
        )

        # Tyler'ın İstediği Katı "Covers" Stili System Instruction
        prompt = f"""
        You are a highly analytical, professional MLB Sabermetrics expert providing betting insights for a high-end sports betting terminal.
        Your task is to analyze the provided data and return EXACTLY 3 BULLET POINTS. Do not use conversational filler (e.g., "Here is the analysis," "Hi there").

        Follow this strict structure using markdown bullet points (-):
        - Bullet 1 (Anomaly/Pitching): Identify the most significant statistical edge or anomaly, focusing on run projections or recent trends.
        - Bullet 2 (Trends/Environment): State how the specific Ballpark Weather (Wind/Temp) or the pitchers' NRFI/YRFI trends (Location/Streak) influence the game context.
        - Bullet 3 (The Action): Clearly declare the most mathematically sound betting action (Moneyline, Total, or NRFI/YRFI) based strictly on the highest calculated Edge percentage or confidence score.

        DATA:
        {context}
        """
        
        import asyncio
        max_retries = 4
        base_delay = 12.0  # 429 alındığında en az 12 saniye bekle (limit 5 RPM olduğu için)

        for attempt in range(max_retries):
            try:
                # Doğrudan native asenkron çağrı yapıyoruz (aio.models)
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg and attempt < max_retries - 1:
                    print(f"⚠️ Gemini 429 Kota Sınırı. {base_delay} sn bekleniyor... (Deneme {attempt + 1}/{max_retries})")
                    await asyncio.sleep(base_delay)
                    base_delay *= 1.5  # Exponential backoff
                    continue
                else:
                    print(f"❌ Gemini AI Hatası: {e}")
                    return "AI analysis is temporarily unavailable due to network/API restrictions."
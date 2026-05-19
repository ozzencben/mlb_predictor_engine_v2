import os
from groq import AsyncGroq
from app.services.ai.base import BaseAIPredictor
from app.core.config import settings

class GroqPredictor(BaseAIPredictor):
    """Groq API kullanarak MLB bahis analizleri üreten asenkron servis katmanı."""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model_name = settings.GROQ_MODEL_NAME
        
        if self.api_key:
            # Asenkron operasyonlar için AsyncGroq istemcisini başlatıyoruz
            self.client = AsyncGroq(api_key=self.api_key)
        else:
            self.client = None

    async def generate_insight_async(self, prediction_data: dict) -> str:
        if not self.client:
            return "AI analysis currently unavailable (Groq API Key missing)."

        # Veri Ayrıştırma (todays_predictions.json yapısı ile tam uyumlu)
        matchup = prediction_data.get("matchup", {})
        full = prediction_data.get("Full_Game", {})
        odds = prediction_data.get("Odds", {})
        nrfi = prediction_data.get("NRFI", {})
        weather = prediction_data.get("Weather", {})
        
        trends = nrfi.get("scraped_trends", {})
        is_fallback = trends.get("is_fallback", True)
        
        a_pitcher = trends.get("away_pitcher", {}) if not is_fallback else {"location_nrfi_pct": "N/A", "streak_score": "N/A", "season_record": "N/A", "location_record": "N/A", "last10_record": "N/A", "streak_emoji": ""}
        h_pitcher = trends.get("home_pitcher", {}) if not is_fallback else {"location_nrfi_pct": "N/A", "streak_score": "N/A", "season_record": "N/A", "location_record": "N/A", "last10_record": "N/A", "streak_emoji": ""}
        a_team_nrfi = trends.get("away_team_nrfi", {}) if not is_fallback else {"season_nrfi_pct": "N/A", "season_record": "N/A"}
        h_team_nrfi = trends.get("home_team_nrfi", {}) if not is_fallback else {"season_nrfi_pct": "N/A", "season_record": "N/A"}

        # Ham veri paketinin string formata dönüştürülmesi
        context = (
            f"Matchup: {matchup.get('away_team')} vs {matchup.get('home_team')}\n"
            f"Full Game Proj: {full.get('full_away_score')}-{full.get('full_home_score')} (Total: {full.get('full_total')}).\n"
            f"Vegas Lines: O/U {odds.get('over_under', 'N/A')}. ML Edge -> Away: {odds.get('away_edge_pct', '0')}%, Home: {odds.get('home_edge_pct', '0')}%. F5 Edge -> Away: {odds.get('f5_away_edge_pct', '0')}%, Home: {odds.get('f5_home_edge_pct', '0')}%. NRFI Edge -> NRFI: {odds.get('nrfi_edge_pct', '0')}%, YRFI: {odds.get('yrfi_edge_pct', '0')}%.\n"
            f"NRFI Confidence: {nrfi.get('confidence')} (Pick: {nrfi.get('pick')}).\n"
            f"Away SP: Loc NRFI {a_pitcher.get('location_nrfi_pct')}% ({a_pitcher.get('location_record')}), Season Record: {a_pitcher.get('season_record')}, L10: {a_pitcher.get('last10_record')}, Streak: {a_pitcher.get('streak_score')} {a_pitcher.get('streak_emoji')}.\n"
            f"Home SP: Loc NRFI {h_pitcher.get('location_nrfi_pct')}% ({h_pitcher.get('location_record')}), Season Record: {h_pitcher.get('season_record')}, L10: {h_pitcher.get('last10_record')}, Streak: {h_pitcher.get('streak_score')} {h_pitcher.get('streak_emoji')}.\n"
            f"Away Team Offense NRFI: {a_team_nrfi.get('season_nrfi_pct')}% ({a_team_nrfi.get('season_record')}).\n"
            f"Home Team Offense NRFI: {h_team_nrfi.get('season_nrfi_pct')}% ({h_team_nrfi.get('season_record')}).\n"
            f"Weather: {weather.get('temp_f', 'N/A')}F, Wind {weather.get('wind_mph', 'N/A')}mph {weather.get('wind_direction', 'N/A')}. Alert: {weather.get('cbs_alert_word', 'None')} (Red Flag: {weather.get('red_flag_alert', False)})."
        )

        # Groq/Llama modelleri için optimize edilmiş System Instruction
        system_instruction = (
            "You are a highly analytical, professional MLB Sabermetrics expert providing betting insights for a high-end sports betting terminal.\n"
            "Your task is to analyze the provided data and return EXACTLY 3 BULLET POINTS. Do not use conversational filler.\n\n"
            "Follow this strict structure using markdown bullet points (-):\n"
            "- Bullet 1 (Anomaly/Pitching): Identify the most significant statistical edge or anomaly, focusing on run projections or recent trends.\n"
            "- Bullet 2 (Trends/Environment): State how the specific Ballpark Weather (Wind/Temp) or the pitchers' NRFI/YRFI trends (Location/Streak) influence the game context.\n"
            "- Bullet 3 (The Action): Clearly declare the most mathematically sound betting action (Moneyline, Total, or NRFI/YRFI) based strictly on the highest calculated Edge percentage or confidence score.\n\n"
            "CRITICAL: Avoid using the word 'Bookie', use 'Book' instead."
        )

        import asyncio
        max_retries = 4
        base_delay = 12.0  # Groq 429 limitleri için bekleme

        for attempt in range(max_retries):
            try:
                # Groq chat completion API çağrısı
                completion = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"DATA:\n{context}"}
                    ],
                    temperature=0.2,  # Sabermetrik tutarlılık için düşük sıcaklık katsayısı
                    max_tokens=180
                )
                return completion.choices[0].message.content.strip()

            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg and attempt < max_retries - 1:
                    print(f"⚠️ Groq 429 Kota Sınırı (TPM/RPM). {base_delay} sn bekleniyor... (Deneme {attempt + 1}/{max_retries})")
                    await asyncio.sleep(base_delay)
                    base_delay *= 1.5
                    continue
                else:
                    print(f"❌ Groq AI Hatası: {e}")
                    return "AI analysis is temporarily unavailable due to upstream API limits."
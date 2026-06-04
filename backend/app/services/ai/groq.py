import os
from groq import AsyncGroq
from app.services.ai.base import BaseAIPredictor
from app.core.config import settings

class GroqPredictor(BaseAIPredictor):
    """Groq API kullanarak MLB bahis analizleri üreten asenkron servis katmanı."""
    
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.model_name = settings.GROQ_MODEL_NAME
        self.quota_exhausted = False
        
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
        weather = prediction_data.get("Weather", {})
        
        # Atıcı ve takım detaylarını çıkar (Details altından)
        pitcher_analysis = prediction_data.get("Details", {}).get("pitcher_analysis", {})
        a_pitcher_data = pitcher_analysis.get("away") or {}
        h_pitcher_data = pitcher_analysis.get("home") or {}
        
        team_analysis = prediction_data.get("Details", {}).get("team_analysis") or {}
        a_team_data = team_analysis.get("away") or {}
        h_team_data = team_analysis.get("home") or {}

        # Ham veri paketinin string formata dönüştürülmesi
        context = (
            f"Matchup: {matchup.get('away_team')} ({matchup.get('away_pitcher')}) at {matchup.get('home_team')} ({matchup.get('home_pitcher')})\n"
            f"Full Game Score Projection: {full.get('full_away_score')}-{full.get('full_home_score')} (Total: {full.get('full_total')})\n"
            f"Vegas Lines: O/U {odds.get('over_under', 'N/A')}. ML Edge -> Away: {odds.get('away_edge_pct', '0')}%, Home: {odds.get('home_edge_pct', '0')}%. F5 Edge -> Away: {odds.get('f5_away_edge_pct', '0')}%, Home: {odds.get('f5_home_edge_pct', '0')}%.\n"
            f"Away Starter ({matchup.get('away_pitcher')}): ERA: {a_pitcher_data.get('era', 'N/A')}, FIP: {a_pitcher_data.get('fip', 'N/A')}, K-BB%: {round(a_pitcher_data.get('k_bb_pct', 0) * 100, 1) if isinstance(a_pitcher_data.get('k_bb_pct'), (int, float)) else 'N/A'}%, Record: {a_pitcher_data.get('record', 'N/A')}\n"
            f"Home Starter ({matchup.get('home_pitcher')}): ERA: {h_pitcher_data.get('era', 'N/A')}, FIP: {h_pitcher_data.get('fip', 'N/A')}, K-BB%: {round(h_pitcher_data.get('k_bb_pct', 0) * 100, 1) if isinstance(h_pitcher_data.get('k_bb_pct'), (int, float)) else 'N/A'}%, Record: {h_pitcher_data.get('record', 'N/A')}\n"
            f"Away Offense: wRC+: {a_team_data.get('wrc_plus', 100.0)}, RPG: {a_team_data.get('off_current', 4.5)} (Last 3 Games RPG: {a_team_data.get('off_last3', 4.5)}), Bullpen ERA proxy: {a_team_data.get('def_current', 4.5)}\n"
            f"Home Offense: wRC+: {h_team_data.get('wrc_plus', 100.0)}, RPG: {h_team_data.get('off_current', 4.5)} (Last 3 Games RPG: {h_team_data.get('off_last3', 4.5)}), Bullpen ERA proxy: {h_team_data.get('def_current', 4.5)}\n"
            f"Weather: {weather.get('temp_f', 'N/A')}F, Wind {weather.get('wind_mph', 'N/A')}mph {weather.get('wind_direction', 'N/A')}. Alert: {weather.get('cbs_alert_word', 'None')}."
        )

        # Groq/Llama modelleri için optimize edilmiş System Instruction
        system_instruction = (
            "You are a highly analytical, professional MLB Sabermetrics expert providing betting insights for a high-end sports betting terminal.\n"
            "Your task is to analyze the provided data and return EXACTLY 3 BULLET POINTS. Do not use conversational filler.\n\n"
            "Follow this strict structure using markdown bullet points (-):\n"
            "- Bullet 1 (Starting Pitchers): Analyze and compare the starting pitchers (ERA, FIP, K-BB%, record), highlighting who has the advantage and why.\n"
            "- Bullet 2 (Offense & Bullpen): Compare the team offenses (wRC+, RPG momentum) and bullpen strength (Bullpen ERA proxy), factoring in weather impact if significant.\n"
            "- Bullet 3 (The Action): Clearly declare the most mathematically sound betting action (Moneyline or Over/Under Total) based strictly on the highest calculated Edge percentage or model score difference.\n\n"
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
                error_msg = str(e).lower()
                is_429 = "429" in error_msg or "rate_limit" in error_msg or "rate limit" in error_msg
                is_daily_limit = "tpd" in error_msg or "tokens per day" in error_msg or "daily limit" in error_msg or "quota" in error_msg
                
                if is_429:
                    if is_daily_limit:
                        print(f"🛑 Groq Günlük/Kalıcı Limit Aşıldı (TPD). Circuit breaker devreye giriyor...")
                        self.quota_exhausted = True
                        return "AI analysis is temporarily unavailable due to daily API limits."
                    
                    if attempt < max_retries - 1:
                        print(f"⚠️ Groq 429 Kota Sınırı (TPM/RPM). {base_delay} sn bekleniyor... (Deneme {attempt + 1}/{max_retries})")
                        await asyncio.sleep(base_delay)
                        base_delay *= 1.5
                        continue
                    else:
                        print(f"🛑 Groq 429 limit denemeleri tükendi. Circuit breaker devreye giriyor...")
                        self.quota_exhausted = True
                        return "AI analysis is temporarily unavailable due to upstream API limits."
                else:
                    print(f"❌ Groq AI Hatası: {e}")
                    return f"AI analysis is temporarily unavailable: {e}"
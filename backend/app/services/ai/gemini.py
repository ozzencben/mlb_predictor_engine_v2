import os
from google import genai
from app.services.ai.base import BaseAIPredictor
from app.core.config import settings

class GeminiPredictor(BaseAIPredictor):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.quota_exhausted = False
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = 'gemini-2.5-flash'
        else:
            self.client = None

    async def generate_insight_async(self, prediction_data: dict) -> str:
        if not self.client:
            return "AI analysis currently unavailable (API Key missing)."

        # Sistemin JSON yapısına (todays_predictions.json) sadık kalarak veri çekimi
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

        # LLM için Rafine Bağlam (Context) Paketi
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

        # Tyler'ın İstediği Katı "Covers" Stili System Instruction
        prompt = f"""
        You are a highly analytical, professional MLB Sabermetrics expert providing betting insights for a high-end sports betting terminal.
        Your task is to analyze the provided data and return EXACTLY 3 BULLET POINTS. Do not use conversational filler (e.g., "Here is the analysis," "Hi there").

        Follow this strict structure using markdown bullet points (-):
        - Bullet 1 (Starting Pitchers): Analyze and compare the starting pitchers (ERA, FIP, K-BB%, record), highlighting who has the advantage and why.
        - Bullet 2 (Offense & Bullpen): Compare the team offenses (wRC+, RPG momentum) and bullpen strength (Bullpen ERA proxy), factoring in weather impact if significant.
        - Bullet 3 (The Action): Clearly declare the most mathematically sound betting action (Moneyline or Over/Under Total) based strictly on the highest calculated Edge percentage or model score difference.

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
                error_msg = str(e).lower()
                is_429 = "429" in error_msg or "rate_limit" in error_msg or "rate limit" in error_msg or "quota" in error_msg
                is_daily_limit = "daily" in error_msg or "tpd" in error_msg or "quota" in error_msg or "user limit" in error_msg
                
                if is_429:
                    if is_daily_limit:
                        print(f"🛑 Gemini Günlük/Kalıcı Limit Aşıldı. Circuit breaker devreye giriyor...")
                        self.quota_exhausted = True
                        return "AI analysis is temporarily unavailable due to daily API limits."
                        
                    if attempt < max_retries - 1:
                        print(f"⚠️ Gemini 429 Kota Sınırı. {base_delay} sn bekleniyor... (Deneme {attempt + 1}/{max_retries})")
                        await asyncio.sleep(base_delay)
                        base_delay *= 1.5  # Exponential backoff
                        continue
                    else:
                        print(f"🛑 Gemini 429 limit denemeleri tükendi. Circuit breaker devreye giriyor...")
                        self.quota_exhausted = True
                        return "AI analysis is temporarily unavailable due to upstream API limits."
                else:
                    print(f"❌ Gemini AI Hatası: {e}")
                    return f"AI analysis is temporarily unavailable: {e}"

    async def generate_tennis_insight_async(self, prediction_data: dict) -> str:
        if not self.client:
            return "AI analysis currently unavailable (API Key missing)."

        h_player = prediction_data.get("home_player", "Player 1")
        a_player = prediction_data.get("away_player", "Player 2")
        t_name = prediction_data.get("tournament", "Unknown Tournament")
        surface = prediction_data.get("surface", "Hard")
        h_prob = prediction_data.get("home_win_probability", 50.0)
        a_prob = prediction_data.get("away_win_probability", 50.0)
        p1_odds = prediction_data.get("p1_odds") or "N/A"
        p2_odds = prediction_data.get("p2_odds") or "N/A"
        edge = prediction_data.get("edge_percentage") or 0.0
        
        p1_stats = prediction_data.get("p1_stats") or {}
        p2_stats = prediction_data.get("p2_stats") or {}
        
        context = (
            f"Matchup: {h_player} vs {a_player} at {t_name} ({surface} court)\n"
            f"Model Projections: {h_player} Win Prob: {h_prob}%, {a_player} Win Prob: {a_prob}%\n"
            f"Market Lines: P1 Odds: {p1_odds}, P2 Odds: {p2_odds}. Calculated Edge: {edge}%\n"
            f"Player 1 ({h_player}) Stats: Rank: {p1_stats.get('rank', 'N/A')}, ELO: {p1_stats.get('elo', '1500')}, Court DNA: {p1_stats.get('surface_rate', '0.5')}, Form Momentum: {p1_stats.get('momentum', '0.5')}, Fatigue (Sets Played): {p1_stats.get('fatigue', '0')}, Set Dominance: {p1_stats.get('set_dominance', '0.5')}, Game Dominance: {p1_stats.get('game_dominance', '0.5')}, Recovery (Rest Days): {p1_stats.get('rest_days', '7')}, Clutch Win Rate: {p1_stats.get('clutch_win_rate', '50')}%, Straight Sets Rate: {p1_stats.get('straight_sets_rate', '50')}%\n"
            f"Player 2 ({a_player}) Stats: Rank: {p2_stats.get('rank', 'N/A')}, ELO: {p2_stats.get('elo', '1500')}, Court DNA: {p2_stats.get('surface_rate', '0.5')}, Form Momentum: {p2_stats.get('momentum', '0.5')}, Fatigue (Sets Played): {p2_stats.get('fatigue', '0')}, Set Dominance: {p2_stats.get('set_dominance', '0.5')}, Game Dominance: {p2_stats.get('game_dominance', '0.5')}, Recovery (Rest Days): {p2_stats.get('rest_days', '7')}, Clutch Win Rate: {p2_stats.get('clutch_win_rate', '50')}%, Straight Sets Rate: {p2_stats.get('straight_sets_rate', '50')}%"
        )

        prompt = f"""
        You are a highly analytical, professional Tennis Sabermetrics & Betting expert providing automated, punchy pre-match insights for a premium sports betting terminal.
        Your task is to analyze the provided player matchup details and return EXACTLY 3 BULLET POINTS (no introductory text, no conversational filler).

        Follow this strict structure using markdown bullet points (-):
        - Bullet 1 (The Surface & ELO Edge): Compare their Court DNA (surface success rate) and Surface ELO Gap, highlighting who dominates the target ground.
        - Bullet 2 (Physical & Fatigue Factor): Contrast their Fatigue Index (sets played recently) and Recovery Window (rest days). Pinpoint if a player is entering depleted.
        - Bullet 3 (The Betting Angle): Explicitly recommend the best mathematical play (Moneyline, Set Handicap, or Game Total) backed by the Edge or alternative market rules.

        DATA:
        {context}
        """
        
        import asyncio
        max_retries = 4
        base_delay = 12.0

        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                error_msg = str(e).lower()
                is_429 = "429" in error_msg or "rate_limit" in error_msg or "rate limit" in error_msg or "quota" in error_msg
                is_daily_limit = "daily" in error_msg or "tpd" in error_msg or "quota" in error_msg or "user limit" in error_msg
                
                if is_429:
                    if is_daily_limit:
                        print(f"🛑 Gemini Günlük/Kalıcı Limit Aşıldı. Circuit breaker devreye giriyor...")
                        self.quota_exhausted = True
                        return "AI analysis is temporarily unavailable due to daily API limits."
                        
                    if attempt < max_retries - 1:
                        print(f"⚠️ Gemini 429 Kota Sınırı. {base_delay} sn bekleniyor... (Deneme {attempt + 1}/{max_retries})")
                        await asyncio.sleep(base_delay)
                        base_delay *= 1.5
                        continue
                    else:
                        print(f"🛑 Gemini 429 limit denemeleri tükendi. Circuit breaker devreye giriyor...")
                        self.quota_exhausted = True
                        return "AI analysis is temporarily unavailable due to upstream API limits."
                else:
                    print(f"❌ Gemini AI Hatası: {e}")
                    return f"AI analysis is temporarily unavailable: {e}"

    async def generate_wnba_insight_async(self, prediction_data: dict) -> str:
        if not self.client:
            return "AI analysis currently unavailable (API Key missing)."

        home = prediction_data.get("home_team_name", "Home")
        away = prediction_data.get("away_team_name", "Away")
        h_prob = round(float(prediction_data.get("home_win_prob", 0.5)) * 100, 1)
        a_prob = round(float(prediction_data.get("away_win_prob", 0.5)) * 100, 1)
        spread = prediction_data.get("predicted_spread", 0)
        total = prediction_data.get("predicted_total", 0)
        elo_h = prediction_data.get("elo_home", 1500)
        elo_a = prediction_data.get("elo_away", 1500)
        rest_h = prediction_data.get("rest_home", "N/A")
        rest_a = prediction_data.get("rest_away", "N/A")
        odds = prediction_data.get("odds") or {}
        ml_h = odds.get("moneyline_home", "N/A")
        ml_a = odds.get("moneyline_away", "N/A")
        sp_line = odds.get("spread_home", "N/A")
        tot_line = odds.get("total_over", "N/A")
        top_bets = prediction_data.get("alt_bets") or []
        bet_summary = "; ".join(
            f"{b.get('market')} {b.get('pick')} (edge {b.get('edge')}%)" for b in top_bets[:3]
        ) or "No strong edge plays"

        h_l5 = prediction_data.get("home_l5") or {}
        a_l5 = prediction_data.get("away_l5") or {}
        feats = prediction_data.get("features") or {}
        star_impact = feats.get("feature_star_out_impact_diff", 0)

        context = (
            f"Matchup: {away} @ {home}\n"
            f"Model: {home} {h_prob}% | {away} {a_prob}% | Spread {spread:+.1f} | Total {total:.1f}\n"
            f"ELO: {home} {elo_h} vs {away} {elo_a} | Rest days: {home} {rest_h}, {away} {rest_a}\n"
            f"L5 Net Rating: {home} {h_l5.get('net_rtg', 'N/A')} vs {away} {a_l5.get('net_rtg', 'N/A')}\n"
            f"Star absence impact diff (home-away PPG): {star_impact}\n"
            f"Market: ML {home}/{away} = {ml_h}/{ml_a} | Spread {sp_line} | Total {tot_line}\n"
            f"Top model edges: {bet_summary}"
        )

        prompt = f"""
        You are a professional WNBA analytics & betting expert for a premium sports terminal.
        Return EXACTLY 3 markdown bullet points (-), no intro text.

        - Bullet 1 (Team Strength): Compare ELO, L5 net rating, and home court context. Who has the edge and why?
        - Bullet 2 (Situational Factors): Rest days, star player absence impact, recent form. Any fatigue or injury angle?
        - Bullet 3 (The Betting Angle): Recommend the best play (Moneyline, Spread, or Total) using model vs market edges.

        DATA:
        {context}
        """

        import asyncio
        max_retries = 4
        base_delay = 12.0

        for attempt in range(max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e:
                error_msg = str(e).lower()
                is_429 = "429" in error_msg or "rate_limit" in error_msg or "quota" in error_msg
                is_daily_limit = "daily" in error_msg or "tpd" in error_msg or "user limit" in error_msg

                if is_429:
                    if is_daily_limit:
                        self.quota_exhausted = True
                        return "AI analysis is temporarily unavailable due to daily API limits."
                    if attempt < max_retries - 1:
                        await asyncio.sleep(base_delay)
                        base_delay *= 1.5
                        continue
                    self.quota_exhausted = True
                    return "AI analysis is temporarily unavailable due to upstream API limits."
                return f"AI analysis is temporarily unavailable: {e}"
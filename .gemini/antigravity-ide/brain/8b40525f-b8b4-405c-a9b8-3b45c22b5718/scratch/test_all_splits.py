import asyncio
import httpx
import json
import os
from datetime import datetime

async def fetch_team_splits_async():
    url_teams = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    async with httpx.AsyncClient() as client:
        res = await client.get(url_teams)
        teams = res.json().get("teams", [])
        
        tasks = []
        team_info = []
        for t in teams:
            team_id = t["id"]
            team_name = t["name"]
            url_splits = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=statSplits&group=hitting&sitCodes=vl,vr&season=2026"
            tasks.append(client.get(url_splits, timeout=10.0))
            team_info.append((team_id, team_name))
            
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        splits_db = {}
        for (team_id, team_name), resp in zip(team_info, responses):
            if isinstance(resp, Exception) or resp.status_code != 200:
                print(f"Failed to fetch splits for {team_name}")
                continue
                
            data = resp.json()
            splits = data.get("stats", [{}])[0].get("splits", [])
            
            vs_LHP = {"avg": 0.250, "obp": 0.320, "slg": 0.400, "ops": 0.720, "k_pct": 22.0}
            vs_RHP = {"avg": 0.250, "obp": 0.320, "slg": 0.400, "ops": 0.720, "k_pct": 22.0}
            
            for s in splits:
                code = s.get("split", {}).get("code")
                stat = s.get("stat", {})
                
                # Safe parsing helper
                def safe_float(k, default):
                    v = stat.get(k)
                    if v is None:
                        return default
                    try:
                        return float(str(v).replace("%", ""))
                    except ValueError:
                        return default
                        
                pa = safe_float("plateAppearances", 1.0)
                so = safe_float("strikeOuts", 0.0)
                k_pct = round((so / pa) * 100.0, 1) if pa > 0 else 22.0
                
                parsed_split = {
                    "avg": safe_float("avg", 0.250),
                    "obp": safe_float("obp", 0.320),
                    "slg": safe_float("slg", 0.400),
                    "ops": safe_float("ops", 0.720),
                    "k_pct": k_pct
                }
                
                if code == "vl":
                    vs_LHP = parsed_split
                elif code == "vr":
                    vs_RHP = parsed_split
                    
            splits_db[team_name] = {
                "vs_LHP": vs_LHP,
                "vs_RHP": vs_RHP
            }
            
        print(f"Fetched splits for {len(splits_db)} teams successfully.")
        return splits_db

if __name__ == "__main__":
    db = asyncio.run(fetch_team_splits_async())
    # print some samples
    for name in ["New York Yankees", "Los Angeles Dodgers", "Chicago Cubs"][:3]:
        print(f"\n{name}:")
        print(" vs LHP:", db.get(name, {}).get("vs_LHP"))
        print(" vs RHP:", db.get(name, {}).get("vs_RHP"))

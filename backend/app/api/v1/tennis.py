import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException, Query

tennis_router = APIRouter(prefix="/tennis", tags=["Tennis"])

# Global Yollar
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sports", "tennis", "data"))
PREDICTIONS_FILE = os.path.join(DATA_DIR, "today_predictions.json")
RESULTS_FILE = os.path.join(DATA_DIR, "today_accuracy_results.json")
PLAYER_MATCHES_DIR = os.path.join(DATA_DIR, "raw", "player_matches")

def _get_file_modified_time(filepath: str) -> str:
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
    return "Bulunamadı"

@tennis_router.get("/predictions")
async def get_predictions(date: str | None = None):
    """
    Bugünün veya arşivdeki belirli bir tarihin tenis tahminlerini döndürür.
    """
    now_et = datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    
    target_file = PREDICTIONS_FILE
    if date and date != today_str:
        target_file = os.path.join(DATA_DIR, "archive", f"predictions_{date}.json")
        
    if not os.path.exists(target_file):
        raise HTTPException(
            status_code=404,
            detail=f"Belirtilen tarih ({date or today_str}) için tenis tahmin verisi bulunamadı."
        )
    
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        last_modified = _get_file_modified_time(target_file)
        return {
            "status": "success",
            "last_updated": last_modified,
            "data": data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tahmin dosyası okunurken hata oluştu: {str(e)}"
        )

@tennis_router.get("/results")
async def get_results(date: str | None = None):
    """
    Bugünün veya arşivdeki belirli bir tarihin tenis doğruluk test sonuçlarını döndürür.
    """
    now_et = datetime.now(ZoneInfo("America/New_York"))
    today_str = now_et.strftime("%Y-%m-%d")
    
    target_file = RESULTS_FILE
    if date and date != today_str:
        target_file = os.path.join(DATA_DIR, "archive", f"results_{date}.json")
        
    if not os.path.exists(target_file):
        raise HTTPException(
            status_code=404,
            detail=f"Belirtilen tarih ({date or today_str}) için tenis doğruluk sonuçları bulunamadı."
        )
        
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        last_modified = _get_file_modified_time(target_file)
        return {
            "status": "success",
            "last_updated": last_modified,
            "data": data
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Sonuç dosyası okunurken hata oluştu: {str(e)}"
        )

@tennis_router.get("/player-history/{player_id}")
async def get_player_history(
    player_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Döndürülecek maksimum maç sayısı")
):
    """
    Belirli bir oyuncunun son N maçını döndürür.
    Player ID, prediction JSON'daki p1_id / p2_id alanından alınır.
    """
    player_file = os.path.join(PLAYER_MATCHES_DIR, f"{player_id}.json")
    
    if not os.path.exists(player_file):
        raise HTTPException(
            status_code=404,
            detail=f"Oyuncu geçmişi bulunamadı: {player_id}"
        )
    
    try:
        with open(player_file, "r", encoding="utf-8") as f:
            matches = json.load(f)
        
        limited_matches = matches[:limit]
        
        return {
            "status": "success",
            "player_id": player_id,
            "total_matches": len(matches),
            "returned_matches": len(limited_matches),
            "matches": limited_matches
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Oyuncu geçmişi okunurken hata oluştu: {str(e)}"
        )


@tennis_router.get("/rankings")
async def get_rankings(limit: int = Query(default=5, ge=1, le=20)):
    """
    ATP ve WTA sıralama listesinden en yüksek rütbeli oyuncuları döndürür.
    """
    atp_file = os.path.join(DATA_DIR, "atp_ranks.json")
    wta_file = os.path.join(DATA_DIR, "wta_ranks.json")
    
    def _parse_ranks(filepath: str) -> list:
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            players = []
            for p_id, p_info in data.items():
                pn = p_info.get("PN", "")
                parts = pn.strip().split()
                if len(parts) >= 2:
                    formatted_name = f"{parts[-1]} {' '.join(parts[:-1])}"
                else:
                    formatted_name = pn
                
                players.append({
                    "id": p_id,
                    "name": formatted_name,
                    "rank": int(p_info.get("RA", 9999)),
                    "points": int(p_info.get("PO", 0)) if p_info.get("PO") else 0,
                    "country": p_info.get("CN", ""),
                    "player_id": p_info.get("PI", "")
                })
            
            # Sort by rank ascending
            players.sort(key=lambda x: x["rank"])
            return players[:limit]
        except Exception as e:
            print(f"Error parsing ranks file {filepath}: {e}")
            return []

    atp_top = _parse_ranks(atp_file)
    wta_top = _parse_ranks(wta_file)
    
    return {
        "status": "success",
        "atp": atp_top,
        "wta": wta_top
    }

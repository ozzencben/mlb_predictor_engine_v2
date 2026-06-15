import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import APIRouter, HTTPException

tennis_router = APIRouter(prefix="/tennis", tags=["Tennis"])

# Global Yollar
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "sports", "tennis", "data"))
PREDICTIONS_FILE = os.path.join(DATA_DIR, "today_predictions.json")
RESULTS_FILE = os.path.join(DATA_DIR, "today_accuracy_results.json")

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

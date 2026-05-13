import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Veri klasörünün yolunu bul (/app/core/../data)
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("------------------------------------------")
    print("🔥 MLB Predictor Engine API Başlatılıyor...")
    
    # Veri klasörü yoksa oluştur
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"📁 Veri klasörü oluşturuldu: {DATA_DIR}")
    else:
        print(f"✅ Veri klasörü hazır: {DATA_DIR}")
        
    yield  # Uygulama çalışıyor...
    
    print("🛑 API Kapatılıyor... Tüm kaynaklar serbest bırakıldı.")
    print("------------------------------------------")
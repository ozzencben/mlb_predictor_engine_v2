# =============================================================================
# MLB Predictor Engine - Backend Dockerfile
# Build tool: uv (fast Python package manager)
# Runtime: Python 3.12-slim
# =============================================================================

# --- Stage 1: Dependency Builder ---
# uv'yi kullanarak bağımlılıkları izole bir ortamda derliyoruz
FROM python:3.12-slim AS builder

# uv'yi resmi imajdan kopyala (pip'e göre çok daha hızlı)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Çalışma dizinini ayarla
WORKDIR /app

# Önce sadece bağımlılık dosyalarını kopyala (Docker layer cache optimizasyonu)
COPY pyproject.toml uv.lock ./

# Bağımlılıkları /app/.venv içine yükle, proje paketi hariç
RUN uv sync --frozen --no-install-project --no-dev

# --- Stage 2: Production Runtime ---
FROM python:3.12-slim AS runtime

# Güvenlik: Root olmayan kullanıcı oluştur
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

WORKDIR /app

# Builder aşamasından sanal ortamı kopyala
COPY --from=builder /app/.venv /app/.venv

# Uygulama kodunu kopyala
COPY app/ ./app/

# Virtual environment PATH'e ekle
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Veri klasörünün sahibini değiştir
RUN chown -R appuser:appgroup /app

# Root olmayan kullanıcıya geç
USER appuser

# Port tanımla (bilgilendirme amaçlı)
EXPOSE 8000

# Health check: API'nin sağlıklı olup olmadığını kontrol et
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Uygulama başlatma komutu
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

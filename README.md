# ⚾ MLB Predictor Engine v2

> A data-driven MLB prediction and betting edge detection system. The backend scrapes live team/pitcher statistics and computes NRFI, F5, and full-game projections. The frontend displays today's matchups with win probabilities, projected totals, and value alerts.

---

## Project Structure

```
mlb_predictor_engine_v2/
├── backend/          # FastAPI — deployed on Render
│   ├── app/
│   │   ├── api/v1/   # REST endpoints (/predictions, /system-status, /refresh-data)
│   │   ├── core/     # Lifespan, config
│   │   ├── data/     # JSON data files (runtime-generated, not in Git)
│   │   ├── models/   # NRFI, F5, Full-Game math models
│   │   └── services/ # Scrapers, engine, odds provider
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example  ← copy to .env for local dev
│
├── frontend/         # Vite + React — deployed on Vercel
│   ├── src/
│   │   ├── api/      # Axios client (reads VITE_API_URL)
│   │   ├── components/
│   │   ├── hooks/
│   │   └── utils/
│   └── .env.example  ← copy to .env for local dev
│
├── docker-compose.yml  # Local full-stack dev
└── .env.example        # Root-level shared env template
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Package Manager | [uv](https://docs.astral.sh/uv/) |
| Frontend | React 19, Vite, Tailwind CSS v4, Axios |
| Container | Docker (multi-stage build) |
| Backend Hosting | [Render](https://render.com) |
| Frontend Hosting | [Vercel](https://vercel.com) |

---

## Local Development

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) — recommended
- Or: Python 3.12 + [uv](https://docs.astral.sh/uv/getting-started/installation/) + Node.js 20+

### Option A — Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/ozzencben/mlb_predictor_engine_v2.git
cd mlb_predictor_engine_v2

# 2. Create root .env
cp .env.example .env

# 3. Start the backend
docker compose up --build
```

API will be available at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### Option B — Manual

**Backend**
```bash
cd backend
cp .env.example .env          # fill in your values
uv sync                       # install dependencies
uvicorn app.main:app --reload --port 8000
```

**Frontend**
```bash
cd frontend
cp .env.example .env          # set VITE_API_URL=http://localhost:8000/api/v1
npm install
npm run dev                   # http://localhost:5173
```

---

## API Endpoints

Base URL: `http://localhost:8000`

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/api/v1/predictions` | Today's predictions (1-hour cache) |
| `GET` | `/api/v1/system-status` | Last update timestamps |
| `POST` | `/api/v1/refresh-data` | Force re-run the prediction engine |

---

## Deployment

### Backend → Render

1. Go to [render.com](https://render.com) → **New Web Service** → connect your GitHub repo.
2. Set the following in the Render dashboard:

| Setting | Value |
|---|---|
| **Root Directory** | `backend` |
| **Runtime** | `Docker` |
| **Dockerfile Path** | `./Dockerfile` |
| **Port** | `8000` |

3. Add **Environment Variables** (from `backend/.env.example`):

| Key | Value |
|---|---|
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |
| `CACHE_EXPIRY_SECONDS` | `3600` |

> ⚠️ **Important:** Render's free tier spins down after inactivity. The first request after a cold start may take 30–60 seconds while the scraper fetches fresh data.

---

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → import your GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Add **Environment Variables**:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://your-render-service.onrender.com/api/v1` |

4. Deploy — Vercel auto-detects Vite.

---

## Environment Variables Reference

### Backend (`backend/.env.example`)

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `development` | Runtime environment |
| `PORT` | `8000` | Server port (Render sets this automatically) |
| `CORS_ORIGINS` | `*` | Allowed frontend origins (use specific domain in production) |
| `CACHE_EXPIRY_SECONDS` | `3600` | How long prediction files stay fresh |
| `SCRAPER_USER_AGENT` | Chrome UA | HTTP User-Agent for scraper requests |

### Frontend (`frontend/.env.example`)

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | ✅ Yes | Full base URL of the backend API including `/api/v1` |

---

## Data Flow

```
Scraper services          PredictionRunner             API Layer
─────────────────         ─────────────────            ─────────
DataCollector      ──►    MLBUnifiedEngine   ──►    /api/v1/predictions
PitcherScraper     ──►    (NRFI + F5 + Full)         (1-hr file cache)
MatchupScraper     ──►
OddsProvider       ──►    Edge calculation   ──►    Odds + value alerts
```

All intermediate data is written to `backend/app/data/*.json` (excluded from Git — runtime generated).

---

## Known Considerations

- **Data files not in Git:** `backend/app/data/*.json` files are excluded from version control and generated at runtime. On a fresh Render deploy, the first `/api/v1/predictions` call triggers the full scrape pipeline.
- **Render cold starts:** Free tier services sleep after 15 minutes of inactivity. First wake-up request will be slow.
- **CORS in production:** Change `CORS_ORIGINS` from `*` to your exact Vercel URL before going live.

---

## License

MIT

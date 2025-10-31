# DugTrio

DugTrio is a backend + Telegram bot ecosystem for discovering and surfacing social sentiment and PNL screenshots related to Solana ecosystem projects.

## Overview
- Backend: FastAPI server exposing endpoints for sentiment, PNL cards, trending projects, history, and administrative tasks.
- Ingest: A scheduled fetcher that queries X (Twitter) for project mentions and saves tweets (with media URLs) to the DB.
- Analysis:
  - NLP sentiment analysis using Hugging Face Transformers.
  - PNL image OCR and parsing using Tesseract OCR + pytesseract.
  - Trend scoring based on mention volume changes.
- UI: Telegram bot that presents sentiment, top projects, PNL cards, stats, and tracking controls.

## Tech Stack
- Languages: Python 3.10+
- Web framework: FastAPI (`main.py`)
- ASGI server: Uvicorn
- Database ORM: SQLAlchemy (`models.py`, `database.py`)
- DB: PostgreSQL (Neon) — configured via `DATABASE_URL` in `.env`
- Twitter/X ingestion: tweepy (`tracker.py`)
- Bot: python-telegram-bot (`bot.py`)
- OCR: Tesseract + pytesseract (`pnl_analyzer.py`)
- ML/NLP: transformers, torch (`analyzer.py`)
- HTTP client: httpx (bot calls backend)
- Build script: `build.sh` — installs system Tesseract and pip deps

## Tech & Tools — what we used and why
- Python — Primary language for backend, bot, ingestion, analysis, and utility scripts.
- FastAPI — Serves the REST API endpoints used by the bot and frontend.
- Uvicorn — ASGI server used to run the FastAPI app in development/production.
- SQLAlchemy — ORM for defining models and interacting with the PostgreSQL database.
- PostgreSQL (Neon) — Production database for storing tweets, sentiment results, PNL cards, and tracking requests.
- Tweepy — Fetches tweets and media from X (Twitter) for ingestion into the DB.
- transformers (Hugging Face) + torch — Runs the sentiment models to label tweets and produce confidence scores.
- pytesseract + Tesseract OCR — Extracts text (PNL values) from screenshot images attached to tweets.
- python-telegram-bot — Telegram UI layer: bot handlers, menus, and user commands.
- httpx — HTTP client used by the bot to call backend API endpoints.
- python-dotenv — Loads local `.env` secrets during development.
- Docker / build scripts — Optional environment reproducibility and system deps installer (Tesseract helper).
- Requirements.txt / pip — Python dependency management.

Use-case summary:
- Ingest (tweepy) → store (SQLAlchemy/Postgres) → analyze (transformers, OCR) → expose (FastAPI) → present (python-telegram-bot).

## Repository Layout
- `main.py` — FastAPI app and endpoints
- `bot.py` — Telegram bot and handlers
- `tracker.py` — pulls tweets and stores into DB
- `analyzer.py` — runs sentiment analysis and writes results
- `pnl_analyzer.py` — downloads media, OCRs, parses PNL cards, saves `PnlCard` rows
- `database.py` — engine, `SessionLocal`, `Base`, helpers
- `models.py` — SQLAlchemy ORM models (`User`, `Tweet`, `PnlCard`, `TrackRequest`, `TrendingProject`, `TrackedWallet`)
- `create_tables.py` — one-shot table init helper
- `reset_DataBase.py` — interactive reset script (destructive)
- `build.sh` — installs Tesseract and Python dependencies
- `requirements.txt` — Python dependencies
- `.env` — environment variables (API keys, DB url, etc.) — DO NOT COMMIT TO PUBLIC REPOS

## Getting started (developer)
1. Copy `.env` locally (never commit).
2. Install system deps (Linux example):
   ```sh
   sudo ./build.sh
   ```
3. Create tables:
   ```sh
   python create_tables.py
   ```
4. Run backend (development):
   ```sh
   uvicorn main:app --reload
   ```
5. Run bot (in another terminal):
   ```sh
   python bot.py
   ```
6. Run ingestion & analysis tasks (manual/testing):
   - Fetch fresh tweets:
     ```sh
     python tracker.py
     ```
   - Analyze sentiment:
     ```sh
     python analyzer.py
     ```
   - Analyze PNL images:
     ```sh
     python pnl_analyzer.py
     ```

## API Endpoints (example)
- GET /api/project/{project_name} — project sentiment summary (24h)
- POST /api/request — request to track a new project
- GET /api/history/{project_tag} — 7-day daily average sentiment
- POST /api/run-analysis — trigger background analysis tasks
- GET /api/pnl/{project_name} — list parsed PNL cards for a project
- GET /api/trending — top trending projects
- Root `/` — basic health / welcome

## Notes & Best Practices
- Secrets: Keep `.env` out of the repo. Use environment variables in production.
- Tesseract: Ensure `tesseract` binary is available on the host for OCR to work.
- Model weights: transformers models may download large files; prefer an environment with GPU or use smaller models for development.
- Rate limits: X (Twitter) API rate limits apply — consider backoff and caching.
- Database: Use connection pooling in production and secure credentials.

## Presenting the project
- Demo flow: show the API endpoints in a browser or curl, then run the bot locally and demo commands (/start, /stats, /track, /sentiment, /tweets) and the inline menus.
- Highlight: ingestion → analysis → presentation pipeline and the modular separation (tracker, analyzer, pnl_analyzer, API, bot).

## Contact
- Repo by DugTrio team
- For demos, run the bot locally and point it at `http://localhost:8000` or a public deploy.
```// filepath: c:\Users\shaur\OneDrive\Desktop\DugTrio\README.md
# DugTrio

DugTrio is a backend + Telegram bot ecosystem for discovering and surfacing social sentiment and PNL screenshots related to Solana ecosystem projects.

## Overview
- Backend: FastAPI server exposing endpoints for sentiment, PNL cards, trending projects, history, and administrative tasks.
- Ingest: A scheduled fetcher that queries X (Twitter) for project mentions and saves tweets (with media URLs) to the DB.
- Analysis:
  - NLP sentiment analysis using Hugging Face Transformers.
  - PNL image OCR and parsing using Tesseract OCR + pytesseract.
  - Trend scoring based on mention volume changes.
- UI: Telegram bot that presents sentiment, top projects, PNL cards, stats, and tracking controls.

## Tech Stack
- Languages: Python 3.10+
- Web framework: FastAPI (`main.py`)
- ASGI server: Uvicorn
- Database ORM: SQLAlchemy (`models.py`, `database.py`)
- DB: PostgreSQL (Neon) — configured via `DATABASE_URL` in `.env`
- Twitter/X ingestion: tweepy (`tracker.py`)
- Bot: python-telegram-bot (`bot.py`)
- OCR: Tesseract + pytesseract (`pnl_analyzer.py`)
- ML/NLP: transformers, torch (`analyzer.py`)
- HTTP client: httpx (bot calls backend)
- Build script: `build.sh` — installs system Tesseract and pip deps

## Tech & Tools — what we used and why
- Python — Primary language for backend, bot, ingestion, analysis, and utility scripts.
- FastAPI — Serves the REST API endpoints used by the bot and frontend.
- Uvicorn — ASGI server used to run the FastAPI app in development/production.
- SQLAlchemy — ORM for defining models and interacting with the PostgreSQL database.
- PostgreSQL (Neon) — Production database for storing tweets, sentiment results, PNL cards, and tracking requests.
- Tweepy — Fetches tweets and media from X (Twitter) for ingestion into the DB.
- transformers (Hugging Face) + torch — Runs the sentiment models to label tweets and produce confidence scores.
- pytesseract + Tesseract OCR — Extracts text (PNL values) from screenshot images attached to tweets.
- python-telegram-bot — Telegram UI layer: bot handlers, menus, and user commands.
- httpx — HTTP client used by the bot to call backend API endpoints.
- python-dotenv — Loads local `.env` secrets during development.
- Docker / build scripts — Optional environment reproducibility and system deps installer (Tesseract helper).
- Requirements.txt / pip — Python dependency management.

Use-case summary:
- Ingest (tweepy) → store (SQLAlchemy/Postgres) → analyze (transformers, OCR) → expose (FastAPI) → present (python-telegram-bot).

## Repository Layout
- `main.py` — FastAPI app and endpoints
- `bot.py` — Telegram bot and handlers
- `tracker.py` — pulls tweets and stores into DB
- `analyzer.py` — runs sentiment analysis and writes results
- `pnl_analyzer.py` — downloads media, OCRs, parses PNL cards, saves `PnlCard` rows
- `database.py` — engine, `SessionLocal`, `Base`, helpers
- `models.py` — SQLAlchemy ORM models (`User`, `Tweet`, `PnlCard`, `TrackRequest`, `TrendingProject`, `TrackedWallet`)
- `create_tables.py` — one-shot table init helper
- `reset_DataBase.py` — interactive reset script (destructive)
- `build.sh` — installs Tesseract and Python dependencies
- `requirements.txt` — Python dependencies
- `.env` — environment variables (API keys, DB url, etc.) — DO NOT COMMIT TO PUBLIC REPOS

## Getting started (developer)
1. Copy `.env` locally (never commit).
2. Install system deps (Linux example):
   ```sh
   sudo ./build.sh
   ```
3. Create tables:
   ```sh
   python create_tables.py
   ```
4. Run backend (development):
   ```sh
   uvicorn main:app --reload
   ```
5. Run bot (in another terminal):
   ```sh
   python bot.py
   ```
6. Run ingestion & analysis tasks (manual/testing):
   - Fetch fresh tweets:
     ```sh
     python tracker.py
     ```
   - Analyze sentiment:
     ```sh
     python analyzer.py
     ```
   - Analyze PNL images:
     ```sh
     python pnl_analyzer.py
     ```

## API Endpoints (example)
- GET /api/project/{project_name} — project sentiment summary (24h)
- POST /api/request — request to track a new project
- GET /api/history/{project_tag} — 7-day daily average sentiment
- POST /api/run-analysis — trigger background analysis tasks
- GET /api/pnl/{project_name} — list parsed PNL cards for a project
- GET /api/trending — top trending projects
- Root `/` — basic health / welcome

## Notes & Best Practices
- Secrets: Keep `.env` out of the repo. Use environment variables in production.
- Tesseract: Ensure `tesseract` binary is available on the host for OCR to work.
- Model weights: transformers models may download large files; prefer an environment with GPU or use smaller models for development.
- Rate limits: X (Twitter) API rate limits apply — consider backoff and caching.
- Database: Use connection pooling in production and secure credentials.

## Presenting the project
- Demo flow: show the API endpoints in a browser or curl, then run the bot locally and demo commands (/start, /stats, /track, /sentiment, /tweets) and the inline menus.
- Highlight: ingestion → analysis → presentation pipeline and the modular separation (tracker, analyzer, pnl_analyzer, API, bot).

## Contact
- Repo by DugTrio team
- For demos, run the bot locally and point it at `http://localhost:8000` or a public deploy.
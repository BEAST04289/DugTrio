# ⛏️ DugTrio: The AI Alpha Hunter for Solana

## 🚀 Verifiable Alpha Intelligence via Telegram

**DugTrio is a full-stack, AI-powered intelligence engine built to solve the fundamental problem of Fake Alpha in high-speed crypto markets.**

We eliminate guesswork by fusing advanced **AI Sentiment Analysis** with verifiable **On-Chain Metrics**, delivering actionable signals directly into the trader's Telegram workflow.

### 💡 The DugTrio Edge

| Feature | The Strategic Advantage |
| :--- | :--- |
| **Dual Intelligence Stream** | Fuses **Social Hype (X.com)** with **Liquidity/Volume (On-Chain)** to eliminate "Fool's Gold." |
| **Zero Latency Delivery** | **Telegram-Native** deployment provides instant access to critical signals. |
| **Monetization Ready** | Supports premium tools: **PNL OCR** and **Smart Wallet Tracking** (high-value utility). |
| **Proven Execution** | Built and deployed on **Zero-Budget, Free-Tier Resources**, demonstrating rapid development capability. |

---

## 📹 Live Demo Preview

Experience the power of the DugTrio pipeline: from raw tweet ingestion to AI analysis to a final, actionable signal in the Telegram bot.



**Try the Bot Live:** **[t.me/DugTrio\_ai\_bot](https://t.me/DugTrio_ai_bot)**

---

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
- **Deployment:** Render (API Web Service), Heroku/Railway (Bot Worker)

---

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
- `.env` — environment variables (API keys, DB url, etc.) — **DO NOT COMMIT TO PUBLIC REPOS**

## Getting Started (Developer)
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

---
## API Endpoints (example)
- GET /api/project/{project_name} — project sentiment summary (24h)
- POST /api/request — request to track a new project
- GET /api/history/{project_tag} — 7-day daily average sentiment
- POST /api/run-analysis — trigger background analysis tasks
- GET /api/pnl/{project_name} — list parsed PNL cards for a project
- GET /api/trending — top trending projects
- Root `/` — basic health / welcome

## Notes & Best Practices
- **Secrets:** Keep `.env` out of the repo. Use environment variables in production.
- **Tesseract:** Ensure `tesseract` binary is available on the host for OCR to work.
- **Rate limits:** X (Twitter) API rate limits apply — consider backoff and caching.

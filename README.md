# 🤖 DugTrio: The Verifiable AI Intelligence Layer

> *"Ephemeral sentiment, permanently verifiable."*

**DugTrio** is a Telegram-based AI agent that aggregates real-time crypto market social signals, analyzes them using Transformer models (RoBERTa), and anchors that intelligence onto the **Story Protocol** blockchain. It transforms fleeting market analysis into verifiable, ownable Intellectual Property (IP).

---

## 🚩 The Problem

1.  **Data Overload:** Crypto moves too fast for humans to read every tweet or news article.
2.  **Lack of Accountability:** "Influencers" delete bearish tweets when the market pumps. There is no record of who predicted what.
3.  **Ephemeral Insights:** Valuable analysis is lost in the feed within minutes.

---

## 🛠️ How It Works

### 1. The Eyes (Data Ingestion) 👁️
DugTrio continuously monitors high-velocity keywords (e.g., `$SOL`, `$JUP`) on X (Twitter). It filters out spam to capture the raw "voice of the market."

### 2. The Brain (AI Analysis) 🧠
We use **RoBERTa** (`cardiffnlp/twitter-roberta-base-sentiment`), a transformer model fine-tuned on financial tweets, to understand context:
*   **Input:** *"This dip is tasty."*
*   **Output:** `Bullish (0.85)` *(Unlike simple tools which might see 'dip' as negative).*

### 3. The Vault (Story Protocol Integration) 🔒
**The Killer Feature:** When a user requests to "Mint IP," DugTrio:
1.  Packages the analysis (Token, Score, Timestamp).
2.  Hashes the data into a unique fingerprint.
3.  Interacts with the **Story Protocol IP Asset Registry** (Sepolia Testnet).
4.  **Result:** A permanent, on-chain record proving *this* specific AI generated *this* insight at *this* time.

---

## 🏗️ Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Interface** | `python-telegram-bot` | User-facing command center. |
| **Backend** | `FastAPI` | Logic handling & blockchain orchestration. |
| **AI Engine** | `HuggingFace Transformers` | RoBERTa model for sentiment scoring. |
| **Blockchain** | `Web3.py` | Interaction with Story Protocol (Sepolia). |
| **Database** | `SQLite` / `PostgreSQL` | Caching tweets & user sessions. |
| **Cloud** | `Render` | CI/CD & 24/7 Hosting. |

---

## 🗺️ Roadmap (Winter Code & Beyond)

### ✅ Phase 1: The Foundation (Completed)
- [x] Telegram Bot Interface.
- [x] Twitter/X Scraper (`services/tracker.py`).
- [x] RoBERTa Sentiment Model Integration (`services/analyzer.py`).

### ✅ Phase 2: Proof of Intelligence (Completed)
- [x] Connection to Story Protocol (Sepolia Testnet).
- [x] Pipeline to mint Sentiment Reports as IP Assets.
- [x] **Dynamic Sentiment Analysis:** Type `/sentiment <coin>` to analyze any project instantly.
- [x] Deployment on Render.

### 🚀 Phase 3: The "World Class" Upgrade (Upcoming)
- [ ] **Multi-Agent Council:** Three AI agents (Technical, Fundamental, Social) debate the token.
- [ ] **Automated Trading:** Connect Phantom Wallet to auto-execute trades if Score > 0.85.
- [ ] **Fake PNL Detector:** OCR feature to detect photoshopped profit screenshots.
- [ ] **IP Marketplace:** Frontend for users to trade their high-accuracy sentiment reports.
- [ ] **More Commands:** Add `/chart <coin>` and `/whale <coin>` for deeper insights.

> **💡 Have a better idea?** We are open to discussing innovative features beyond this roadmap! If you have a cool concept for an AI agent or a new way to use Story Protocol, feel free to open an issue or a PR. We love creative contributions!

---

## ⚡ Quick Start

### Prerequisites
*   Python 3.10+
*   Telegram Bot Token
*   **X (Twitter) Developer Account** (Essential for the scraper)
*   Story Protocol Private Key (Sepolia)
*   PostgreSQL Database (Recommended)

### Installation

1.  **Clone the repo**
    ```bash
    git clone https://github.com/BEAST04289/DugTrio.git
    cd DugTrio
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment**
    Create a `.env` file:
    ```env
    TELEGRAM_BOT_TOKEN=your_token_here
    BEARER_TOKEN=your_twitter_api_bearer_token
    PRIVATE_KEY=your_wallet_private_key
    RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
    API_BASE_URL=http://127.0.0.1:8000
    DATABASE_URL=postgresql://user:password@localhost/dugtrio_db
    ```

### ⚠️ Important: X (Twitter) API Limits
The **Free Tier** of the X API only allows **100 tweets per month**.
*   **Default Setting:** We have set the scraper to pull only **10 tweets** per run to prevent you from burning your quota instantly.
*   **How to Change:** If you have a paid plan (Basic/Pro), go to `services/tracker.py` and change `max_results=10` to `50` or `100`.

### 🚀 Running the System (The 2-Terminal Setup)

Since DugTrio uses real-time data, you need to run the backend and the bot. The data engine now runs automatically when you use the bot!

**Terminal 1: The Backend API**
```bash
uvicorn api.main:app --reload
```
**Terminal 2: The Telegram Bot**
```bash
python -m bot.bot
```

*(Optional) Terminal 3: Manual Data Engine*
Only needed if you want to force a bulk update without using the bot.
```bash
python -m services.tracker
python -m services.analyzer
```

---

## 🔧 Troubleshooting & Common Issues

### ❌ "No Data Found" Error in Bot
**Cause:** The database is empty or the X API limit (100 tweets/month) has been reached.
**Fix:**
1.  **Check your API Quota:** Log in to the [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) and ensure you haven't used all 100 tweets.
2.  **Wait:** If you have quota, just click the button in the bot again. It now automatically tries to fetch data.
3.  **Check Logs:** Look at the "Terminal 1" output. If it says "429 Too Many Requests", you are out of quota.

### 🦊 IP Minting & MetaMask
To use the "Mint IP" feature, you need a wallet on the **Sepolia Testnet**.
1.  Install **MetaMask**.
2.  Enable "Show Test Networks" in settings.
3.  Copy your **Private Key** (Settings -> Security -> Show Private Key).
4.  Paste it into your `.env` file as `PRIVATE_KEY`.
5.  Get free Sepolia ETH from a faucet (e.g., Google "Sepolia Faucet") to pay for gas.

### 📉 How to check how much data I have?
We included a utility script to check your database stats:
```bash
python -m scripts.check_stats
```
### 🔗 Blockchain/Story Protocol Errors
**Cause:** Missing PRIVATE_KEY or RPC_URL in .env.
**Fix:** The bot will still work without blockchain features, but IP minting will fail. Ensure your .env is set up correctly if you want to test minting.
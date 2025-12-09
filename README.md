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
- [x] Twitter/X Scraper (`tracker.py`).
- [x] RoBERTa Sentiment Model Integration (`analyzer.py`).

### ✅ Phase 2: Proof of Intelligence (Completed)
- [x] Connection to Story Protocol (Sepolia Testnet).
- [x] Pipeline to mint Sentiment Reports as IP Assets.
- [x] Deployment on Render.

### 🚀 Phase 3: The "World Class" Upgrade (Upcoming)
- [ ] **Multi-Agent Council:** Three AI agents (Technical, Fundamental, Social) debate the token.
- [ ] **Automated Trading:** Connect Phantom Wallet to auto-execute trades if Score > 0.85.
- [ ] **Fake PNL Detector:** OCR feature to detect photoshopped profit screenshots.
- [ ] **IP Marketplace:** Frontend for users to trade their high-accuracy sentiment reports.

---

## ⚡ Quick Start

### Prerequisites
*   Python 3.10+
*   Telegram Bot Token
*   Story Protocol Private Key (Sepolia)

### Installation

1.  **Clone the repo**
    ```bash
    git clone https://github.com/shaurya-upadhyay/DugTrio.git
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
    PRIVATE_KEY=your_wallet_private_key
    RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
    API_BASE_URL=http://127.0.0.1:8000
    ```
# Terminal 1: Backend
uvicorn main:app --reload

# Terminal 2: Bot
python bot.py
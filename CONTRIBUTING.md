# Contributing to DugTrio

Thank you for your interest in contributing to DugTrio! We welcome contributions from the community to help make this project better.

## Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/BEAST04289/DugTrio.git
    cd DugTrio
    ```
3.  **Set up the environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
4.  **Configure Environment**:
    *   Copy `.env.example` (if available) or create a `.env` file.
    *   **Crucial:** You need a valid **X (Twitter) Developer Account** to run the scraper. Add your `BEARER_TOKEN` to the `.env` file.
    *   Set up a local PostgreSQL database or use a cloud provider (like Neon).

5.  **Create a branch** for your feature or fix:
    ```bash
    git checkout -b feature/amazing-feature
    ```

## Project Structure

The project is organized as follows:

*   `api/`: Backend API (FastAPI/Flask) and entry points.
*   `bot/`: Telegram bot logic.
*   `services/`: Core business logic (AI analysis, tracking, blockchain interaction).
*   `database/`: Database models and connection logic.
*   `scripts/`: Utility scripts.

## ⚠️ API Limits & Configuration
We use the **X (Twitter) API Free Tier** by default, which is limited to **100 tweets/month**.
*   The scraper (`services/tracker.py`) is configured to pull **10 tweets per run**.
*   **Do not increase this** unless you have a paid API plan, or you will break the build for other contributors testing the app.

## 🦊 Blockchain Setup (Story Protocol)
To test the IP Minting features:
1.  You need a **MetaMask** wallet.
2.  Export your **Private Key** and add it to `.env`.
3.  Ensure you have **Sepolia ETH** (Testnet tokens) for gas fees.

## Submitting Changes

1.  **Commit your changes** with clear messages.
2.  **Push to your fork**:
    ```bash
    git push origin feature/amazing-feature
    ```
3.  **Open a Pull Request** (PR) on the main repository.

## Code Style

*   Follow PEP 8 guidelines for Python code.
*   Ensure your code is well-documented.

## 💡 Have an Idea?
We are super open to new, innovative ideas! You don't have to stick strictly to the roadmap. If you have a vision for a new feature, a better AI model, or a cool blockchain integration, please:
1.  Open an **Issue** to discuss it.
2.  Or just build a prototype and submit a **Pull Request**!

## Need Help?

If you have questions, feel free to reach out or open an issue.

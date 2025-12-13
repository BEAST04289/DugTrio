# Contributing to DugTrio

Thank you for your interest in contributing to DugTrio! We welcome contributions from the community to help make this project better.

## Getting Started

1.  **Fork the repository** on GitHub.
2.  **Clone your fork** locally:
    ```bash
    git clone https://github.com/your-username/DugTrio.git
    cd DugTrio
    ```
3.  **Set up the environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```
4.  **Create a branch** for your feature or fix:
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

## Need Help?

If you have questions, feel free to reach out or open an issue.

# Telegram Webhook Bot

This project is a simple Telegram bot that listens for updates via a webhook using Flask. It is designed to handle incoming messages and events from Telegram and can be deployed on platforms like Heroku.

## Project Structure

```
telegram-webhook-bot
├── app.py                # Main entry point for the Flask application
├── bot.py                # Contains the logic for handling Telegram updates
├── requirements.txt      # Lists the dependencies required for the project
├── Procfile              # Specifies the command to run the application on Heroku
├── .env.example          # Example environment variables needed for the application
├── runtime.txt           # Specifies the Python version for deployment
├── tests                 # Directory containing unit tests
│   └── test_webhook.py   # Tests for the webhook listener functionality
└── README.md             # Documentation for the project
```

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd telegram-webhook-bot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Copy the `.env.example` to `.env` and fill in your `TELEGRAM_BOT_TOKEN` and `PORT`.

5. **Run the application:**
   ```bash
   gunicorn app:app
   ```

## Usage

Once the application is running, it will listen for incoming updates from Telegram at the specified webhook URL. Make sure to set the webhook using the Telegram Bot API.

## Testing

To run the tests, use the following command:
```bash
pytest tests/test_webhook.py
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.
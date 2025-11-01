# dugtrio-webhook-bot

## Overview
This project is a Telegram webhook bot built using Flask. It listens for incoming updates from Telegram and processes them accordingly. The bot's logic is defined in `bot.py`, while `app.py` serves as the main entry point for the Flask application.

## Project Structure
```
dugtrio-webhook-bot
├── src
│   ├── app.py          # Main entry point for the Flask application
│   └── bot.py          # Contains the main handler logic for the Telegram bot
├── .env                # Environment variables for the bot token and port
├── .gitignore          # Files and directories to be ignored by Git
├── requirements.txt    # List of dependencies for the project
└── README.md           # Documentation for the project
```

## Setup Instructions
1. Clone the repository:
   ```
   git clone <repository-url>
   cd dugtrio-webhook-bot
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory and add your Telegram bot token and port:
   ```
   BOT_TOKEN=your_bot_token_here
   PORT=your_port_here
   ```

## Usage
To start the Flask application, run:
```
python src/app.py
```

The application will listen for incoming updates from Telegram on the specified port.

## Contributing
Feel free to submit issues or pull requests if you have suggestions or improvements for the project.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
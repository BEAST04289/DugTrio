import os
import logging
import asyncio
from flask import Flask, request, abort
from telegram import Update
from bot import application  # must export Application instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set in environment")

PORT = int(os.getenv("PORT", "8443"))

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


@app.route("/<token>", methods=["POST"])
def webhook(token: str):
    if token != TELEGRAM_BOT_TOKEN:
        logger.warning("Received webhook with invalid token")
        abort(403)

    try:
        payload = request.get_json(force=True)
    except Exception:
        logger.exception("Invalid JSON payload")
        abort(400)

    try:
        update = Update.de_json(payload, application.bot)
    except Exception:
        logger.exception("Failed to build Update object")
        abort(400)

    # Process update synchronously by running the application's coroutine
    try:
        asyncio.run(application.process_update(update))
    except Exception:
        logger.exception("Failed to process update")
        abort(500)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
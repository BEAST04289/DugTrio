# ...existing code...
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


# ...existing code...
@app.route("/<token>", methods=["POST"])
def webhook(token: str):
    if token != TELEGRAM_BOT_TOKEN:
        logger.warning("Received webhook with invalid token")
        abort(403)

    payload = request.get_json(silent=True)
    if not payload:
        logger.warning("Empty/invalid JSON payload")
        abort(400)

    try:
        update = Update.de_json(payload, application.bot)
    except Exception as exc:
        logger.exception("Failed to build Update object: %s", exc)
        abort(400)

    # Enqueue update (best-effort; do not let queue failures kill the web process)
    try:
        application.update_queue.put_nowait(update)
    except Exception:
        try:
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(application.update_queue.put(update))
        except Exception:
            logger.exception("Failed to enqueue update; returning 200 to avoid retry storm")
            # Return 200 so Telegram will not immediately retry; investigate and reprocess missed updates later
            return "OK", 200

    return "OK", 200
# ...existing code...


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
# ...existing code...
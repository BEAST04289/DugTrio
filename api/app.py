import os
import logging
import asyncio
import threading
import importlib
from flask import Flask, request, abort, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # do NOT raise here
PORT = int(os.getenv("PORT", "8443"))

app = Flask(__name__)

# Start the PTB Application exported by bot.py lazily and only once
_started = False
_start_lock = threading.Lock()

async def _start_ptb_app(application):
    await application.initialize()
    await application.start()
    # keep the loop alive for the lifetime of the process
    await asyncio.Event().wait()

def ensure_bot_started():
    global _started
    if _started:
        return
    with _start_lock:
        if _started:
            return
        def _runner():
            try:
                bot_mod = importlib.import_module("bot.bot")
                application = getattr(bot_mod, "application")
                asyncio.run(_start_ptb_app(application))
            except Exception as e:
                logger.exception("Failed to start PTB application: %s", e)
        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        _started = True

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

@app.route("/<token>", methods=["POST"])
def webhook(token: str):
    if token != TELEGRAM_BOT_TOKEN:
        logger.warning("Received webhook with invalid token")
        abort(403)

    payload = request.get_json(silent=True)
    if not payload:
        logger.warning("Empty/invalid JSON payload")
        abort(400)

    # Lazy import dependencies so the worker can boot even if packages lag install
    try:
        bot_mod = importlib.import_module("bot")
        application = getattr(bot_mod, "application")
        telegram_mod = importlib.import_module("telegram")
        Update = getattr(telegram_mod, "Update")
    except ModuleNotFoundError as e:
        logger.exception("Missing dependency during webhook handling: %s", e)
        return jsonify({"error": "Missing dependency: python-telegram-bot not installed"}), 503
    except Exception as e:
        logger.exception("Failed to import bot or telegram: %s", e)
        return jsonify({"error": "Internal server error importing bot"}), 500

    # Make sure the PTB application is running and consuming update_queue
    ensure_bot_started()

    try:
        update = Update.de_json(payload, application.bot)
    except Exception as exc:
        logger.exception("Failed to build Update object: %s", exc)
        abort(400)

    # Enqueue update (best-effort)
    try:
        application.update_queue.put_nowait(update)
    except Exception:
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            loop.run_until_complete(application.update_queue.put(update))
        except Exception:
            logger.exception("Failed to enqueue update; returning 200 to avoid retry storm")
            return "OK", 200

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
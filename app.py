import os
import logging
import asyncio
import threading
import importlib
from flask import Flask, request, abort, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set")

application = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello from DugTrio!")

application.add_handler(CommandHandler("start", start))

# Start PTB in a background thread so UpdateQueue is consumed
async def _runner():
    await application.initialize()
    await application.start()
    # keep running; do not call idle() to avoid blocking

threading.Thread(target=lambda: asyncio.run(_runner()), daemon=True).start()
PORT = int(os.getenv("PORT", "8443"))

app = Flask(__name__)


@app.route("/", methods=["GET"])
def health():
    return "OK", 200
@app.route("/<token>", methods=["POST"])
def webhook(token: str):
    if token != TOKEN:
        logger.warning("Received webhook with invalid token")
        abort(403)
        logger.warning("Received webhook with invalid token")
        abort(403)

    payload = request.get_json(silent=True)
    if not payload:
        logger.warning("Empty/invalid JSON payload")
        abort(400)

    # Lazy import to avoid crashing worker when dependencies are missing
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
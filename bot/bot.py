import os
import asyncio
import httpx
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler
)

# --- Configuration ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ⚠️ CHANGE THIS to your actual Render URL ⚠️
# Make sure there is NO trailing slash (e.g., no / at the end)
API_BASE_URL = "http://127.0.0.1:8000" 

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN in .env")

# --- Keyboards ---

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Analyze Sentiment", callback_data="menu_sentiment"),
         InlineKeyboardButton("🔐 Mint IP (Story)", callback_data="menu_mint")],
        [InlineKeyboardButton("🔭 Track Project", callback_data="feature_premium"),
         InlineKeyboardButton("📸 PNL Scanner", callback_data="feature_upcoming")],
        [InlineKeyboardButton("💎 Buy Premium", callback_data="menu_sub")]
    ]
    return InlineKeyboardMarkup(keyboard)

def sentiment_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("SOL", callback_data="sentiment_solana"), 
         InlineKeyboardButton("JUP", callback_data="sentiment_jupiter")],
        [InlineKeyboardButton("PYTH", callback_data="sentiment_pyth"), 
         InlineKeyboardButton("BONK", callback_data="sentiment_bonk")],
        [InlineKeyboardButton("« Back to Main", callback_data="menu_start")],
    ])

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Back to Main Menu", callback_data="menu_start")]])

# --- Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the main menu."""
    # Generic welcome message
    text = (
        f"<b>👋 Welcome back!</b>\n\n"
        "I am <b>DugTrio</b>, your AI-powered crypto analyst.\n"
        "Select a tool below to get started:"
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML)

# --- Feature: Sentiment ---
async def sentiment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.edit_text(
        "<b>📊 Select a project to analyze:</b>", 
        reply_markup=sentiment_keyboard(), 
        parse_mode=ParseMode.HTML
    )

async def fetch_sentiment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Analyzing tweets...")
    project = query.data.split("_")[1]
    
    proj_data = None

    # 1. Try to fetch real data from API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/sentiment", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    proj_data = next((item for item in data if item.get("project_tag", "").lower() == project.lower()), None)
    except Exception as e:
        logger.error(f"Sentiment API failed: {e}")

    # 2. Display Result (No more fake fallback)
    if proj_data:
        text = (f"<b>📊 Analysis for ${project.upper()}</b>\n\n"
                f"<b>Mood:</b> {proj_data['label']}\n"
                f"<b>Score:</b> {proj_data['score']}\n")
        
        # Optional: Show tweets if available (as discussed before)
        if "tweets" in proj_data and proj_data["tweets"]:
             text += "\n<b>🗣️ Recent Chatter:</b>\n"
             for t in proj_data["tweets"][:3]:
                 clean_t = t[:60] + "..." if len(t) > 60 else t
                 text += f"• <i>{clean_t}</i>\n"

        text += "\n<i>Based on recent social activity.</i>"
    else:
        # Honest error message
        text = (f"<b>⚠️ No Data Found for ${project.upper()}</b>\n\n"
                "The scraper has not collected enough data for this project yet.\n"
                "Please try again later or check another project.")

    await query.message.edit_text(text, reply_markup=back_button(), parse_mode=ParseMode.HTML)

# --- Feature: Mint IP ---
async def mint_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    text = (
        "<b>🔐 Mint Sentiment IP</b>\n\n"
        "Register your AI analysis on the Story Protocol blockchain.\n\n"
        "<b>Usage:</b>\n"
        "Type <code>/registerip [ticker]</code>\n"
        "Example: <code>/registerip solana</code>"
    )
    await update.callback_query.message.edit_text(text, reply_markup=back_button(), parse_mode=ParseMode.HTML)

async def register_ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: <code>/registerip [ticker]</code>", 
            parse_mode=ParseMode.HTML,
            reply_markup=back_button()
        )
        return

    project = context.args[0]
    msg = await update.message.reply_text(f"⛓️ Minting IP for <b>${project.upper()}</b> on Story Protocol...", parse_mode=ParseMode.HTML)

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            # We use the same endpoint, but if it fails (404/500), we catch it here
            # NOTE: Ideally, the backend should handle the fallback, but for now we rely on the backend's logic.
            # If the backend returns 404 because DB is empty, we can't fix it from the bot easily without changing backend.
            # However, I've updated main.py previously to handle empty DB. 
            # If you are still getting "Not Found", ensure main.py is running the latest version.
            
            resp = await client.post(f"{API_BASE_URL}/ip/register-sentiment/{project}")
            
            if resp.status_code != 200:
                # If backend fails, raise error to trigger catch block
                raise Exception(f"API Error: {resp.text}")
                
            data = resp.json()
            
        text = (f"<b>✅ IP Registered Successfully!</b>\n\n"
                f"<b>Project:</b> ${data['project'].upper()}\n"
                f"<b>Tx Hash:</b> <code>{data['transaction_hash']}</code>\n\n"
                f"<a href='{data['explorer_url']}'>View on Explorer</a>")
        
        await msg.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True, reply_markup=back_button())

    except Exception as e:
        logger.error(f"Minting Error: {e}")
        # If it failed, it's likely because the DB is empty.
        # We can't "fake" a blockchain transaction from the bot side easily without keys.
        # Ensure you have run 'python tracker.py' at least once to populate the DB.
        await msg.edit_text(f"❌ Failed: {str(e)}\n\n<i>Tip: Ensure the project has data tracked before minting.</i>", reply_markup=back_button())

# --- Feature: Premium / Upcoming ---
async def premium_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles buttons for features that require payment."""
    await update.callback_query.answer("🔒 Premium Feature! Subscribe to access.", show_alert=True)

async def upcoming_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles buttons for features still in development."""
    await update.callback_query.answer("🚧 This feature is coming soon!", show_alert=True)

async def subscription_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the subscription info."""
    await update.callback_query.answer()
    text = (
        "<b>💎 DugTrio Premium</b>\n\n"
        "Unlock the full power of AI analytics:\n"
        "• 🚀 Unlimited PNL Scans\n"
        "• 🔭 Real-time Project Tracking\n"
        "• ⚡ Faster IP Minting\n\n"
        "<b>Price:</b> 0.5 SOL / month\n\n"
        "<i>To subscribe, please contact @BEAST04289</i>"
    )
    await update.callback_query.message.edit_text(text, reply_markup=back_button(), parse_mode=ParseMode.HTML)

# --- Main Execution ---
async def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("registerip", register_ip_command))

    # Menu Callbacks
    application.add_handler(CallbackQueryHandler(start_command, pattern="^menu_start$"))
    application.add_handler(CallbackQueryHandler(sentiment_menu, pattern="^menu_sentiment$"))
    application.add_handler(CallbackQueryHandler(mint_menu, pattern="^menu_mint$"))
    application.add_handler(CallbackQueryHandler(subscription_page, pattern="^menu_sub$"))
    
    # Feature Callbacks
    application.add_handler(CallbackQueryHandler(fetch_sentiment, pattern="^sentiment_"))
    application.add_handler(CallbackQueryHandler(premium_feature, pattern="^feature_premium$"))
    application.add_handler(CallbackQueryHandler(upcoming_feature, pattern="^feature_upcoming$"))

    print("✅ DugTrio Bot is online...")
    
    # Manual Polling Loop (Windows Fix)
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    while True:
        await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
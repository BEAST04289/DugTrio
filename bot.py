import os
import asyncio
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler
)
from typing import Optional

# --- Configuration ---
load_dotenv()

# Load Bot Token from .env file
token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file. Please add it.")
TELEGRAM_BOT_TOKEN: str = token

# Load Backend API URL from .env file, with a default for convenience
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://dugtrio-backend.onrender.com")


# --- UI: Keyboards ---

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Check Sentiment", callback_data="menu_sentiment"),
            InlineKeyboardButton("🔥 Top Projects", callback_data="menu_topprojects"),
        ],
        [
            InlineKeyboardButton("📸 PNL Viewer", callback_data="menu_analyze_pnl"),
            InlineKeyboardButton("📈 Statistics", callback_data="menu_stats"),
        ],
        [InlineKeyboardButton("➕ Track New Project", callback_data="menu_track_project")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_sentiment_keyboard() -> InlineKeyboardMarkup:
    """Returns the sentiment menu keyboard with popular projects."""
    keyboard = [
        [
            InlineKeyboardButton("SOL", callback_data="sentiment_solana"),
            InlineKeyboardButton("JUP", callback_data="sentiment_jupiter"),
        ],
        [
            InlineKeyboardButton("PYTH", callback_data="sentiment_pyth"),
            InlineKeyboardButton("BONK", callback_data="sentiment_bonk"),
        ],
        [InlineKeyboardButton("« Back to Main Menu", callback_data="menu_start")],
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Bot Logic: Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and main menu navigation."""
    welcome_message = (
        "<b>⛏️ DugTrio is Online. Ready to Unearth Alpha! 🚀</b>\n\n"
        "<i>Your AI-powered analytics system for the Solana ecosystem is live.</i>\n\n"
        "Use the buttons below to navigate or type a command like <code>/sentiment solana</code>."
    )
    
    query = update.callback_query
    if query:
        # If called from a button, answer the callback and edit the message
        await query.answer()
        if query.message:
            await query.message.edit_text(
                welcome_message, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML
            )
    elif update.message:
        # If called by command, send a new message
        await update.message.reply_text(
            welcome_message, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML
        )


async def sentiment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the sentiment analysis menu."""
    message_text = (
        "<b>📊 Sentiment Analysis</b>\n\n"
        "Choose a project from the buttons or type the command manually:\n"
        "<code>/sentiment [project_name]</code>"
    )
    query = update.callback_query
    if query:
        await query.answer()
        if query.message:
            await query.message.edit_text(
                message_text, reply_markup=get_sentiment_keyboard(), parse_mode=ParseMode.HTML
            )


async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays aggregated sentiment for a project."""
    project_name: Optional[str] = None
    query = update.callback_query

    if query:
        await query.answer()
        # Extract project name from callback data like "sentiment_solana"
        project_name = query.data.split("_", 1)[1]
        # Show a "loading" message
        await query.message.edit_text(
            f"<i>⛏️ Digging for <b>${project_name.upper()}</b> sentiment...</i>",
            parse_mode=ParseMode.HTML
        )
    elif context.args and update.message:
        project_name = context.args[0]
        await update.message.reply_text(
            f"<i>⛏️ Digging for <b>${project_name.upper()}</b> sentiment...</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        # If command is used without arguments, show the menu
        await sentiment_menu(update, context)
        return

    if not project_name:
        await context.bot.send_message(update.effective_chat.id, "Could not determine project.", reply_markup=get_sentiment_keyboard())
        return

    try:
        async with httpx.AsyncClient() as client:
            # This endpoint should return a list of all sentiment results
            response = await client.get(f"{API_BASE_URL}/sentiment", timeout=30.0)
            response.raise_for_status()
        
        all_sentiments = response.json()
        project_sentiments = [s for s in all_sentiments if s.get("project_tag", "").lower() == project_name.lower()]

        if not project_sentiments:
            reply = f"😕 No sentiment data found for <b>${project_name.upper()}</b>. It may not be tracked yet."
        else:
            # Aggregate the results
            total = len(project_sentiments)
            positive = sum(1 for s in project_sentiments if s.get("label", "").lower() == "positive")
            negative = sum(1 for s in project_sentiments if s.get("label", "").lower() == "negative")
            neutral = total - positive - negative
            
            pos_pct = (positive / total * 100) if total else 0
            mood = "🟢 Bullish" if pos_pct >= 50 else "🟡 Neutral" if pos_pct >= 35 else "🔴 Bearish"

            reply = (
                f"<b>📈 Sentiment for ${project_name.upper()}</b>\n\n"
                f"<b>Overall Mood:</b> {mood}\n"
                f"<i>(Based on {total} tweets)</i>\n\n"
                f"😊 Positive: <code>{pos_pct:.1f}%</code>\n"
                f"😐 Neutral: <code>{(neutral / total * 100):.1f}%</code>\n"
                f"😞 Negative: <code>{(negative / total * 100):.1f}%</code>"
            )
        
        # Edit the original "loading" message with the final result
        if query and query.message:
            await query.message.edit_text(reply, reply_markup=get_sentiment_keyboard(), parse_mode=ParseMode.HTML)
        elif update.message:
            await update.message.reply_text(reply, reply_markup=get_sentiment_keyboard(), parse_mode=ParseMode.HTML)

    except Exception as e:
        error_message = f"❌ An error occurred: {e}"
        if query and query.message:
            await query.message.edit_text(error_message, reply_markup=get_sentiment_keyboard())
        elif update.message:
            await update.message.reply_text(error_message, reply_markup=get_sentiment_keyboard())


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays overall system statistics."""
    message_text = "<i>📊 Fetching system statistics...</i>"
    query = update.callback_query
    
    if query:
        await query.answer()
        await query.message.edit_text(message_text, parse_mode=ParseMode.HTML)
    elif update.message:
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

    try:
        async with httpx.AsyncClient() as client:
            # Make API calls to get counts
            tweets_resp = await client.get(f"{API_BASE_URL}/tweets", timeout=15.0)
            pnl_resp = await client.get(f"{API_BASE_URL}/pnl-cards", timeout=15.0)
            projects_resp = await client.get(f"{API_BASE_URL}/track-requests", timeout=15.0)

        tweets_count = len(tweets_resp.json()) if tweets_resp.status_code == 200 else "N/A"
        pnl_count = len(pnl_resp.json()) if pnl_resp.status_code == 200 else "N/A"
        projects_count = len(projects_resp.json()) if projects_resp.status_code == 200 else "N/A"

        reply = (
            f"<b>📈 DugTrio System Statistics</b>\n\n"
            f"🐦 <b>Total Tweets Analyzed:</b> <code>{tweets_count}</code>\n"
            f"💰 <b>PNL Cards Generated:</b> <code>{pnl_count}</code>\n"
            f"📁 <b>Tracked Projects:</b> <code>{projects_count}</code>\n\n"
            f"✅ <b>API Status:</b> Online"
        )
        
        if query and query.message:
            await query.message.edit_text(reply, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)
        elif update.message:
            await update.message.reply_text(reply, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML)

    except Exception as e:
        await context.bot.send_message(update.effective_chat.id, f"❌ Error fetching stats: {e}", reply_markup=get_main_menu_keyboard())

# --- Other handlers for PNL, Tracking, etc. would go here ---
# (This is a simplified example focusing on the main structure)


async def main() -> None:
    """Sets up and runs the bot using an explicit asyncio event loop."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("sentiment", sentiment_command))

    # Callback Query Handlers (for buttons)
    application.add_handler(CallbackQueryHandler(start_command, pattern="^menu_start$"))
    application.add_handler(CallbackQueryHandler(sentiment_menu, pattern="^menu_sentiment$"))
    application.add_handler(CallbackQueryHandler(stats_command, pattern="^menu_stats$"))
    
    # This handler catches all sentiment buttons like "sentiment_solana"
    application.add_handler(CallbackQueryHandler(sentiment_command, pattern="^sentiment_"))

    # Run the bot until the user presses Ctrl-C
    print("✅ DugTrio Bot is online and polling for messages...")
    # The run_polling() method is a shortcut for the following calls
    # which we do manually here to ensure the event loop is handled correctly.
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Keep the script running
    while True:
        await asyncio.sleep(3600) # Sleep for an hour, then loop again


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped manually.")

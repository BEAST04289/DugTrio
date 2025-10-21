import os
import httpx
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)
from typing import Optional

# --- Load Environment Variables & Constants ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# This check is critical. It confirms the token was loaded and satisfies the type checker.
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("FATAL ERROR: TELEGRAM_BOT_TOKEN not found in .env file. Please check your configuration.")

# --- UI Keyboard Definitions (The Buttons) ---

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Returns the main navigation menu with all feature buttons."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Check Sentiment", callback_data='menu_sentiment'),
            InlineKeyboardButton("🔥 Top Projects", callback_data='menu_topprojects')
        ],
        [
            InlineKeyboardButton("📸 PNL Viewer", callback_data='menu_analyze_pnl'),
            InlineKeyboardButton("📈 Statistics", callback_data='menu_stats')
        ],
        [
            InlineKeyboardButton("➕ Track Project", callback_data='menu_track_project')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_sentiment_keyboard(project_name: Optional[str] = None) -> InlineKeyboardMarkup:
    """
    Returns the secondary menu for sentiment checks.
    If a project_name is provided, it adds a button to view sentiment details.
    """
    keyboard = [
        [
            InlineKeyboardButton("SOL", callback_data='sentiment_solana'),
            InlineKeyboardButton("JUP", callback_data='sentiment_jupiter')
        ],
        [
            InlineKeyboardButton("PYTH", callback_data='sentiment_pyth'),
            InlineKeyboardButton("BONK", callback_data='sentiment_bonk')
        ]
    ]
    
    keyboard.append([InlineKeyboardButton("« Back to Main Menu", callback_data='menu_start')])
    return InlineKeyboardMarkup(keyboard)

# Helper utilities to avoid edit_text
async def send_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None, disable_web_page_preview: Optional[bool] = None):
    if not update.effective_chat:
        return None
    chat_id = update.effective_chat.id
    return await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=disable_web_page_preview
    )

async def safe_delete_message(message):
    try:
        await message.delete()
    except Exception:
        pass

# --- Core Command & Callback Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command and 'Back to Main Menu' button presses."""
    welcome_message = (
        "<b>⛏️ DugTrio is Online. Ready to Unearth Alpha! 🚀</b>\n\n"
        "<i>Your AI-powered analytics system for the Solana ecosystem is live.</i>\n\n"
        "Use the buttons below to navigate or type a command like <code>/sentiment solana</code>."
    )
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.message:
            await safe_delete_message(query.message)
        await send_new_message(update, context, welcome_message, reply_markup=get_main_menu_keyboard())
    elif update.message:
        await update.message.reply_text(
            welcome_message, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /help command by reusing the start message."""
    await start_command(update, context)


async def sentiment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the sentiment sub-menu when the 'Check Sentiment' button is pressed."""
    message = (
        "<b>📊 Sentiment Analysis</b>\n\n"
        "Choose a popular project below or type your own:\n"
        "<code>/sentiment [project_name]</code>\n\n"
        "Example: <code>/sentiment solana</code>"
    )
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.message:
            await safe_delete_message(query.message)
        await send_new_message(update, context, message, reply_markup=get_sentiment_keyboard())


async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles sentiment requests from both commands and buttons.
    Fetches data from the local DugTrio API.
    """
    project_name: Optional[str] = None
    status_message = None
    query = update.callback_query

    if query:
        await query.answer()
        try:
            if query.data:
                project_name = query.data.split('_', 1)[1]
        except Exception:
            project_name = None
        if query.message:
            await safe_delete_message(query.message)
        status_message = await send_new_message(
            update, context, f"<i>⛏️ Digging for {project_name.capitalize() if project_name else 'project'} sentiment...</i>"
        )
    elif context.args and update.message:
        project_name = context.args[0]
        status_message = await update.message.reply_text(
            text=f"<i>⛏️ Digging for {project_name.capitalize()} sentiment...</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        if update.message:
            await update.message.reply_text(
                "Please specify a project. Usage: `/sentiment solana`",
                reply_markup=get_sentiment_keyboard(),
                parse_mode=ParseMode.HTML
            )
        return

    if not project_name:
        await send_new_message(update, context, "⚠️ Could not determine the project. Please try again.", reply_markup=get_sentiment_keyboard())
        if status_message:
            await safe_delete_message(status_message)
        return

    try:
        async with httpx.AsyncClient() as client:
            # Fetch sentiment analysis from local API
            response = await client.get(f"{API_BASE_URL}/sentiment", timeout=30.0)
        
        response.raise_for_status()
        all_sentiments = response.json()
        
        # Filter sentiments for the requested project
        project_sentiments = [s for s in all_sentiments if s.get('project_tag', '').lower() == project_name.lower()]
        
        if not project_sentiments:
            reply = f"😕 No sentiment data found for <b>{project_name.upper()}</b>. Try tracking it first with <code>/track {project_name}</code>"
            await send_new_message(update, context, reply, reply_markup=get_sentiment_keyboard(project_name=project_name))
            if status_message:
                await safe_delete_message(status_message)
            return
        
        # Calculate sentiment statistics
        positive = sum(1 for s in project_sentiments if s.get('label', '').lower() == 'positive')
        negative = sum(1 for s in project_sentiments if s.get('label', '').lower() == 'negative')
        neutral = sum(1 for s in project_sentiments if s.get('label', '').lower() == 'neutral')
        total = len(project_sentiments)
        
        positive_pct = (positive / total * 100) if total > 0 else 0
        negative_pct = (negative / total * 100) if total > 0 else 0
        neutral_pct = (neutral / total * 100) if total > 0 else 0
        
        # Determine overall mood
        if positive_pct >= 60:
            mood = "🟢 Very Bullish"
        elif positive_pct >= 45:
            mood = "🟢 Bullish"
        elif positive_pct >= 35:
            mood = "🟡 Neutral"
        elif positive_pct >= 25:
            mood = "🟠 Cautious"
        else:
            mood = "🔴 Bearish"
        
        # Get the most confident sentiment
        top_sentiment = max(project_sentiments, key=lambda x: x.get('confidence', 0))
        
        reply_parts = [
            f"<b>📈 Sentiment for {project_name.upper()}</b>\n",
            f"<b>Overall Mood:</b> {mood}",
            f"<b>Analyzed Tweets:</b> <code>{total}</code>\n",
            f"😊 Positive: <code>{positive_pct:.1f}%</code> ({positive} tweets)",
            f"😐 Neutral: <code>{neutral_pct:.1f}%</code> ({neutral} tweets)",
            f"😞 Negative: <code>{negative_pct:.1f}%</code> ({negative} tweets)",
        ]
        
        if top_sentiment:
            conf = top_sentiment.get('confidence', 0) * 100
            label = top_sentiment.get('label', 'N/A')
            reply_parts.append(
                f"\n<b>🔝 Most Confident Analysis:</b>\n"
                f"<i>{label.capitalize()} ({conf:.1f}% confidence)</i>"
            )
        
        reply = "\n".join(reply_parts)
        
        await send_new_message(
            update,
            context,
            reply,
            reply_markup=get_sentiment_keyboard(project_name=project_name),
            disable_web_page_preview=True
        )

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            reply = f"⚠️ No data found for <b>{project_name.upper()}</b>. The tracker may not have this token yet."
        else:
            reply = f"❌ Server error: Could not retrieve data ({e.response.status_code}). Please try again."
        await send_new_message(update, context, reply, reply_markup=get_sentiment_keyboard(project_name=project_name))
    except Exception as e:
        reply = f"❌ An unexpected error occurred: {e}"
        await send_new_message(update, context, reply, reply_markup=get_sentiment_keyboard(project_name=project_name))
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def analyze_pnl_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts the user to view PNL cards."""
    query = update.callback_query
    if query:
        await query.answer()
        if query.message:
            await safe_delete_message(query.message)
    
    status_message = await send_new_message(update, context, "<i>📸 Fetching PNL cards...</i>")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/pnl-cards", timeout=30.0)
        
        response.raise_for_status()
        pnl_cards = response.json()
        
        if not pnl_cards:
            reply = "😕 No PNL cards found yet. The analyzer hasn't detected any PNL images."
        else:
            reply_parts = [f"<b>📸 Recent PNL Cards ({len(pnl_cards)} found)</b>\n"]
            for i, card in enumerate(pnl_cards[:10], 1):  # Show first 10
                project = card.get('project_tag', 'Unknown')
                pnl_value = card.get('pnl_value', 'N/A')
                tweet_id = card.get('tweet_id', 'N/A')
                reply_parts.append(f"{i}. <b>{project}</b>: {pnl_value} (Tweet ID: {tweet_id})")
            
            if len(pnl_cards) > 10:
                reply_parts.append(f"\n<i>...and {len(pnl_cards) - 10} more</i>")
            
            reply = "\n".join(reply_parts)
        
        await send_new_message(
            update, context, reply, reply_markup=get_main_menu_keyboard(), disable_web_page_preview=True
        )
    except httpx.HTTPStatusError as e:
        reply = f"❌ Server error: Could not retrieve PNL data ({e.response.status_code})."
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        reply = f"❌ An unexpected error occurred: {e}"
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def track_project_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompts user to track a new project."""
    query = update.callback_query
    if query:
        await query.answer()
        if query.message:
            await safe_delete_message(query.message)
        await send_new_message(
            update, context,
            "<b>➕ Track New Project</b>\n\n"
            "Please send the command:\n<code>/track [project_name]</code>\n\n"
            "Example: <code>/track solana</code>",
            reply_markup=get_main_menu_keyboard()
        )


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a new project to track."""
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "❓ Please provide a project name.\n\n"
                "<b>Usage:</b> <code>/track solana</code>",
                parse_mode=ParseMode.HTML
            )
        return
    
    project_name = context.args[0].lower()
    status_message = None
    
    if update.message:
        status_message = await update.message.reply_text(
            f"<i>Adding {project_name} to tracker...</i>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/track-request",
                json={"project_name": project_name},
                timeout=30.0
            )
        
        if response.status_code == 200:
            reply = f"✅ Successfully added <b>{project_name}</b> to tracking!"
        elif response.status_code == 400:
            reply = f"⚠️ <b>{project_name}</b> is already being tracked."
        else:
            reply = "❌ Failed to add project. Please try again later."
        
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    
    except Exception as e:
        reply = f"❌ An error occurred: {e}"
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def top_projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays all tracked projects."""
    query = update.callback_query
    if query and query.message:
        await query.answer()
        await safe_delete_message(query.message)
        status_message = await send_new_message(update, context, "<i>🔥 Fetching tracked projects...</i>")
    elif update.message:
        status_message = await update.message.reply_text(
            "<i>🔥 Fetching tracked projects...</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        return

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/track-requests", timeout=30.0)

        response.raise_for_status()
        projects = response.json()

        if not projects:
            reply = "😕 No projects are being tracked yet."
        else:
            reply_parts = [f"<b>🔥 Tracked Projects ({len(projects)})</b>\n"]
            for i, project in enumerate(projects, 1):
                project_name = project.get('project_name', 'Unknown')
                reply_parts.append(f"{i}. <code>{project_name}</code>")
            reply = "\n".join(reply_parts)

        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except httpx.HTTPStatusError as e:
        reply = f"❌ Server error: Could not retrieve data ({e.response.status_code}). Please try again."
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        reply = f"❌ An unexpected error occurred: {e}"
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get system statistics."""
    query = update.callback_query
    if query and query.message:
        await query.answer()
        await safe_delete_message(query.message)
        status_message = await send_new_message(update, context, "<i>📊 Fetching statistics...</i>")
    elif update.message:
        status_message = await update.message.reply_text(
            "<i>📊 Fetching statistics...</i>",
            parse_mode=ParseMode.HTML
        )
    else:
        return
    
    try:
        async with httpx.AsyncClient() as client:
            # Fetch all data
            tweets_response = await client.get(f"{API_BASE_URL}/tweets", timeout=30.0)
            sentiment_response = await client.get(f"{API_BASE_URL}/sentiment", timeout=30.0)
            pnl_response = await client.get(f"{API_BASE_URL}/pnl-cards", timeout=30.0)
            projects_response = await client.get(f"{API_BASE_URL}/track-requests", timeout=30.0)
        
        tweets_count = len(tweets_response.json()) if tweets_response.status_code == 200 else 0
        sentiment_count = len(sentiment_response.json()) if sentiment_response.status_code == 200 else 0
        pnl_count = len(pnl_response.json()) if pnl_response.status_code == 200 else 0
        projects_count = len(projects_response.json()) if projects_response.status_code == 200 else 0
        
        reply = f"""<b>📊 DugTrio System Statistics</b>

🐦 <b>Total Tweets:</b> <code>{tweets_count}</code>
🧠 <b>Sentiment Analyses:</b> <code>{sentiment_count}</code>
💰 <b>PNL Cards:</b> <code>{pnl_count}</code>
📁 <b>Tracked Projects:</b> <code>{projects_count}</code>

✅ <b>API Status:</b> Online
🌐 <b>Server:</b> {API_BASE_URL}
"""
        
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        reply = f"❌ An error occurred while fetching statistics: {e}"
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def tweets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get recent tweets for a project."""
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "❓ Please provide a project name.\n\n"
                "<b>Usage:</b> <code>/tweets solana</code>",
                parse_mode=ParseMode.HTML
            )
        return
    
    project_tag = context.args[0].lower()
    status_message = None
    
    if update.message:
        status_message = await update.message.reply_text(
            f"<i>🐦 Fetching tweets for {project_tag}...</i>",
            parse_mode=ParseMode.HTML
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/tweets/{project_tag}", timeout=30.0)
        
        response.raise_for_status()
        tweets = response.json()
        
        if not tweets:
            reply = f"📭 No tweets found for <b>{project_tag.upper()}</b>."
        else:
            reply_parts = [f"<b>🐦 Recent Tweets for {project_tag.upper()}</b>\n"]
            
            for i, tweet in enumerate(tweets[:5], 1):  # Show first 5
                author = tweet.get('author_username', 'Unknown')
                text = tweet.get('tweet_text', '')[:100]
                reply_parts.append(f"{i}. <b>@{author}</b>\n{text}...\n")
            
            if len(tweets) > 5:
                reply_parts.append(f"<i>...and {len(tweets) - 5} more tweets</i>")
            
            reply = "\n".join(reply_parts)
        
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            reply = f"⚠️ No tweets found for <b>{project_tag.upper()}</b>."
        else:
            reply = f"❌ Server error: Could not retrieve tweets ({e.response.status_code})."
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        reply = f"❌ An error occurred: {e}"
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


# --- Main Bot Logic ---

def main() -> None:
    """Starts the bot and registers all the different ways a user can interact."""
    assert TELEGRAM_BOT_TOKEN is not None  # Type narrowing for type checker
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    print("✅ DugTrio Bot is online...")

    # Register handlers for simple text commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("sentiment", sentiment_command))
    application.add_handler(CommandHandler("track", track_command))
    application.add_handler(CommandHandler("tweets", tweets_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # Register handlers for main menu button presses, using their callback_data
    application.add_handler(CallbackQueryHandler(start_command, pattern=r'^menu_start$'))
    application.add_handler(CallbackQueryHandler(sentiment_menu, pattern=r'^menu_sentiment$'))
    application.add_handler(CallbackQueryHandler(analyze_pnl_prompt, pattern=r'^menu_analyze_pnl$'))
    application.add_handler(CallbackQueryHandler(track_project_prompt, pattern=r'^menu_track_project$'))
    application.add_handler(CallbackQueryHandler(top_projects_command, pattern=r'^menu_topprojects$'))
    application.add_handler(CallbackQueryHandler(stats_command, pattern=r'^menu_stats$'))

    # Sentiment actions
    application.add_handler(CallbackQueryHandler(sentiment_command, pattern=r'^sentiment_'))

    application.run_polling()


if __name__ == "__main__":
    main()
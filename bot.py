import os
import httpx
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler
)
from typing import Optional
# ...existing code...

# --- Load Environment Variables & Constants ---
load_dotenv()

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise ValueError("FATAL ERROR: TELEGRAM_BOT_TOKEN not found in .env file. Please check your configuration.")
TELEGRAM_BOT_TOKEN: str = token

API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
# ...existing code...
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("FATAL ERROR: TELEGRAM_BOT_TOKEN not found in .env file. Please check your configuration.")

# --- UI Keyboards ---
def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📊 Check Sentiment", callback_data="menu_sentiment"),
            InlineKeyboardButton("🔥 Top Projects", callback_data="menu_topprojects"),
        ],
        [
            InlineKeyboardButton("📸 PNL Viewer", callback_data="menu_analyze_pnl"),
            InlineKeyboardButton("📈 Statistics", callback_data="menu_stats"),
        ],
        [InlineKeyboardButton("➕ Track Project", callback_data="menu_track_project")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_sentiment_keyboard(project_name: Optional[str] = None) -> InlineKeyboardMarkup:
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

# --- Helpers ---
async def send_new_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
    disable_web_page_preview: Optional[bool] = None,
):
    if not update.effective_chat:
        return None
    return await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=disable_web_page_preview,
    )


async def safe_delete_message(message):
    try:
        await message.delete()
    except Exception:
        pass

# --- Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = (
        "<b>⛏️ DugTrio is Online. Ready to Unearth Alpha! 🚀</b>\n\n"
        "<i>Your AI-powered analytics system for the Solana ecosystem is live.</i>\n\n"
        "Use the buttons below or type <code>/sentiment solana</code>."
    )
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        if q.message:
            await safe_delete_message(q.message)
        await send_new_message(update, context, welcome_message, reply_markup=get_main_menu_keyboard())
    elif update.message:
        await update.message.reply_text(
            welcome_message, reply_markup=get_main_menu_keyboard(), parse_mode=ParseMode.HTML
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def sentiment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "<b>📊 Sentiment Analysis</b>\n\n"
        "Choose a project or type:\n"
        "<code>/sentiment [project]</code>\n"
        "Example: <code>/sentiment solana</code>"
    )
    if update.callback_query:
        q = update.callback_query
        await q.answer()
        if q.message:
            await safe_delete_message(q.message)
        await send_new_message(update, context, msg, reply_markup=get_sentiment_keyboard())


async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    project_name: Optional[str] = None
    status_message = None
    q = update.callback_query

    if q:
        await q.answer()
        try:
            if q.data:
                project_name = q.data.split("_", 1)[1]
        except Exception:
            project_name = None
        if q.message:
            await safe_delete_message(q.message)
        status_message = await send_new_message(
            update, context, f"<i>⛏️ Digging for {project_name.capitalize() if project_name else 'project'} sentiment...</i>"
        )
    elif context.args and update.message:
        project_name = context.args[0]
        status_message = await update.message.reply_text(
            text=f"<i>⛏️ Digging for {project_name.capitalize()} sentiment...</i>", parse_mode=ParseMode.HTML
        )
    else:
        if update.message:
            await update.message.reply_text(
                "Please specify a project. Usage: <code>/sentiment solana</code>",
                reply_markup=get_sentiment_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        return

    if not project_name:
        await send_new_message(update, context, "⚠️ Could not determine the project.", reply_markup=get_sentiment_keyboard())
        if status_message:
            await safe_delete_message(status_message)
        return

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/sentiment", timeout=30.0)
        resp.raise_for_status()
        all_sentiments = resp.json()

        items = [s for s in all_sentiments if s.get("project_tag", "").lower() == project_name.lower()]
        if not items:
            reply = (
                f"😕 No sentiment data for <b>{project_name.upper()}</b>.\n"
                f"Try tracking it first: <code>/track {project_name}</code>"
            )
            await send_new_message(update, context, reply, reply_markup=get_sentiment_keyboard(project_name=project_name))
            if status_message:
                await safe_delete_message(status_message)
            return

        positive = sum(1 for s in items if s.get("label", "").lower() == "positive")
        negative = sum(1 for s in items if s.get("label", "").lower() == "negative")
        neutral = sum(1 for s in items if s.get("label", "").lower() == "neutral")
        total = len(items)

        pos_pct = (positive / total * 100) if total else 0
        neg_pct = (negative / total * 100) if total else 0
        neu_pct = (neutral / total * 100) if total else 0

        if pos_pct >= 60:
            mood = "🟢 Very Bullish"
        elif pos_pct >= 45:
            mood = "🟢 Bullish"
        elif pos_pct >= 35:
            mood = "🟡 Neutral"
        elif pos_pct >= 25:
            mood = "🟠 Cautious"
        else:
            mood = "🔴 Bearish"

        top = max(items, key=lambda x: x.get("confidence", 0), default=None)

        parts = [
            f"<b>📈 Sentiment for {project_name.upper()}</b>\n",
            f"<b>Overall Mood:</b> {mood}",
            f"<b>Analyzed Tweets:</b> <code>{total}</code>\n",
            f"😊 Positive: <code>{pos_pct:.1f}%</code> ({positive})",
            f"😐 Neutral: <code>{neu_pct:.1f}%</code> ({neutral})",
            f"😞 Negative: <code>{neg_pct:.1f}%</code> ({negative})",
        ]
        if top:
            conf = (top.get("confidence", 0) or 0) * 100
            label = top.get("label", "N/A")
            parts.append(f"\n<b>🔝 Most Confident:</b> <i>{label.capitalize()} ({conf:.1f}% confidence)</i>")

        reply = "\n".join(parts)
        await send_new_message(
            update, context, reply, reply_markup=get_sentiment_keyboard(project_name=project_name), disable_web_page_preview=True
        )
    except httpx.HTTPStatusError as e:
        await send_new_message(
            update, context, f"❌ Server error ({e.response.status_code}).", reply_markup=get_sentiment_keyboard()
        )
    except Exception as e:
        await send_new_message(update, context, f"❌ Error: {e}", reply_markup=get_sentiment_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def analyze_pnl_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q:
        await q.answer()
        if q.message:
            await safe_delete_message(q.message)

    status_message = await send_new_message(update, context, "<i>📸 Fetching PNL cards...</i>")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/pnl-cards", timeout=30.0)
        resp.raise_for_status()
        pnl_cards = resp.json()

        if not pnl_cards:
            reply = "😕 No PNL cards found yet."
        else:
            parts = [f"<b>📸 Recent PNL Cards ({len(pnl_cards)})</b>\n"]
            for i, card in enumerate(pnl_cards[:10], 1):
                project = card.get("project_tag", "Unknown")
                pnl_value = card.get("pnl_value", "N/A")
                tweet_id = card.get("tweet_id", "N/A")
                parts.append(f"{i}. <b>{project}</b>: {pnl_value} (Tweet ID: {tweet_id})")
            if len(pnl_cards) > 10:
                parts.append(f"\n<i>...and {len(pnl_cards) - 10} more</i>")
            reply = "\n".join(parts)

        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard(), disable_web_page_preview=True)
    except httpx.HTTPStatusError as e:
        await send_new_message(update, context, f"❌ Server error ({e.response.status_code}).", reply_markup=get_main_menu_keyboard())
    except Exception as e:
        await send_new_message(update, context, f"❌ Error: {e}", reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def track_project_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if q:
        await q.answer()
        if q.message:
            await safe_delete_message(q.message)
        await send_new_message(
            update,
            context,
            "<b>➕ Track New Project</b>\n\nSend:\n<code>/track [project_name]</code>\n\nExample: <code>/track solana</code>",
            reply_markup=get_main_menu_keyboard(),
        )


async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "❓ Please provide a project name.\n\n<b>Usage:</b> <code>/track solana</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    project_name = context.args[0].lower()
    status_message = None
    if update.message:
        status_message = await update.message.reply_text(
            f"<i>Adding {project_name} to tracker...</i>", parse_mode=ParseMode.HTML
        )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{API_BASE_URL}/track-request", json={"project_name": project_name}, timeout=30.0)

        if resp.status_code == 200:
            reply = f"✅ Added <b>{project_name}</b> to tracking!"
        elif resp.status_code == 400:
            reply = f"⚠️ <b>{project_name}</b> is already being tracked."
        else:
            reply = "❌ Failed to add project."
        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        await send_new_message(update, context, f"❌ Error: {e}", reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def top_projects_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status_message = None
    q = update.callback_query
    if q and q.message:
        await q.answer()
        await safe_delete_message(q.message)
        status_message = await send_new_message(update, context, "<i>🔥 Fetching tracked projects...</i>")
    elif update.message:
        status_message = await update.message.reply_text("<i>🔥 Fetching tracked projects...</i>", parse_mode=ParseMode.HTML)
    else:
        return

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/track-requests", timeout=30.0)
        resp.raise_for_status()
        projects = resp.json()

        if not projects:
            reply = "😕 No projects are being tracked yet."
        else:
            parts = [f"<b>🔥 Tracked Projects ({len(projects)})</b>\n"]
            for i, proj in enumerate(projects, 1):
                name = proj.get("project_name", "Unknown")
                parts.append(f"{i}. <code>{name}</code>")
            reply = "\n".join(parts)

        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except httpx.HTTPStatusError as e:
        await send_new_message(update, context, f"❌ Server error ({e.response.status_code}).", reply_markup=get_main_menu_keyboard())
    except Exception as e:
        await send_new_message(update, context, f"❌ Error: {e}", reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status_message = None
    q = update.callback_query
    if q and q.message:
        await q.answer()
        await safe_delete_message(q.message)
        status_message = await send_new_message(update, context, "<i>📊 Fetching statistics...</i>")
    elif update.message:
        status_message = await update.message.reply_text("<i>📊 Fetching statistics...</i>", parse_mode=ParseMode.HTML)
    else:
        return

    try:
        async with httpx.AsyncClient() as client:
            tweets_r = await client.get(f"{API_BASE_URL}/tweets", timeout=30.0)
            sentiment_r = await client.get(f"{API_BASE_URL}/sentiment", timeout=30.0)
            pnl_r = await client.get(f"{API_BASE_URL}/pnl-cards", timeout=30.0)
            projects_r = await client.get(f"{API_BASE_URL}/track-requests", timeout=30.0)

        tweets_count = len(tweets_r.json()) if tweets_r.status_code == 200 else 0
        sentiment_count = len(sentiment_r.json()) if sentiment_r.status_code == 200 else 0
        pnl_count = len(pnl_r.json()) if pnl_r.status_code == 200 else 0
        projects_count = len(projects_r.json()) if projects_r.status_code == 200 else 0

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
        await send_new_message(update, context, f"❌ Error while fetching statistics: {e}", reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)


async def tweets_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        if update.message:
            await update.message.reply_text(
                "❓ Provide a project name.\n<b>Usage:</b> <code>/tweets solana</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    project_tag = context.args[0].lower()
    status_message = None
    if update.message:
        status_message = await update.message.reply_text(
            f"<i>🐦 Fetching tweets for {project_tag}...</i>", parse_mode=ParseMode.HTML
        )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE_URL}/tweets/{project_tag}", timeout=30.0)
        resp.raise_for_status()
        tweets = resp.json()

        if not tweets:
            reply = f"📭 No tweets found for <b>{project_tag.upper()}</b>."
        else:
            parts = [f"<b>🐦 Recent Tweets for {project_tag.upper()}</b>\n"]
            for i, t in enumerate(tweets[:5], 1):
                author = t.get("author_username", "Unknown")
                text = (t.get("tweet_text", "") or "")[:100]
                parts.append(f"{i}. <b>@{author}</b>\n{text}...\n")
            if len(tweets) > 5:
                parts.append(f"<i>...and {len(tweets) - 5} more</i>")
            reply = "\n".join(parts)

        await send_new_message(update, context, reply, reply_markup=get_main_menu_keyboard())
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            await send_new_message(update, context, f"⚠️ No tweets for <b>{project_tag.upper()}</b>.", reply_markup=get_main_menu_keyboard())
        else:
            await send_new_message(update, context, f"❌ Server error ({e.response.status_code}).", reply_markup=get_main_menu_keyboard())
    except Exception as e:
        await send_new_message(update, context, f"❌ Error: {e}", reply_markup=get_main_menu_keyboard())
    finally:
        if status_message:
            await safe_delete_message(status_message)

# --- App bootstrap ---
def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    print("✅ DugTrio Bot is online...")

    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("sentiment", sentiment_command))
    application.add_handler(CommandHandler("track", track_command))
    application.add_handler(CommandHandler("tweets", tweets_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # Menus
    application.add_handler(CallbackQueryHandler(start_command, pattern=r"^menu_start$"))
    application.add_handler(CallbackQueryHandler(sentiment_menu, pattern=r"^menu_sentiment$"))
    application.add_handler(CallbackQueryHandler(analyze_pnl_prompt, pattern=r"^menu_analyze_pnl$"))
    application.add_handler(CallbackQueryHandler(track_project_prompt, pattern=r"^menu_track_project$"))
    application.add_handler(CallbackQueryHandler(top_projects_command, pattern=r"^menu_topprojects$"))
    application.add_handler(CallbackQueryHandler(stats_command, pattern=r"^menu_stats$"))

    # Sentiment quick buttons
    application.add_handler(CallbackQueryHandler(sentiment_command, pattern=r"^sentiment_"))

    application.run_polling()


if __name__ == "__main__":
    main()
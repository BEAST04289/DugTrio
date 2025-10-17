import os
import logging
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from io import BytesIO
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = "http://127.0.0.1:8000/api"

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome to the DugTrio Bot! 🚀\n\n"
        "I can provide you with sentiment analysis for Solana projects. "
        "Here are some commands you can use:\n\n"
        "/sentiment <project_name> - Get the current sentiment score for a project.\n"
        "/history <project_name> - Get the 7-day sentiment history for a project.\n"
        "/trending - Get the top 10 trending projects.\n"
        "/request <project_name> - Request a new project to be tracked.\n"
        "/new_pools - Get the latest liquidity pools on Solana.\n"
        "/top_projects - Get the top 10 projects based on sentiment and trend scores.\n"
        "/calendar - Get upcoming crypto events.\n"
        "/pnl - Reply to an image to analyze the PNL."
    )

async def sentiment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the sentiment score for a given project."""
    project_name = ' '.join(context.args)
    if not project_name:
        await update.message.reply_text("Please provide a project name. Usage: /sentiment <project_name>")
        return

    sent_message = await update.message.reply_text("Digging for sentiment...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/project/{project_name}")
            response.raise_for_status()
            data = response.json()

            message = (
                f"Sentiment for {data['project_name']}:\n"
                f"Score: {data['sentiment_score']}\n"
                f"Analyzed Tweets: {data['analyzed_tweet_count']}"
            )

            if 'top_tweet' in data and data['top_tweet']:
                top_tweet = data['top_tweet']
                message += f"\n\nTop Tweet by {top_tweet['author']}:\n{top_tweet['text']}"
                if 'media_url' in top_tweet and top_tweet['media_url']:
                    await update.message.reply_photo(top_tweet['media_url'])

            await sent_message.edit_text(message)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await sent_message.edit_text(f"No data found for project: {project_name}")
            else:
                await sent_message.edit_text(f"An error occurred: {e}")
        except httpx.RequestError as e:
            await sent_message.edit_text(f"Could not connect to the API: {e}")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the 7-day sentiment history for a given project."""
    project_name = ' '.join(context.args)
    if not project_name:
        await update.message.reply_text("Please provide a project name. Usage: /history <project_name>")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/history/{project_name}")
            response.raise_for_status()
            data = response.json()
            message = f"7-Day Sentiment History for {project_name}:\n\n"
            for item in data:
                message += f"Date: {item['date']}, Score: {item['score']}\n"
            await update.message.reply_text(message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await update.message.reply_text(f"No historical data found for project: {project_name}")
            else:
                await update.message.reply_text(f"An error occurred: {e}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to the API: {e}")

async def trending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the top 10 trending projects."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/trending")
            response.raise_for_status()
            data = response.json()
            message = "Top 10 Trending Projects:\n\n"
            for item in data:
                message += f"Project: {item['project_name']}, Score: {item['trend_score']:.2f}\n"
            await update.message.reply_text(message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await update.message.reply_text("No trending projects found at the moment.")
            else:
                await update.message.reply_text(f"An error occurred: {e}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to the API: {e}")

async def request_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Requests a new project to be tracked."""
    project_name = ' '.join(context.args)
    if not project_name:
        await update.message.reply_text("Please provide a project name. Usage: /request <project_name>")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{API_BASE_URL}/request", json={"project_name": project_name})
            response.raise_for_status()
            data = response.json()
            await update.message.reply_text(data['message'])
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                await update.message.reply_text(f"Project '{project_name}' has already been requested.")
            else:
                await update.message.reply_text(f"An error occurred: {e}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to the API: {e}")

async def new_pools(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the latest liquidity pools on Solana."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/new_pools")
            response.raise_for_status()
            data = response.json()
            message = "Newest Liquidity Pools on Solana:\n\n"
            for pool in data:
                message += f"Pair: {pool['baseToken']['symbol']}/{pool['quoteToken']['symbol']}\n"
                message += f"Address: {pool['pairAddress']}\n"
                message += f"Created At: {datetime.fromtimestamp(pool['pairCreatedAt'] / 1000)}\n\n"
            await update.message.reply_text(message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await update.message.reply_text("No new pools found at the moment.")
            else:
                await update.message.reply_text(f"An error occurred: {e}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to the API: {e}")

async def top_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays the top 10 projects."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/top_projects")
            response.raise_for_status()
            data = response.json()
            message = "Top 10 Projects:\n\n"
            for project in data:
                message += f"Project: {project['project_name']}, Score: {project['score']:.2f}\n"
            await update.message.reply_text(message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await update.message.reply_text("No top projects found at the moment.")
            else:
                await update.message.reply_text(f"An error occurred: {e}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to the API: {e}")

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetches and displays upcoming crypto events."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/calendar")
            response.raise_for_status()
            data = response.json()
            message = "Upcoming Crypto Events:\n\n"
            for event in data.get('body', []):
                message += f"**{event.get('title', 'N/A')}**\n"
                message += f"Date: {event.get('date_event', 'N/A')}\n"
                message += f"Coins: {', '.join([coin.get('name', 'N/A') for coin in event.get('coins', [])])}\n\n"
            await update.message.reply_text(message)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                await update.message.reply_text("No upcoming events found.")
            else:
                await update.message.reply_text(f"An error occurred: {e}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to the API: {e}")

async def pnl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyzes a PNL screenshot."""
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Please reply to an image with the /pnl command.")
        return

    photo = update.message.reply_to_message.photo[-1]
    file = await photo.get_file()

    async with httpx.AsyncClient() as client:
        try:
            file_content = await file.download_as_bytearray()
            files = {'file': ('image.png', file_content, 'image/png')}
            response = await client.post(f"{API_BASE_URL}/pnl/analyze", files=files)
            response.raise_for_status()
            data = response.json()

            message = "PNL Analysis:\n\n"
            for key, value in data.items():
                message += f"{key.replace('_', ' ').title()}: {value}\n"
            await update.message.reply_text(message)

        except httpx.HTTPStatusError as e:
            await update.message.reply_text(f"An error occurred during analysis: {e}")
        except httpx.RequestError as e:
            await update.message.reply_text(f"Could not connect to the API: {e}")

def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("sentiment", sentiment))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("trending", trending))
    application.add_handler(CommandHandler("request", request_project))
    application.add_handler(CommandHandler("new_pools", new_pools))
    application.add_handler(CommandHandler("top_projects", top_projects))
    application.add_handler(CommandHandler("calendar", calendar))
    application.add_handler(CommandHandler("pnl", pnl))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
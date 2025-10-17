import asyncio
import logging
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import and_, func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from database import get_db
from models import Tweet, TrackRequest, PnlCard
from typing import Dict, Any, List

from database import get_db, SessionLocal
from models import Tweet, TrackRequest, PnlCard, TrendingProject
import requests
from PIL import Image
from io import BytesIO
import re
import pytesseract

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Pydantic Models for Request Body Validation ---
class NewTrackRequest(BaseModel):
    project_name: str

# --- FastAPI Application Instance ---
app = FastAPI(
    title="DugTrio API",
    description="API for serving social sentiment analysis for Solana projects.",
    version="0.1.0"
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Endpoints ---
@app.get("/api/project/{project_name}")
def get_project_data(project_name: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieves the latest analyzed data for a specific project.
    Uses corrected three-label sentiment mapping (0=Neg, 1=Neu, 2=Pos).
    """
    try:
        # Query the database for the 50 most recent, analyzed tweets
        # Pylance reports an "Invalid conditional operand" error here, but the SQLAlchemy logic is correct.
        tweets: List[Tweet] = db.query(Tweet)\
            .filter(Tweet.project_tag == project_name, Tweet.sentiment_label != None)\
            .order_by(Tweet.created_at.desc())\
            .limit(50)\
            .all()

        if not tweets:
            raise HTTPException(status_code=404, detail="No analyzed data found for this project.")

        # --- Correctly calculate Positive Tweets (LABEL_2) ---
        POSITIVE_LABEL = 'LABEL_2'
        
        # The list comprehension safely filters the list retrieved from the DB
        # Use getattr to avoid static type-checker confusion about SQLAlchemy Column types
        positive_tweets = [t for t in tweets if getattr(t, "sentiment_label", None) == POSITIVE_LABEL]
        
        total_analyzed = len(tweets) 
        
        sentiment_score = (len(positive_tweets) / total_analyzed) * 100 if total_analyzed > 0 else 0
        # --- END OF FIX ---

        # Prepare the list of tweets for the JSON response
        tweet_data = [{
            "text": t.text,
            "author": t.author_username,
            "sentiment": t.sentiment_label,
            "score": t.sentiment_score
        } for t in tweets]
        
        # Return the final JSON response
        return {
            "project_name": project_name,
            "sentiment_score": round(sentiment_score, 2),
            "analyzed_tweet_count": total_analyzed,
            "tweets": tweet_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))

@app.post("/api/request")
def request_new_project(request: NewTrackRequest, db: Session = Depends(get_db)):
    """
    Endpoint for users to request a new project to be tracked.
    Prevents duplicate project entries.
    """
    try:
        # Create a new TrackRequest object
        new_request = TrackRequest(project_name=request.project_name)

        # Add it to the session and commit
        db.add(new_request)
        db.commit()

        return {"status": "success", "message": f"Project '{request.project_name}' has been successfully requested for tracking."}

    except IntegrityError:
        # This happens if the project_name is not unique
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Project '{request.project_name}' has already been requested.")

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))


@app.get("/api/history/{project_tag}")
def get_project_history(project_tag: str, db: Session = Depends(get_db)):
    """
    Retrieves the daily average sentiment score for the last 7 days for a specific project.
    """
    try:
        # Define the time window for the query
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # Define the case for positive sentiment
        positive_sentiment = case((Tweet.sentiment_label == 'LABEL_2', 1), else_=0)

        # Query the database to get daily sentiment scores
        results = db.query(
            func.date(Tweet.created_at).label('date'),
            (func.sum(positive_sentiment) * 100.0 / func.count(Tweet.id)).label('score')
        ).filter(
            and_(
                Tweet.project_tag == project_tag,
                Tweet.created_at >= seven_days_ago
            )
        ).group_by(
            func.date(Tweet.created_at)
        ).order_by(
            func.date(Tweet.created_at)
        ).all()

        if not results:
            raise HTTPException(status_code=404, detail="No historical data found for this project in the last 7 days.")

        # Format the results for the response
        history_data = [{"date": res.date.isoformat(), "score": round(res.score, 2)} for res in results]

        return history_data

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))


# --- Analysis Logic ---

def download_image(url: str) -> Optional[Image.Image]:
    """Downloads an image from a URL and returns a PIL Image object."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading image from {url}: {e}")
        return None

def extract_text_from_image(image: Image.Image) -> str:
    """Extracts text from a PIL Image object using Tesseract OCR."""
    try:
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError:
        logging.error("Tesseract is not installed or not in your PATH.")
        return ""
    except Exception as e:
        logging.error(f"Error during OCR extraction: {e}")
        return ""

def parse_pnl_data(text: str) -> dict:
    """
    Parses extracted text to find PNL-related data using a series of regular expressions.
    This is a more robust implementation to handle various PNL card formats.
    """
    data = {
        "entry_price": None,
        "exit_price": None,
        "pnl_percentage": None,
        "token_symbol": None,
    }

    # Normalize text for easier parsing
    text = text.lower()

    # --- PNL Percentage Extraction ---
    # Look for patterns like "+123.45%", "-50.2%", "PNL: 30%", etc.
    pnl_match = re.search(r'(pnl|profit|loss)\s*:?\s*([\+\-]?\s*\d+(\.\d+)?)\s*%', text)
    if not pnl_match:
        pnl_match = re.search(r'([\+\-]\s*\d+(\.\d+)?)\s*%', text)
    if pnl_match:
        # Extract the numeric part, removing whitespace and the '+' sign
        pnl_value = pnl_match.group(1).replace(' ', '').replace('+', '')
        data['pnl_percentage'] = float(pnl_value)

    # --- Token Symbol Extraction ---
    # Look for common crypto patterns, like a 3-5 letter uppercase word, often preceded by '$'
    symbol_match = re.search(r'\$([a-z]{3,5})\b', text)
    if not symbol_match:
        # Fallback: Look for a 3-5 letter uppercase word near "entry" or "exit"
        symbol_match = re.search(r'\b([a-z]{3,5})\b\s*(entry|exit)', text)
    if symbol_match:
        data['token_symbol'] = symbol_match.group(1).upper()

    # --- Entry and Exit Price Extraction ---
    # Look for "entry price: $123.45" or "entry: 0.123"
    entry_match = re.search(r'entry\s*(price)?\s*:?\s*\$?(\d+(\.\d+)?)', text)
    if entry_match:
        data['entry_price'] = float(entry_match.group(2))

    exit_match = re.search(r'exit\s*(price)?\s*:?\s*\$?(\d+(\.\d+)?)', text)
    if exit_match:
        data['exit_price'] = float(exit_match.group(2))

    return data

def analyze_pnl_cards():
    """
    Finds tweets with media URLs that haven't been analyzed for PNL data,
    processes them, and updates the database.
    """
    db: Session = SessionLocal()
    logging.info("--- 📈 Starting PNL Card Analysis ---")

    try:
        # Find tweets with a media_url that don't have a corresponding PnlCard entry yet.
        tweets_to_process: List[Tweet] = db.query(Tweet).filter(
            Tweet.media_url != None,
            Tweet.pnl_card == None
        ).all()

        if not tweets_to_process:
            logging.info("✅ No new PNL cards to analyze.")
            return

        logging.info(f"Found {len(tweets_to_process)} potential PNL cards to analyze...")

        for tweet in tweets_to_process:
            logging.info(f"Processing tweet {tweet.id} with media URL: {tweet.media_url}")

            image = download_image(tweet.media_url)
            if not image:
                # Create a failed PnlCard entry
                pnl_card = PnlCard(tweet_id=tweet.id, analysis_status='download_failed')
                db.add(pnl_card)
                continue

            extracted_text = extract_text_from_image(image)
            if not extracted_text:
                # Create a failed PnlCard entry
                pnl_card = PnlCard(tweet_id=tweet.id, analysis_status='ocr_failed')
                db.add(pnl_card)
                continue

            pnl_data = parse_pnl_data(extracted_text)

            # Create a new PnlCard with the extracted data
            pnl_card = PnlCard(
                tweet_id=tweet.id,
                analysis_status='success',
                extracted_text=extracted_text,
                **pnl_data
            )
            db.add(pnl_card)

        logging.info("Committing all new PNL card data to the database...")
        db.commit()
        logging.info("✅ PNL analysis complete.")

    except Exception as e:
        logging.error(f"❌ An error occurred during the PNL analysis process: {e}")
        db.rollback()
    finally:
        logging.info("Closing database session.")
        db.close()

def calculate_trend_score(current_mentions: int, previous_mentions: int) -> float:
    """Calculates a trend score based on the change in mention volume."""
    # Simple growth rate calculation. Add 1 to avoid division by zero.
    return (current_mentions - previous_mentions) / (previous_mentions + 1)

def analyze_and_update_trends():
    """
    Analyzes tweet volume for tracked projects to identify trends
    and saves the results to the database.
    """
    db: Session = SessionLocal()
    logging.info("--- 📈 Starting Trend Analysis ---")

    try:
        # Define the time windows for analysis (e.g., last 4 hours vs. previous 4 hours)
        now = datetime.utcnow()
        current_window_start = now - timedelta(hours=4)
        previous_window_start = now - timedelta(hours=8)
        previous_window_end = current_window_start

        # Get all projects that are being tracked
        tracked_projects = db.query(TrackRequest.project_name).all()
        project_names = [p.project_name for p in tracked_projects]

        if not project_names:
            logging.warning("No projects are being tracked. Skipping trend analysis.")
            return

        logging.info(f"Analyzing trends for {len(project_names)} projects...")

        trending_results = []

        for name in project_names:
            # Count mentions in the current window
            current_mentions = db.query(func.count(Tweet.id)).filter(
                and_(
                    Tweet.project_tag == name,
                    Tweet.created_at >= current_window_start
                )
            ).scalar() or 0

            # Count mentions in the previous window
            previous_mentions = db.query(func.count(Tweet.id)).filter(
                and_(
                    Tweet.project_tag == name,
                    Tweet.created_at.between(previous_window_start, previous_window_end)
                )
            ).scalar() or 0

            # Calculate the trend score
            score = calculate_trend_score(current_mentions, previous_mentions)

            # We only care about projects that are currently being mentioned
            if current_mentions > 0:
                trending_results.append({
                    "project_name": name,
                    "mention_count": current_mentions,
                    "trend_score": score
                })

        if not trending_results:
            logging.info("No significant trends detected in the last window.")
            return

        # Sort by trend score in descending order
        trending_results.sort(key=lambda x: x['trend_score'], reverse=True)

        # Clear the old trending projects data
        db.query(TrendingProject).delete()

        # Save the new top trending projects to the database
        logging.info("Saving new trending projects to the database...")
        for result in trending_results[:10]: # Save top 10
            new_trend = TrendingProject(**result)
            db.add(new_trend)

        db.commit()
        logging.info("✅ Trend analysis complete. Database has been updated.")

    except Exception as e:
        logging.error(f"❌ An error occurred during the trend analysis process: {e}")
        db.rollback()
    finally:
        logging.info("Closing database session.")
        db.close()


# --- Background Task ---

@app.post("/api/run-analysis")
def run_analysis(background_tasks: BackgroundTasks):
    """
    Triggers a background task to run the PNL and trending analysis.
    """
    background_tasks.add_task(analyze_pnl_cards)
    background_tasks.add_task(analyze_and_update_trends)
    return {"message": "Analysis tasks have been started in the background."}


# --- API Endpoints ---

@app.get("/api/pnl/{project_name}")
def get_pnl_data(project_name: str, db: Session = Depends(get_db)):
    """
    Retrieves all analyzed PNL card data for a specific project.
    """
    try:
        # Query the database for PnlCard entries related to the project
        pnl_cards = db.query(PnlCard).join(Tweet).filter(
            Tweet.project_tag == project_name,
            PnlCard.analysis_status == 'success'
        ).all()

        if not pnl_cards:
            raise HTTPException(status_code=404, detail="No PNL card data found for this project.")

        # Prepare the list of PNL cards for the JSON response
        pnl_data = [{
            "tweet_id": card.tweet_id,
            "entry_price": card.entry_price,
            "exit_price": card.exit_price,
            "pnl_percentage": card.pnl_percentage,
            "token_symbol": card.token_symbol,
            "media_url": card.tweet.media_url,
            "tweet_text": card.tweet.text
        } for card in pnl_cards]

        return {
            "project_name": project_name,
            "pnl_cards": pnl_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))


@app.get("/api/trending")
def get_trending_projects(db: Session = Depends(get_db)):
    """
    Retrieves the list of currently trending projects.
    """
    try:
        trending_projects = db.query(TrendingProject).order_by(TrendingProject.trend_score.desc()).all()

        if not trending_projects:
            raise HTTPException(status_code=404, detail="No trending projects found at the moment.")

        return trending_projects

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Server Error: " + str(e))


@app.get("/")
def read_root():
    return {"status": "DugTrio API is running"}
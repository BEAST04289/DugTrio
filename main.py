from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from sqlalchemy import and_, func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
import logging
import re
import pytesseract
import requests
from typing import Dict, Any, List, Optional

from database import get_db, SessionLocal
from models import Tweet, TrackRequest, PnlCard, TrendingProject
from PIL import Image
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Pydantic Models for Request Body Validation ---
class NewTrackRequest(BaseModel):
    project_name: str

    @validator('project_name')
    def validate_project_name(cls, v):
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError('Project name must be between 1 and 100 characters')
        return v

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
        # Count the number of tweets mentioning the project in the past 24 hours
        past_24h = datetime.utcnow() - timedelta(hours=24)
        total_mentions = db.query(Tweet).filter(
            Tweet.project_tag == project_name,
            Tweet.created_at >= past_24h
        ).count()

        if total_mentions == 0:
            raise HTTPException(status_code=404, detail="No recent data found for this project.")

        # Calculate the average sentiment score for the past 24 hours
        avg_sentiment = db.query(func.avg(Tweet.sentiment_score)).filter(
            Tweet.project_tag == project_name,
            Tweet.created_at >= past_24h,
            Tweet.sentiment_score != None
        ).scalar()

        # Count tweets by sentiment label
        sentiment_counts = db.query(
            Tweet.sentiment_label,
            func.count(Tweet.id)
        ).filter(
            Tweet.project_tag == project_name,
            Tweet.created_at >= past_24h,
            Tweet.sentiment_label != None
        ).group_by(Tweet.sentiment_label).all()

        sentiment_breakdown = {label: count for label, count in sentiment_counts}

        return {
            "project_name": project_name,
            "total_mentions": total_mentions,
            "average_sentiment_score": round(avg_sentiment, 2) if avg_sentiment else None,
            "sentiment_breakdown": sentiment_breakdown
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_project_data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/request")
def request_new_project(request: NewTrackRequest, db: Session = Depends(get_db)):
    """
    Endpoint for users to request a new project to be tracked.
    Prevents duplicate project entries.
    """
    try:
        project_name = request.project_name
        
        new_request = TrackRequest(project_name=project_name)
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        return {
            "message": f"Project '{project_name}' has been added to the tracking queue.",
            "request_id": new_request.id
        }

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="This project is already being tracked.")

    except Exception as e:
        db.rollback()
        logging.error(f"Error in request_new_project: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/history/{project_tag}")
def get_project_history(project_tag: str, db: Session = Depends(get_db)):
    """
    Retrieves the daily average sentiment score for the last 7 days for a specific project.
    """
    try:
        past_7_days = datetime.utcnow() - timedelta(days=7)
        
        # Query for daily average sentiment
        daily_data = db.query(
            func.date(Tweet.created_at).label('date'),
            func.avg(Tweet.sentiment_score).label('avg_sentiment'),
            func.count(Tweet.id).label('mention_count')
        ).filter(
            Tweet.project_tag == project_tag,
            Tweet.created_at >= past_7_days,
            Tweet.sentiment_score != None
        ).group_by(func.date(Tweet.created_at)).all()

        if not daily_data:
            raise HTTPException(status_code=404, detail="No historical data found for this project.")

        history = [
            {
                "date": str(row.date),
                "average_sentiment": round(row.avg_sentiment, 2),
                "mentions": row.mention_count
            }
            for row in daily_data
        ]

        return {
            "project_tag": project_tag,
            "history": history
        }

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in get_project_history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# --- Analysis Logic ---

def download_image(url: str) -> Optional[Image.Image]:
    """Downloads an image from a URL and returns a PIL Image object."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading image from {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error opening image: {e}")
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
    data: Dict[str, Optional[float | str]] = {
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
    if pnl_match:
        try:
            # Extract group 2 (the numeric part after the label)
            pnl_value = pnl_match.group(2).replace(' ', '').replace('+', '')
            data['pnl_percentage'] = float(pnl_value)
        except (ValueError, AttributeError) as e:
            logging.warning(f"Failed to parse PNL percentage from first match: {e}")
    
    if data['pnl_percentage'] is None:
        # Fallback: Look for standalone percentage
        pnl_match = re.search(r'([\+\-]\s*\d+(\.\d+)?)\s*%', text)
        if pnl_match:
            try:
                pnl_value = pnl_match.group(1).replace(' ', '').replace('+', '')
                data['pnl_percentage'] = float(pnl_value)
            except (ValueError, AttributeError) as e:
                logging.warning(f"Failed to parse PNL percentage from fallback match: {e}")

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
        try:
            data['entry_price'] = float(entry_match.group(2))
        except (ValueError, AttributeError) as e:
            logging.warning(f"Failed to parse entry price: {e}")

    exit_match = re.search(r'exit\s*(price)?\s*:?\s*\$?(\d+(\.\d+)?)', text)
    if exit_match:
        try:
            data['exit_price'] = float(exit_match.group(2))
        except (ValueError, AttributeError) as e:
            logging.warning(f"Failed to parse exit price: {e}")

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
        tweets_to_analyze: List[Tweet] = db.query(Tweet).filter(
            Tweet.media_url != None,
            Tweet.pnl_card == None
        ).all()

        if not tweets_to_analyze:
            logging.info("✅ No new PNL cards to analyze.")
            return

        logging.info(f"Found {len(tweets_to_analyze)} potential PNL cards to analyze...")

        for tweet in tweets_to_analyze:
            logging.info(f"Processing tweet {tweet.id} with media URL: {tweet.media_url}")

            # No need to cast, already filtered by media_url != None
            image = download_image(tweet.media_url.scalar()) if tweet.media_url is not None else None
            media_url_value = tweet.media_url if isinstance(tweet.media_url, str) else tweet.media_url.scalar()
            image = download_image(media_url_value) if media_url_value is not None else None
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
        now = datetime.utcnow()
        past_24h = now - timedelta(hours=24)
        past_48h = now - timedelta(hours=48)

        # Query for current and previous mention counts
        projects = db.query(TrackRequest).all()
        trending_results = []

        for project in projects:
            current_count = db.query(Tweet).filter(
                Tweet.project_tag == project.project_name,
                Tweet.created_at >= past_24h
            ).count()

            previous_count = db.query(Tweet).filter(
                Tweet.project_tag == project.project_name,
                Tweet.created_at >= past_48h,
                Tweet.created_at < past_24h
            ).count()

            trend_score = calculate_trend_score(current_count, previous_count)

            trending_results.append({
                "project_name": project.project_name,
                "mention_count": current_count,
                "trend_score": trend_score
            })

        # Sort by trend score
        trending_results.sort(key=lambda x: x['trend_score'], reverse=True)

        # Clear old trending data
        db.query(TrendingProject).delete()

        # Save the new top trending projects to the database
        logging.info("Saving new trending projects to the database...")
        for result in trending_results[:10]:
            new_trend = TrendingProject(
                **result,
                created_at=now
            )
            db.add(new_trend)

        db.commit()
        logging.info("✅ Trend analysis complete.")

    except Exception as e:
        logging.error(f"❌ An error occurred during trend analysis: {e}")
        db.rollback()
    finally:
        logging.info("Closing database session.")
        db.close()


# --- Background Task ---

@app.post("/api/run-analysis")
def run_analysis(background_tasks: BackgroundTasks):
    """Triggers background analysis tasks."""
    background_tasks.add_task(analyze_pnl_cards)
    background_tasks.add_task(analyze_and_update_trends)
    return {"message": "Analysis tasks started in the background"}


# --- API Endpoints ---

@app.get("/api/pnl/{project_name}")
def get_pnl_data(project_name: str, db: Session = Depends(get_db)):
    """Retrieves PNL card data for a specific project."""
    pnl_cards = db.query(PnlCard).join(Tweet).filter(
        Tweet.project_tag == project_name,
        PnlCard.analysis_status == 'success'
    ).all()
    
    return {"project_name": project_name, "pnl_cards": pnl_cards}


@app.get("/api/trending")
def get_trending_projects(db: Session = Depends(get_db)):
    """Retrieves the current trending projects."""
    trending = db.query(TrendingProject).order_by(
        TrendingProject.trend_score.desc()
    ).limit(10).all()
    
    return {"trending_projects": trending}


@app.get("/")
def read_root():
    return {"message": "Welcome to DugTrio API"}
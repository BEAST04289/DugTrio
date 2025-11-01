from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import logging
import re
import pytesseract
import requests
from PIL import Image
from io import BytesIO

from database import get_db, SessionLocal
from models import Tweet, TrackRequest, PnlCard, TrendingProject

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dugtrio.api")

# --- Helpers ---
def model_to_dict(obj) -> Dict[str, Any]:
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        return obj.to_dict()
    try:
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}  # type: ignore[attr-defined]
    except Exception:
        # Last resort; may still fail for relationships/non-serializable fields
        return {k: v for k, v in vars(obj).items() if not k.startswith("_")}

# --- Pydantic Models for Request Body Validation ---
class NewTrackRequest(BaseModel):
    project_name: str

    @validator('project_name')
    def validate_project_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError('Project name must be between 1 and 100 characters')
        return v

# --- FastAPI Application Instance ---
app = FastAPI(
    title="DugTrio API",
    description="API for serving social sentiment analysis for Solana projects.",
    version="0.1.0",
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
    Assumes sentiment_label mapping 0=Neg, 1=Neu, 2=Pos.
    """
    try:
        past_24h = datetime.utcnow() - timedelta(hours=24)

        total_mentions = db.query(Tweet).filter(
            Tweet.project_tag == project_name,
            Tweet.created_at >= past_24h,
        ).count()

        if total_mentions == 0:
            raise HTTPException(status_code=404, detail="No recent data found for this project.")

        avg_sentiment = db.query(func.avg(Tweet.sentiment_score)).filter(
            Tweet.project_tag == project_name,
            Tweet.created_at >= past_24h,
            Tweet.sentiment_score != None,  # noqa: E711
        ).scalar()

        sentiment_counts = db.query(
            Tweet.sentiment_label,
            func.count(Tweet.id),
        ).filter(
            Tweet.project_tag == project_name,
            Tweet.created_at >= past_24h,
            Tweet.sentiment_label != None,  # noqa: E711
        ).group_by(Tweet.sentiment_label).all()

        sentiment_breakdown = {int(label): count for label, count in sentiment_counts if label is not None}

        return {
            "project_name": project_name,
            "total_mentions": total_mentions,
            "average_sentiment_score": round(avg_sentiment, 2) if avg_sentiment is not None else None,
            "sentiment_breakdown": sentiment_breakdown,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_project_data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/request")
def request_new_project(request: NewTrackRequest, db: Session = Depends(get_db)):
    """
    Endpoint for users to request a new project to be tracked.
    Prevents duplicate project entries (relies on DB unique constraint).
    """
    try:
        project_name = request.project_name
        new_request = TrackRequest(project_name=project_name)
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return {"message": f"Project '{project_name}' has been added to the tracking queue.", "request_id": new_request.id}
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="This project is already being tracked.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error in request_new_project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/history/{project_tag}")
def get_project_history(project_tag: str, db: Session = Depends(get_db)):
    """
    Retrieves the daily average sentiment score for the last 7 days for a specific project.
    """
    try:
        past_7_days = datetime.utcnow() - timedelta(days=7)
        daily_data = db.query(
            func.date(Tweet.created_at).label('date'),
            func.avg(Tweet.sentiment_score).label('avg_sentiment'),
            func.count(Tweet.id).label('mention_count'),
        ).filter(
            Tweet.project_tag == project_tag,
            Tweet.created_at >= past_7_days,
            Tweet.sentiment_score != None,  # noqa: E711
        ).group_by(func.date(Tweet.created_at)).all()

        if not daily_data:
            raise HTTPException(status_code=404, detail="No historical data found for this project.")

        history = [
            {"date": str(row.date), "average_sentiment": round(row.avg_sentiment, 2), "mentions": row.mention_count}
            for row in daily_data
        ]

        return {"project_tag": project_tag, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_project_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# --- Analysis Logic ---
def download_image(url: str) -> Optional[Image.Image]:
    """Downloads an image from a URL and returns a PIL Image object."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading image from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error opening image: {e}")
        return None

def extract_text_from_image(image: Image.Image) -> str:
    """Extracts text from a PIL Image object using Tesseract OCR."""
    try:
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract is not installed or not in PATH.")
        return ""
    except Exception as e:
        logger.error(f"Error during OCR extraction: {e}")
        return ""

def parse_pnl_data(text: str) -> dict:
    """
    Parses extracted text to find PNL-related data using several regex patterns.
    """
    data: Dict[str, Optional[float | str]] = {
        "entry_price": None,
        "exit_price": None,
        "pnl_percentage": None,
        "token_symbol": None,
    }

    t = text.lower()

    # PNL %
    m = re.search(r'(pnl|profit|loss)\s*:?\s*([\+\-]?\s*\d+(\.\d+)?)\s*%', t)
    if m:
        try:
            val = m.group(2).replace(' ', '').replace('+', '')
            data['pnl_percentage'] = float(val)
        except Exception:
            pass
    if data['pnl_percentage'] is None:
        m = re.search(r'([\+\-]\s*\d+(\.\d+)?)\s*%', t)
        if m:
            try:
                val = m.group(1).replace(' ', '').replace('+', '')
                data['pnl_percentage'] = float(val)
            except Exception:
                pass

    # Token symbol
    sm = re.search(r'\$([a-z]{3,5})\b', t)
    if not sm:
        sm = re.search(r'\b([a-z]{3,5})\b\s*(entry|exit)', t)
    if sm:
        data['token_symbol'] = sm.group(1).upper()

    # Entry/Exit
    em = re.search(r'entry\s*(price)?\s*:?\s*\$?(\d+(\.\d+)?)', t)
    if em:
        try:
            data['entry_price'] = float(em.group(2))
        except Exception:
            pass

    xm = re.search(r'exit\s*(price)?\s*:?\s*\$?(\d+(\.\d+)?)', t)
    if xm:
        try:
            data['exit_price'] = float(xm.group(2))
        except Exception:
            pass

    return data

def analyze_pnl_cards():
    """
    Finds tweets with media URLs that haven't been analyzed for PNL data,
    processes them, and updates the database.
    """
    db: Session = SessionLocal()
    logger.info("--- Starting PNL Card Analysis ---")

    try:
        tweets_to_analyze: List[Tweet] = db.query(Tweet).filter(
            Tweet.media_url != None,      # noqa: E711
            Tweet.pnl_card == None        # noqa: E711 (assuming relationship present)
        ).all()

        if not tweets_to_analyze:
            logger.info("No new PNL cards to analyze.")
            return

        logger.info(f"Found {len(tweets_to_analyze)} potential PNL cards to analyze...")

        for tweet in tweets_to_analyze:
            media_url_value: Optional[str] = None
            try:
                # Handle str or instrumented attribute gracefully
                media_url_value = str(tweet.media_url) if tweet.media_url is not None else None
            except Exception:
                media_url_value = None

            image = download_image(media_url_value) if media_url_value else None
            if not image:
                db.add(PnlCard(tweet_id=tweet.id, analysis_status='download_failed'))
                continue

            extracted_text = extract_text_from_image(image)
            if not extracted_text:
                db.add(PnlCard(tweet_id=tweet.id, analysis_status='ocr_failed'))
                continue

            pnl_data = parse_pnl_data(extracted_text)
            db.add(PnlCard(
                tweet_id=tweet.id,
                analysis_status='success',
                extracted_text=extracted_text,
                **pnl_data
            ))

        logger.info("Committing new PNL card data to the database...")
        db.commit()
        logger.info("PNL analysis complete.")
    except Exception as e:
        logger.error(f"Error during PNL analysis: {e}", exc_info=True)
        db.rollback()
    finally:
        logger.info("Closing database session.")
        db.close()

def calculate_trend_score(current_mentions: int, previous_mentions: int) -> float:
    """Calculates a trend score based on the change in mention volume."""
    return (current_mentions - previous_mentions) / (previous_mentions + 1)

def analyze_and_update_trends():
    """
    Analyzes tweet volume for tracked projects to identify trends
    and saves the results to the database.
    """
    db: Session = SessionLocal()
    logger.info("--- Starting Trend Analysis ---")

    try:
        now = datetime.utcnow()
        past_24h = now - timedelta(hours=24)
        past_48h = now - timedelta(hours=48)

        projects = db.query(TrackRequest).all()
        trending_results: List[Dict[str, Any]] = []

        for project in projects:
            name = project.project_name

            current_count = db.query(Tweet).filter(
                Tweet.project_tag == name,
                Tweet.created_at >= past_24h
            ).count()

            previous_count = db.query(Tweet).filter(
                Tweet.project_tag == name,
                Tweet.created_at >= past_48h,
                Tweet.created_at < past_24h
            ).count()

            trending_results.append({
                "project_name": name,
                "mention_count": current_count,
                "trend_score": calculate_trend_score(current_count, previous_count),
            })

        trending_results.sort(key=lambda x: x["trend_score"], reverse=True)

        # Replace old trending data with new top 10
        db.query(TrendingProject).delete()
        for result in trending_results[:10]:
            db.add(TrendingProject(**result, created_at=now))

        db.commit()
        logger.info("Trend analysis complete.")
    except Exception as e:
        logger.error(f"Error during trend analysis: {e}", exc_info=True)
        db.rollback()
    finally:
        logger.info("Closing database session.")
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
    return {
        "project_name": project_name,
        "pnl_cards": [model_to_dict(pc) for pc in pnl_cards],
    }

@app.get("/api/trending")
def get_trending_projects(db: Session = Depends(get_db)):
    trending = db.query(TrendingProject).order_by(
        TrendingProject.trend_score.desc()
    ).limit(5).all()
    return [model_to_dict(t) for t in trending]

@app.get("/")
def read_root():
    return {"message": "Welcome to DugTrio API"}
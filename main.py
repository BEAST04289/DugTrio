from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import and_, func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta

from database import get_db
from models import Tweet, TrackRequest, PnlCard
from typing import Dict, Any, List

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


@app.get("/")
def read_root():
    return {"status": "DugTrio API is running"}
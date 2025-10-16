from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db 
from models import Tweet      
from typing import Dict, Any, List

# Create the main FastAPI application instance
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
        positive_tweets = [t for t in tweets if t.sentiment_label == POSITIVE_LABEL]
        
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

@app.get("/")
def read_root():
    return {"status": "DugTrio API is running"}
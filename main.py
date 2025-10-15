from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Import components from our project files
from database import get_db
from models import Tweet

# Create the main FastAPI application instance
app = FastAPI(
    title="DugTrio API",
    description="API for serving social sentiment analysis for Solana projects.",
    version="0.1.0"
)

# --- Middleware ---
# This allows our future frontend (on a different domain) to make requests to this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)


# --- API Endpoints ---
@app.get("/api/project/{project_name}")
def get_project_data(project_name: str, db: Session = Depends(get_db)):
    """
    Retrieves the latest analyzed data for a specific project.
    """
    try:
        # Query the database for the 50 most recent, already-analyzed tweets for the project
        tweets = db.query(Tweet)\
            .filter(Tweet.project_tag == project_name, Tweet.sentiment_label != None)\
            .order_by(Tweet.created_at.desc())\
            .limit(50)\
            .all()

        if not tweets:
            raise HTTPException(status_code=404, detail="No analyzed data found for this project.")

        # Calculate the overall sentiment score
        positive_tweets = [t for t in tweets if t.sentiment_label == 'Positive']
        total_analyzed = len(tweets)
        sentiment_score = (len(positive_tweets) / total_analyzed) * 100 if total_analyzed > 0 else 0

        # Prepare the list of tweets for the response
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
        # If any other error occurs, return a server error
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"status": "DugTrio API is running"}
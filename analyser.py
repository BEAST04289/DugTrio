import logging
from transformers import pipeline
from sqlalchemy.orm import Session
from typing import List, Optional, cast, Any # Add Optional for better type hinting

from database import SessionLocal
from models import Tweet, Column # Ensure Column is available for type analysis

# Configure logging
logging.basicConfig(level=logging.INFO)

def analyze_and_update_sentiment():
    """
    Finds tweets without sentiment, analyzes them using an AI model,
    and updates the database with the results.
    """
    db: Session = SessionLocal()
    
    logging.info("--- 🧠 Starting Sentiment Analysis ---")

    try:
        # FIX 1: Explicitly define the 'task' argument to resolve Pylance warning
        logging.info("Loading sentiment analysis model...")
        sentiment_pipeline = cast(Any, pipeline)(
            task="sentiment-analysis", 
            model="cardiffnlp/twitter-roberta-base-sentiment"
        )
        logging.info("🤖 Model loaded successfully.")

        # Step 1: Find all tweets that haven't been analyzed yet
        tweets_to_analyze: List[Tweet] = db.query(Tweet).filter(Tweet.sentiment_label == None).all()

        if not tweets_to_analyze:
            logging.info("✅ No new tweets to analyze. Database is up to date.")
            return

        logging.info(f"Found {len(tweets_to_analyze)} tweets to analyze...")

        # Step 2: Analyze each tweet and update the object
        logging.info("Analyzing tweets...")
        for i, tweet in enumerate(tweets_to_analyze):
            try:
                text_to_analyze = tweet.text
                result = sentiment_pipeline(text_to_analyze)[0]
                
                # Update the tweet object
                tweet.sentiment_label = result['label']
                tweet.sentiment_score = result['score']

                if (i + 1) % 10 == 0:
                    logging.info(f"   ...analyzed {i + 1}/{len(tweets_to_analyze)} tweets")

            except Exception as e:
                logging.error(f"Could not analyze tweet ID {tweet.id}: {e}")
                # FIX 2: Assignment is fine here, but we ensure the code structure is clean
                setattr(tweet, 'sentiment_label', 'Error')
        
        # Step 3: Commit all the changes to the database in one go
        logging.info("Saving all new sentiment data to the database...")
        db.commit()
        logging.info("✅ Analysis complete. Database has been updated.")

    except Exception as e:
        logging.error(f"❌ An error occurred during the analysis process: {e}")
        db.rollback()
    finally:
        logging.info("Closing database session.")
        db.close()

if __name__ == "__main__":
    analyze_and_update_sentiment()
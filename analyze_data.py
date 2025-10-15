# Import necessary libraries
from transformers import pipeline
from sqlalchemy.orm import Session

# Import components from our project files
from database import SessionLocal
from models import Tweet

def analyze_and_update_sentiment():
    """
    Finds tweets without sentiment, analyzes them using an AI model,
    and updates the database with the results.
    """
    # Establish a connection to the database
    db: Session = SessionLocal()
    
    print("--- 🧠 Starting Sentiment Analysis ---")

    try:
        # Step 1: Find all tweets that haven't been analyzed yet
        tweets_to_analyze = db.query(Tweet).filter(Tweet.sentiment_label == None).all()

        if not tweets_to_analyze:
            print("✅ No new tweets to analyze. Database is up to date.")
            return

        print(f"Found {len(tweets_to_analyze)} tweets to analyze...")

        # Step 2: Load the pre-trained AI model from Hugging Face
        # The model will be downloaded automatically the first time you run this.
        print("Loading sentiment analysis model (this may take a moment on first run)...")
        sentiment_pipeline = pipeline(
            "sentiment-analysis", 
            model="cardiffnlp/twitter-roberta-base-sentiment"
        )
        print("🤖 Model loaded successfully.")

        # Step 3: Analyze each tweet and update the object
        print("Analyzing tweets...")
        for i, tweet in enumerate(tweets_to_analyze):
            try:
                # Get the tweet's text
                text_to_analyze = tweet.text
                
                # The pipeline returns a list with a dictionary, e.g., [{'label': 'Positive', 'score': 0.98}]
                result = sentiment_pipeline(text_to_analyze)[0]
                
                # Update the tweet object in memory with the new sentiment data
                tweet.sentiment_label = result['label']
                tweet.sentiment_score = result['score']

                # Optional: Print progress for every 10 tweets
                if (i + 1) % 10 == 0:
                    print(f"   ...analyzed {i + 1}/{len(tweets_to_analyze)} tweets")

            except Exception as e:
                print(f"Could not analyze tweet ID {tweet.id}: {e}")
                # Mark as 'Error' so we don't try it again
                tweet.sentiment_label = 'Error'
        
        # Step 4: Commit all the changes to the database in one go
        print("\nSaving all new sentiment data to the database...")
        db.commit()
        print("✅ Analysis complete. Database has been updated.")

    except Exception as e:
        print(f"❌ An error occurred during the analysis process: {e}")
        db.rollback()
    finally:
        # Always close the database session
        print("Closing database session.")
        db.close()

# Standard entry point to run the script
if __name__ == "__main__":
    analyze_and_update_sentiment()
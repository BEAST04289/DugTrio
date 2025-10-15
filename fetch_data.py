import os
import tweepy
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Import the specific components from our project files
from database import SessionLocal
from models import Tweet

def fetch_and_store(db: Session, client: tweepy.Client, project_tag: str, search_query: str):
    """
    Fetches recent tweets for a given query, checks for duplicates,
    and stores new tweets in the database.
    """
    print(f"--- Fetching tweets for: {project_tag} ---")
    try:
        response = client.search_recent_tweets(
            query=search_query,
            max_results=50,
            tweet_fields=["created_at"],
            expansions=["author_id"]
        )

        if not response.data:
            print(f"No new tweets found for {project_tag}.")
            return

        tweets = response.data
        users = {user["id"]: user for user in response.includes["users"]}
        new_tweets_count = 0

        for tweet in tweets:
            exists = db.query(Tweet).filter(Tweet.tweet_id == str(tweet.id)).first()
            if not exists:
                new_tweet = Tweet(
                    tweet_id=str(tweet.id),
                    text=tweet.text,
                    author_username=users[tweet.author_id].username,
                    created_at=tweet.created_at,
                    project_tag=project_tag
                )
                db.add(new_tweet)
                new_tweets_count += 1
        
        print(f"Found and added {new_tweets_count} new tweets.")

    except Exception as e:
        print(f"An error occurred while fetching tweets for {project_tag}: {e}")


def main():
    """
    Main function to orchestrate the data fetching process using Bearer Token authentication.
    """
    load_dotenv()

    try:
        bearer_token = os.getenv("BEARER_TOKEN")
        if not bearer_token:
            raise ValueError("BEARER_TOKEN not found in .env file.")
        
        client = tweepy.Client(bearer_token=bearer_token)
        print("✅ Successfully authenticated with X.com API using Bearer Token.")
    except Exception as e:
        print(f"❌ Error authenticating with X.com API: {e}")
        return

    db = SessionLocal()

    # MODIFICATION: We are only tracking one project for now to avoid rate limits.
    projects_to_track = [
        {'name': 'Solana', 'query': '"Solana" OR "$SOL" -is:retweet lang:en'},
        # {'name': 'Jupiter', 'query': '"Jupiter Exchange" OR "$JUP" -is:retweet lang:en'},
        # {'name': 'Pyth Network', 'query': '"Pyth Network" OR "$PYTH" -is:retweet lang:en'},
        # {'name': 'Bonk', 'query': '"Bonk" OR "$BONK" -is:retweet lang:en'}
    ]

    try:
        for project in projects_to_track:
            fetch_and_store(db, client, project['name'], project['query'])
        
        print("\nCommitting all new tweets to the database...")
        db.commit()
        print("✅ Successfully saved new data.")
    except Exception as e:
        print(f"❌ A database error occurred: {e}")
        db.rollback()
    finally:
        print("Closing database session.")
        db.close()

# This is the standard entry point for a Python script.
if __name__ == "__main__":
    main()
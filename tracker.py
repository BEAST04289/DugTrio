import os
import tweepy
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, List

from database import SessionLocal
from models import Tweet, TrackRequest

# Load environment variables (needed to authenticate X client)
load_dotenv()

def fetch_and_store(db: Session, client: tweepy.Client, project_tag: str, search_query: str):
    """Fetches recent tweets and stores new, unique tweets in the database."""
    print(f"--- Fetching tweets for: {project_tag} ---")
    
    start_time = datetime.utcnow() - timedelta(hours=24)
    start_time_str = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        response = client.search_recent_tweets(
            query=search_query,
            max_results=50,
            start_time=start_time_str,
            tweet_fields=["created_at", "attachments"],
            expansions=["author_id", "attachments.media_keys"]
        )

        # FIX: Explicitly check for response.data existence before proceeding
        # This handles the "Cannot access attribute 'data'" error when no results are found.
        if not response.data: 
            print(f"No new tweets found for {project_tag}.")
            return

        tweets: List[Any] = response.data
        
        # Safely extract user and media mappings from includes, defaulting to empty dicts
        includes: Dict[str, Any] = response.includes or {}
        users: Dict[str, Any] = {user["id"]: user for user in includes.get("users", [])}
        media: Dict[str, Any] = {m["media_key"]: m for m in includes.get("media", [])}
        new_tweets_count = 0

        for tweet in tweets:
            exists = db.query(Tweet).filter(Tweet.tweet_id == str(tweet.id)).first()
            if not exists:
                media_url = None
                if tweet.attachments and tweet.attachments.get("media_keys"):
                    media_key = tweet.attachments["media_keys"][0]
                    if media.get(media_key, {}).get("type") == "photo":
                        media_url = media[media_key].get("url")

                new_tweet = Tweet(
                    tweet_id=str(tweet.id),
                    text=tweet.text,
                    author_username=users.get(tweet.author_id, {}).get("username", "Unknown"),
                    created_at=tweet.created_at,
                    project_tag=project_tag,
                    media_url=media_url
                )
                db.add(new_tweet)
                new_tweets_count += 1
        
        print(f"Found and added {new_tweets_count} new tweets.")

    except Exception as e:
        print(f"An error occurred while fetching tweets for {project_tag}: {e}")

def get_projects_to_track(db: Session) -> List[Dict[str, str]]:
    """
    Fetches the list of projects to track from the database.
    Includes a default project if the table is empty.
    """
    print("Querying database for projects to track...")
    tracked_projects = db.query(TrackRequest).all()

    if not tracked_projects:
        print("No projects found in the database. Using default 'Solana' project.")
        return [{'name': 'Solana', 'query': '"Solana" OR "$SOL" -is:retweet lang:en'}]

    projects = []
    for req in tracked_projects:
        # Simple query format, can be enhanced later (e.g., adding a ticker symbol)
        query = f'"{req.project_name}" -is:retweet lang:en'
        projects.append({'name': req.project_name, 'query': query})

    print(f"Found {len(projects)} projects to track.")
    return projects

def main():
    """Main function to orchestrate the data fetching process."""

    try:
        bearer_token = os.getenv("BEARER_TOKEN")
        if not bearer_token:
            raise ValueError("BEARER_TOKEN not found in .env file.")
        
        client = tweepy.Client(bearer_token=bearer_token)
        print("✅ Successfully authenticated with X.com API.")
    except Exception as e:
        print(f"❌ Error authenticating with X.com API: {e}")
        return

    db = SessionLocal()

    try:
        projects_to_track = get_projects_to_track(db)

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

if __name__ == "__main__":
    main()
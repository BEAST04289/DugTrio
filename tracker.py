import os
import tweepy
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, List

from database import SessionLocal
from models import Tweet, TrackRequest, TrendingProject
from sqlalchemy import and_, func

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

def calculate_trend_score(current_mentions: int, previous_mentions: int) -> float:
    """Calculates a trend score based on the change in mention volume."""
    # Simple growth rate calculation. Add 1 to avoid division by zero.
    return (current_mentions - previous_mentions) / (previous_mentions + 1)

async def analyze_and_update_trends():
    """
    Analyzes tweet volume for tracked projects to identify trends
    and saves the results to the database.
    """
    db: Session = SessionLocal()
    print("--- 📈 Starting Trend Analysis ---")

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
            print("No projects are being tracked. Skipping trend analysis.")
            return

        print(f"Analyzing trends for {len(project_names)} projects...")

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
            print("No significant trends detected in the last window.")
            return

        # Sort by trend score in descending order
        trending_results.sort(key=lambda x: x['trend_score'], reverse=True)

        # Clear the old trending projects data
        db.query(TrendingProject).delete()

        # Save the new top trending projects to the database
        print("Saving new trending projects to the database...")
        for result in trending_results[:10]: # Save top 10
            new_trend = TrendingProject(**result)
            db.add(new_trend)

        db.commit()
        print("✅ Trend analysis complete. Database has been updated.")

    except Exception as e:
        print(f"❌ An error occurred during the trend analysis process: {e}")
        db.rollback()
    finally:
        print("Closing database session.")
        db.close()

if __name__ == "__main__":
    main()
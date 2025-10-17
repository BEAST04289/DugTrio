import logging
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import SessionLocal
from models import Tweet, TrendingProject, TrackRequest

# Configure logging
logging.basicConfig(level=logging.INFO)

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
        # Define the time windows for analysis (e.g., last 4 hours vs. previous 4 hours)
        now = datetime.utcnow()
        current_window_start = now - timedelta(hours=4)
        previous_window_start = now - timedelta(hours=8)
        previous_window_end = current_window_start

        # Get all projects that are being tracked
        tracked_projects = db.query(TrackRequest.project_name).all()
        project_names = [p.project_name for p in tracked_projects]

        if not project_names:
            logging.warning("No projects are being tracked. Skipping trend analysis.")
            return

        logging.info(f"Analyzing trends for {len(project_names)} projects...")

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
            logging.info("No significant trends detected in the last window.")
            return

        # Sort by trend score in descending order
        trending_results.sort(key=lambda x: x['trend_score'], reverse=True)

        # Clear the old trending projects data
        db.query(TrendingProject).delete()

        # Save the new top trending projects to the database
        logging.info("Saving new trending projects to the database...")
        for result in trending_results[:10]: # Save top 10
            new_trend = TrendingProject(**result)
            db.add(new_trend)

        db.commit()
        logging.info("✅ Trend analysis complete. Database has been updated.")

    except Exception as e:
        logging.error(f"❌ An error occurred during the trend analysis process: {e}")
        db.rollback()
    finally:
        logging.info("Closing database session.")
        db.close()

if __name__ == "__main__":
    analyze_and_update_trends()
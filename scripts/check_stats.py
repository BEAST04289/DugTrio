from sqlalchemy import func
from database.connection import SessionLocal
from database.models import Tweet

def show_stats():
    db = SessionLocal()
    try:
        print("\n📊 --- SCRAPER STATISTICS ---")
        
        # Count total tweets
        total = db.query(Tweet).count()
        print(f"Total Tweets in DB: {total}")

        # Count by Project
        print("\nBy Project:")
        projects = db.query(Tweet.project_tag, func.count(Tweet.id)).group_by(Tweet.project_tag).all()
        
        if not projects:
            print("  (No data found)")
        
        for project, count in projects:
            # Count how many have been analyzed (have a score)
            analyzed = db.query(Tweet).filter(
                Tweet.project_tag == project, 
                Tweet.sentiment_score != None
            ).count()
            print(f"  • {project}: {count} tweets ({analyzed} analyzed)")

    finally:
        db.close()

if __name__ == "__main__":
    show_stats()
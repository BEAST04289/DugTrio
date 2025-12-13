import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

# --- Database Imports ---
from database.connection import get_db
from database.models import Tweet, TrackRequest, PnlCard

# --- Service Imports (Fixes the errors) ---
from services.story_service import register_ip_on_chain
from services.tracker import run_single_project_tracker
from services.analyzer import analyze_and_update_sentiment

# --- Configuration ---
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dugtrio.api")

app = FastAPI(title="DugTrio API", description="Sentiment Analysis & IP Registration")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Endpoints ---

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"status": "online", "service": "DugTrio Backend"}

@app.get("/sentiment")
def get_sentiment_for_bot(db: Session = Depends(get_db)):
    """Returns aggregated sentiment data."""
    results = []
    projects = db.query(Tweet.project_tag).distinct().all()
    
    for (project_tag,) in projects:
        if not project_tag: continue
        
        # 1. Calculate Average Score
        avg_score = db.query(func.avg(Tweet.sentiment_score)).filter(
            Tweet.project_tag == project_tag, Tweet.sentiment_score != None
        ).scalar()
        
        if avg_score is None: continue
        
        # 2. Fetch Recent Tweets
        recent_tweets = db.query(Tweet.text).filter(
            Tweet.project_tag == project_tag
        ).order_by(Tweet.created_at.desc()).limit(3).all()
        
        tweet_texts = [t[0] for t in recent_tweets]

        if avg_score > 0.6: label = "Bullish"
        elif avg_score < 0.4: label = "Bearish"
        else: label = "Neutral"
        
        results.append({
            "project_tag": project_tag, 
            "label": label, 
            "score": round(avg_score, 2),
            "tweets": tweet_texts
        })
        
    return results

@app.get("/tweets")
def get_tweets_count(db: Session = Depends(get_db)):
    return db.query(Tweet).limit(10).all() if Tweet else []

@app.get("/pnl-cards")
def get_pnl_cards_count(db: Session = Depends(get_db)):
    return db.query(PnlCard).limit(10).all() if PnlCard else []

@app.post("/ip/register-sentiment/{project_tag}", tags=["Story Protocol"])
async def register_sentiment_ip(project_tag: str, db: Session = Depends(get_db)):
    """Registers IP. Uses DB data if available."""
    logger.info(f"🔵 HIT: /ip/register-sentiment/{project_tag}")
    
    # 1. Check Data Availability
    avg_score = db.query(func.avg(Tweet.sentiment_score)).filter(
        Tweet.project_tag == project_tag
    ).scalar()
    
    if avg_score is None:
        logger.warning(f"No data found for {project_tag}.")
        raise HTTPException(status_code=404, detail=f"No sentiment data found for {project_tag}. Please wait for the scraper to collect data.")
    
    # 2. Prepare Report
    sentiment_label = "Neutral"
    if avg_score > 0.6: sentiment_label = "Bullish"
    elif avg_score < 0.4: sentiment_label = "Bearish"
    
    report = {
        "project": project_tag,
        "sentiment": sentiment_label,
        "score": round(avg_score, 2),
        "timestamp": datetime.utcnow().isoformat(),
        "generator": "DugTrio AI",
        "note": "Generated via DugTrio Sentiment Engine"
    }

    # 3. Call Service
    try:
        # This function is now imported from story_service.py
        tx_hash = await register_ip_on_chain(project_tag, report)
        return {
            "message": "Success",
            "project": project_tag,
            "transaction_hash": tx_hash,
            "explorer_url": f"https://sepolia.etherscan.io/tx/{tx_hash}"
        }
    except Exception as e:
        logger.error(f"IP Registration Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update/{project_tag}")
async def trigger_update(project_tag: str):
    """
    Triggers an on-demand scrape and analysis for a specific project.
    Called by the bot when a user requests sentiment.
    """
    logger.info(f"🔄 Triggering update for {project_tag}...")
    
    # Run in a separate thread to avoid blocking the API
    try:
        # 1. Scrape (10 tweets max)
        run_single_project_tracker(project_tag)
        
        # 2. Analyze
        analyze_and_update_sentiment()
        
        return {"status": "updated", "project": project_tag}
    except Exception as e:
        logger.error(f"Update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
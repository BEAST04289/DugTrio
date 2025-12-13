import logging
import re
import pytesseract
import requests
from PIL import Image
from io import BytesIO
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, cast

from database.connection import SessionLocal
from database.models import Tweet, PnlCard

# Configure logging
logging.basicConfig(level=logging.INFO)

def download_image(url: str) -> Optional[Image.Image]:
    """Downloads an image from a URL and returns a PIL Image object."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading image from {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error opening image: {e}")
        return None

def extract_text_from_image(image: Image.Image) -> str:
    """Extracts text from a PIL Image object using Tesseract OCR."""
    try:
        return pytesseract.image_to_string(image)
    except pytesseract.TesseractNotFoundError:
        logging.error("Tesseract is not installed or not in your PATH.")
        return ""
    except Exception as e:
        logging.error(f"Error during OCR extraction: {e}")
        return ""

def parse_pnl_data(text: str) -> Dict[str, Any]:
    """Parses extracted text to find PNL-related data."""
    data: Dict[str, Any] = {
        "entry_price": None,
        "exit_price": None,
        "pnl_percentage": None,
        "token_symbol": None,
    }
    
    # Normalize text for easier parsing
    text = text.lower()
    
    # --- PNL Percentage Extraction ---
    pnl_match = re.search(r'(pnl|profit|loss)\s*:?\s*([\+\-]?\s*\d+(\.\d+)?)\s*%', text)
    if pnl_match:
        try:
            pnl_value = pnl_match.group(2).replace(' ', '').replace('+', '')
            data['pnl_percentage'] = float(pnl_value)
        except (ValueError, AttributeError) as e:
            logging.warning(f"Failed to parse PNL percentage: {e}")
    
    if data['pnl_percentage'] is None:
        pnl_match = re.search(r'([\+\-]\s*\d+(\.\d+)?)\s*%', text)
        if pnl_match:
            try:
                pnl_value = pnl_match.group(1).replace(' ', '').replace('+', '')
                data['pnl_percentage'] = float(pnl_value)
            except (ValueError, AttributeError) as e:
                logging.warning(f"Failed to parse PNL percentage from fallback: {e}")
    
    # --- Token Symbol Extraction ---
    symbol_match = re.search(r'\$([a-z]{3,5})\b', text)
    if not symbol_match:
        symbol_match = re.search(r'\b([a-z]{3,5})\b\s*(entry|exit)', text)
    if symbol_match:
        data['token_symbol'] = symbol_match.group(1).upper()
    
    # --- Entry and Exit Price Extraction ---
    entry_match = re.search(r'entry\s*(price)?\s*:?\s*\$?(\d+(\.\d+)?)', text)
    if entry_match:
        try:
            data['entry_price'] = float(entry_match.group(2))
        except (ValueError, AttributeError) as e:
            logging.warning(f"Failed to parse entry price: {e}")

    exit_match = re.search(r'exit\s*(price)?\s*:?\s*\$?(\d+(\.\d+)?)', text)
    if exit_match:
        try:
            data['exit_price'] = float(exit_match.group(2))
        except (ValueError, AttributeError) as e:
            logging.warning(f"Failed to parse exit price: {e}")
    
    return data

def analyze_pnl_cards():
    """
    Finds tweets with media URLs that haven't been analyzed for PNL data,
    processes them, and updates the database.
    """
    db: Session = SessionLocal()
    logging.info("--- 📈 Starting PNL Card Analysis ---")

    try:
        # Find tweets with a media_url that don't have a corresponding PnlCard entry yet.
        tweets_to_process: List[Tweet] = db.query(Tweet).filter(
            Tweet.media_url != None,
            Tweet.pnl_card == None
        ).all()

        if not tweets_to_process:
            logging.info("✅ No new PNL cards to analyze.")
            return

        logging.info(f"Found {len(tweets_to_process)} potential PNL cards to analyze...")

        for tweet in tweets_to_process:
            logging.info(f"Processing tweet {tweet.id} with media URL: {tweet.media_url}")

            # Simplified - media_url is guaranteed to exist from the filter above
            image = download_image(cast(str, tweet.media_url))
            if not image:
                # Create a failed PnlCard entry
                pnl_card = PnlCard(tweet_id=tweet.id, analysis_status='download_failed')
                db.add(pnl_card)
                continue

            extracted_text = extract_text_from_image(image)
            if not extracted_text:
                # Create a failed PnlCard entry
                pnl_card = PnlCard(tweet_id=tweet.id, analysis_status='ocr_failed')
                db.add(pnl_card)
                continue

            pnl_data = parse_pnl_data(extracted_text)

            # Create a new PnlCard with the extracted data
            pnl_card = PnlCard(
                tweet_id=tweet.id,
                analysis_status='success',
                extracted_text=extracted_text,
                **pnl_data
            )
            db.add(pnl_card)

        logging.info("Committing all new PNL card data to the database...")
        db.commit()
        logging.info("✅ PNL analysis complete.")

    except Exception as e:
        logging.error(f"❌ An error occurred during the PNL analysis process: {e}")
        db.rollback()
    finally:
        logging.info("Closing database session.")
        db.close()

if __name__ == "__main__":
    analyze_pnl_cards()
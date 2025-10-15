import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file. Please check your configuration.")

# The engine is the core interface to the database.
engine = create_engine(DATABASE_URL)

# SessionLocal class is a factory for creating new, individual database sessions.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all our SQLAlchemy models to inherit from.
Base = declarative_base()


# NEW FEATURE: A dependency to manage database sessions.
# This ensures that every database session is correctly closed after use.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Utility function for initial database setup ---
def create_all_tables():
    """Creates all tables in the database defined by models inheriting from Base."""
    print("Attempting to create tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"An error occurred during table creation: {e}")
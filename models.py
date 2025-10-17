from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, func
from database import Base

# This model defines the structure for storing user information in the database.
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    join_date = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', premium={self.is_premium})>"


# This model defines the structure for storing the tweets we collect.
class Tweet(Base):
    __tablename__ = 'tweets'

    id = Column(Integer, primary_key=True, index=True)
    tweet_id = Column(String, unique=True, nullable=False, index=True)
    text = Column(String, nullable=False)
    author_username = Column(String)
    created_at = Column(DateTime(timezone=True))
    project_tag = Column(String, index=True)
    
    # These fields will be populated by our analysis script later.
    sentiment_label = Column(String, nullable=True)
    sentiment_score = Column(Float, nullable=True)

    def __repr__(self):
        return f"<Tweet(id={self.id}, project='{self.project_tag}', sentiment='{self.sentiment_label}')>"


# This model will store which users are tracking which wallets (a premium feature).
class TrackedWallet(Base):
    __tablename__ = 'tracked_wallets'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False) # Foreign key could be added later
    wallet_address = Column(String, nullable=False, index=True)

    def __repr__(self):
        return f"<TrackedWallet(user_id={self.user_id}, address='{self.wallet_address}')>"


# This model stores user requests for new projects to be tracked.
class TrackRequest(Base):
    __tablename__ = 'track_requests'

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, unique=True, nullable=False, index=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TrackRequest(id={self.id}, project_name='{self.project_name}')>"


# This model stores the results of the trend analysis.
class TrendingProject(Base):
    __tablename__ = 'trending_projects'

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True, nullable=False)
    mention_count = Column(Integer, nullable=False)
    trend_score = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TrendingProject(project_name='{self.project_name}', score={self.trend_score})>"
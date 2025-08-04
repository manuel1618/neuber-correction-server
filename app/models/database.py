"""
Database models for session management and rate limiting
"""

import os

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class Session(Base):
    """User session tracking"""

    __tablename__ = "sessions"

    session_id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, default=func.now)
    last_activity = Column(DateTime, default=func.now)
    request_count = Column(Integer, default=0)
    ip_address = Column(String(45))  # IPv6 compatible


class RateLimit(Base):
    """Rate limiting tracking"""

    __tablename__ = "rate_limits"

    key = Column(String(100), primary_key=True)  # IP or session_id
    requests = Column(Integer, default=0)
    window_start = Column(DateTime, default=func.now)


class UsageLog(Base):
    """Usage analytics"""

    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36))
    endpoint = Column(String(100))
    duration_ms = Column(Integer)
    success = Column(Boolean)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=func.now)
    ip_address = Column(String(45))


# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./neuber_correction.db")
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

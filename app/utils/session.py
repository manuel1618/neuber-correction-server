"""
Session management utilities
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Request

from app.db.interface import DBInterface

# In-memory storage for user materials (session-specific)
user_materials: Dict[str, Dict[str, Any]] = {}


def get_session_id(request: Request) -> str:
    """Get or create session ID for user"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id


def get_user_materials(session_id: str) -> Dict[str, Any]:
    """Get user's custom materials from memory"""
    return user_materials.get(session_id, {})


def save_user_materials(session_id: str, materials: Dict[str, Any]):
    """Save user's custom materials to memory"""
    user_materials[session_id] = materials


def cleanup_expired_sessions():
    """Clean up expired sessions (run periodically)"""
    # In a real implementation, you'd check session TTL
    # For now, just keep the last 1000 sessions
    if len(user_materials) > 1000:
        # Remove oldest sessions (simple FIFO)
        oldest_keys = list(user_materials.keys())[:100]
        for key in oldest_keys:
            del user_materials[key]


def update_session_activity(db: DBInterface, session_id: str, ip_address: str):
    """Update session activity in database"""
    db.update_session_activity(session_id, ip_address)


def check_rate_limit(
    db: DBInterface, key: str, limit: int, window_minutes: int = 1
) -> bool:
    """Check if rate limit is exceeded"""
    now = datetime.now()
    window_start = now - timedelta(minutes=window_minutes)

    # Get or create rate limit record
    rate_limit = db.get_rate_limit(key)

    if not rate_limit:
        db.create_rate_limit(key, now)
        return True

    # Check if window has expired
    if rate_limit["window_start"] < window_start:
        db.update_rate_limit(key, 1, now)
        return True

    # Check if limit exceeded
    if rate_limit["requests"] >= limit:
        return False

    # Increment request count
    db.update_rate_limit(key, rate_limit["requests"] + 1, rate_limit["window_start"])
    return True


def log_usage(
    db: DBInterface,
    session_id: str,
    endpoint: str,
    duration_ms: int,
    success: bool,
    ip_address: str,
    error_message: Optional[str] = None,
):
    """Log usage analytics"""
    db.log_usage(session_id, endpoint, duration_ms, success, ip_address, error_message)


def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    # Check for forwarded headers (proxy/load balancer)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return request.client.host if request.client else "unknown"

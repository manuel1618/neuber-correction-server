"""
Database interface
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional


class DBInterface(ABC):
    """Abstract database interface for session management and rate limiting"""

    @abstractmethod
    def __init__(self, db_path: str):
        """Initialize database connection"""

    @abstractmethod
    def create_tables(self) -> None:
        """Create all required database tables"""

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""

    @abstractmethod
    def create_session(self, session_id: str, ip_address: str) -> None:
        """Create a new session"""

    @abstractmethod
    def update_session_activity(self, session_id: str, ip_address: str) -> None:
        """Update session activity timestamp and request count"""

    @abstractmethod
    def get_rate_limit(self, key: str) -> Optional[Dict[str, Any]]:
        """Get rate limit record by key"""

    @abstractmethod
    def create_rate_limit(self, key: str, window_start: datetime) -> None:
        """Create a new rate limit record"""

    @abstractmethod
    def update_rate_limit(
        self, key: str, requests: int, window_start: datetime
    ) -> None:
        """Update rate limit record"""

    @abstractmethod
    def log_usage(
        self,
        session_id: str,
        endpoint: str,
        duration_ms: int,
        success: bool,
        ip_address: str,
        error_message: Optional[str] = None,
    ) -> None:
        """Log usage analytics"""

    @abstractmethod
    def get_session_count(self) -> int:
        """Get total number of active sessions"""

    @abstractmethod
    def close(self) -> None:
        """Close database connection"""

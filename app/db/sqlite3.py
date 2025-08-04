"""
SQLite database implementation
"""

import sqlite3
from datetime import datetime
from typing import Any, Dict, Optional

from app.db.interface import DBInterface


class SQLiteDatabase(DBInterface):
    """
    SQLite database implementation
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = self._create_connection(db_path)

    def _create_connection(self, db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(
            db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        return conn

    def create_tables(self) -> None:
        """Create all required database tables"""
        try:
            with open("db/migrations/2025-08-04-init.sql", "r", encoding="utf-8") as f:
                sql_script = f.read()

            cursor = self.connection.cursor()
            cursor.executescript(sql_script)
            self.connection.commit()
        except Exception as e:
            # Tables might already exist, which is fine
            if "already exists" not in str(e):
                raise e

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT session_id, created_at, last_activity, request_count, ip_address "
            "FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            # Convert datetime strings back to datetime objects if needed
            for field in ["created_at", "last_activity"]:
                if isinstance(result[field], str):
                    result[field] = datetime.fromisoformat(result[field])
            return result
        return None

    def create_session(self, session_id: str, ip_address: str) -> None:
        """Create a new session"""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO sessions (session_id, created_at, last_activity, request_count, "
            "ip_address) VALUES (?, ?, ?, ?, ?)",
            (session_id, datetime.now(), datetime.now(), 1, ip_address),
        )
        self.connection.commit()

    def update_session_activity(self, session_id: str, ip_address: str) -> None:
        """Update session activity timestamp and request count"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE sessions SET last_activity = ?, request_count = request_count + 1 WHERE session_id = ?",
            (datetime.now(), session_id),
        )
        if cursor.rowcount == 0:
            # Session doesn't exist, create it
            self.create_session(session_id, ip_address)
        else:
            self.connection.commit()

    def get_rate_limit(self, key: str) -> Optional[Dict[str, Any]]:
        """Get rate limit record by key"""
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT key, requests, window_start FROM rate_limits WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row:
            result = dict(row)
            # Convert window_start string back to datetime if needed
            if isinstance(result["window_start"], str):
                result["window_start"] = datetime.fromisoformat(result["window_start"])
            return result
        return None

    def create_rate_limit(self, key: str, window_start: datetime) -> None:
        """Create a new rate limit record"""
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO rate_limits (key, requests, window_start) VALUES (?, ?, ?)",
            (key, 1, window_start),
        )
        self.connection.commit()

    def update_rate_limit(
        self, key: str, requests: int, window_start: datetime
    ) -> None:
        """Update rate limit record"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE rate_limits SET requests = ?, window_start = ? WHERE key = ?",
            (requests, window_start, key),
        )
        self.connection.commit()

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
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO usage_logs (session_id, endpoint, duration_ms, success, "
            "error_message, timestamp, ip_address) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                endpoint,
                duration_ms,
                success,
                error_message,
                datetime.now(),
                ip_address,
            ),
        )
        self.connection.commit()

    def get_session_count(self) -> int:
        """Get total number of active sessions"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM sessions")
        result = cursor.fetchone()
        return result[0] if result else 0

    def close(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()

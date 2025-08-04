"""
Tests for database interface and SQLite implementation
"""

import os
import tempfile
from datetime import datetime, timedelta

import pytest

from app.db.interface import DBInterface
from app.db.sqlite3 import SQLiteDatabase


class TestDatabaseInterface:
    """Test the database interface abstract class"""

    def test_interface_has_required_methods(self):
        """Test that DBInterface has all required abstract methods"""
        required_methods = [
            "__init__",
            "create_tables",
            "get_session",
            "create_session",
            "update_session_activity",
            "get_rate_limit",
            "create_rate_limit",
            "update_rate_limit",
            "log_usage",
            "get_session_count",
            "clear_all_data",
            "cleanup_expired_sessions",
            "close",
        ]

        for method_name in required_methods:
            assert hasattr(
                DBInterface, method_name
            ), f"Method {method_name} not found in DBInterface"


class TestSQLiteDatabase:
    """Test the SQLite database implementation"""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def db(self, temp_db_path):
        """Create a database instance for testing"""
        db = SQLiteDatabase(temp_db_path)
        db.create_tables()
        yield db
        db.close()

    def test_database_creation(self, temp_db_path):
        """Test database creation and connection"""
        db = SQLiteDatabase(temp_db_path)
        assert db.db_path == temp_db_path
        # Test that we can get a connection
        connection = db._get_connection()
        assert connection is not None
        db.close()

    def test_create_tables(self, temp_db_path):
        """Test table creation"""
        db = SQLiteDatabase(temp_db_path)
        db.create_tables()

        # Check that tables exist
        connection = db._get_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ["sessions", "rate_limits", "usage_logs"]
        for table in expected_tables:
            assert table in tables, f"Table {table} not created"

        db.close()

    def test_create_tables_already_exists(self, temp_db_path):
        """Test table creation when tables already exist"""
        db = SQLiteDatabase(temp_db_path)

        # Create tables twice
        db.create_tables()
        db.create_tables()  # Should not raise an error

        db.close()

    def test_session_operations(self, db):
        """Test session creation, retrieval, and updates"""
        session_id = "test-session-123"
        ip_address = "192.168.1.1"

        # Test session creation
        db.create_session(session_id, ip_address)

        # Test session retrieval
        session = db.get_session(session_id)
        assert session is not None
        assert session["session_id"] == session_id
        assert session["ip_address"] == ip_address
        assert session["request_count"] == 1
        assert isinstance(session["created_at"], datetime)
        assert isinstance(session["last_activity"], datetime)

        # Test session update
        db.update_session_activity(session_id, ip_address)
        updated_session = db.get_session(session_id)
        assert updated_session["request_count"] == 2

        # Test non-existent session
        non_existent = db.get_session("non-existent")
        assert non_existent is None

    def test_rate_limit_operations(self, db):
        """Test rate limit creation, retrieval, and updates"""
        key = "test-rate-limit-key"
        window_start = datetime.now()

        # Test rate limit creation
        db.create_rate_limit(key, window_start)

        # Test rate limit retrieval
        rate_limit = db.get_rate_limit(key)
        assert rate_limit is not None
        assert rate_limit["key"] == key
        assert rate_limit["requests"] == 1
        assert isinstance(rate_limit["window_start"], datetime)

        # Test rate limit update
        new_requests = 5
        db.update_rate_limit(key, new_requests, window_start)
        updated_rate_limit = db.get_rate_limit(key)
        assert updated_rate_limit["requests"] == new_requests

        # Test non-existent rate limit
        non_existent = db.get_rate_limit("non-existent")
        assert non_existent is None

    def test_usage_logging(self, db):
        """Test usage logging functionality"""
        session_id = "test-session-456"
        endpoint = "/api/test"
        duration_ms = 150
        success = True
        ip_address = "192.168.1.2"
        error_message = "Test error"

        # Test successful usage log
        db.log_usage(session_id, endpoint, duration_ms, success, ip_address)

        # Test failed usage log with error message
        db.log_usage(
            session_id, endpoint, duration_ms, False, ip_address, error_message
        )

        # Verify logs were created (we can't easily query them without adding a method)
        # This test mainly ensures the method doesn't raise exceptions

    def test_session_count(self, db):
        """Test session count functionality"""
        # Initially should be 0
        assert db.get_session_count() == 0

        # Create some sessions
        db.create_session("session1", "192.168.1.1")
        db.create_session("session2", "192.168.1.2")

        # Should now be 2
        assert db.get_session_count() == 2

    def test_clear_all_data(self, db):
        """Test clearing all data from database"""
        # Create some test data
        db.create_session("session1", "192.168.1.1")
        db.create_session("session2", "192.168.1.2")
        db.create_rate_limit("key1", datetime.now())

        # Verify data exists
        assert db.get_session_count() == 2
        assert db.get_rate_limit("key1") is not None

        # Clear all data
        db.clear_all_data()

        # Verify data is cleared
        assert db.get_session_count() == 0
        assert db.get_rate_limit("key1") is None

    def test_cleanup_expired_sessions(self, db):
        """Test cleanup of expired sessions"""
        now = datetime.now()
        old_time = now - timedelta(hours=2)

        # Create old sessions
        db.create_session("old-session1", "192.168.1.1")
        db.create_session("old-session2", "192.168.1.2")

        # Manually update timestamps to be old
        connection = db._get_connection()
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE sessions SET last_activity = ? WHERE session_id IN (?, ?)",
            (old_time, "old-session1", "old-session2"),
        )
        cursor.execute(
            "UPDATE rate_limits SET window_start = ? WHERE key IN (?, ?)",
            (old_time, "old-key1", "old-key2"),
        )
        cursor.execute(
            "UPDATE usage_logs SET timestamp = ? WHERE session_id IN (?, ?)",
            (old_time, "old-session1", "old-session2"),
        )
        connection.commit()

        # Create recent sessions
        db.create_session("recent-session1", "192.168.1.3")
        db.create_session("recent-session2", "192.168.1.4")

        # Cleanup with 1 hour TTL
        ttl_seconds = 3600  # 1 hour
        db.cleanup_expired_sessions(ttl_seconds)

        # Old sessions should be removed, recent ones should remain
        assert db.get_session("old-session1") is None
        assert db.get_session("old-session2") is None
        assert db.get_session("recent-session1") is not None
        assert db.get_session("recent-session2") is not None

    def test_datetime_parsing(self, db):
        """Test datetime parsing from SQLite strings"""
        session_id = "test-datetime-session"
        ip_address = "192.168.1.5"

        # Create session
        db.create_session(session_id, ip_address)

        # Retrieve session (should parse datetime strings correctly)
        session = db.get_session(session_id)
        assert isinstance(session["created_at"], datetime)
        assert isinstance(session["last_activity"], datetime)

        # Test rate limit datetime parsing
        key = "test-datetime-key"
        window_start = datetime.now()
        db.create_rate_limit(key, window_start)

        rate_limit = db.get_rate_limit(key)
        assert isinstance(rate_limit["window_start"], datetime)

    def test_database_connection_error_handling(self):
        """Test handling of database connection errors"""
        # Test with invalid path - this should not raise an exception immediately
        # since connections are created lazily
        db = SQLiteDatabase("/invalid/path/that/does/not/exist.db")
        # The error will occur when we try to use the database
        with pytest.raises(Exception):
            db.create_tables()

    def test_concurrent_access(self, temp_db_path):
        """Test concurrent database access"""
        db1 = SQLiteDatabase(temp_db_path)
        db2 = SQLiteDatabase(temp_db_path)

        # Both should be able to create tables
        db1.create_tables()
        db2.create_tables()

        # Both should be able to create sessions
        db1.create_session("session1", "192.168.1.1")
        db2.create_session("session2", "192.168.1.2")

        # Both should be able to read
        session1 = db1.get_session("session1")
        session2 = db2.get_session("session2")

        assert session1 is not None
        assert session2 is not None

        db1.close()
        db2.close()


class TestDatabaseIntegration:
    """Integration tests for database functionality"""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file for testing"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        yield db_path

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_full_workflow(self, temp_db_path):
        """Test a complete workflow with sessions, rate limits, and usage logs"""
        db = SQLiteDatabase(temp_db_path)
        db.create_tables()

        # Create session
        session_id = "workflow-session"
        ip_address = "192.168.1.100"
        db.create_session(session_id, ip_address)

        # Update session activity
        db.update_session_activity(session_id, ip_address)
        db.update_session_activity(session_id, ip_address)

        # Create rate limit
        rate_key = f"rate:{ip_address}"
        window_start = datetime.now()
        db.create_rate_limit(rate_key, window_start)

        # Update rate limit
        db.update_rate_limit(rate_key, 5, window_start)

        # Log usage
        db.log_usage(session_id, "/api/test", 200, True, ip_address)
        db.log_usage(session_id, "/api/test", 150, False, ip_address, "Test error")

        # Verify final state
        session = db.get_session(session_id)
        rate_limit = db.get_rate_limit(rate_key)

        assert session["request_count"] == 3
        assert rate_limit["requests"] == 5
        assert db.get_session_count() == 1

        db.close()

    def test_database_persistence(self, temp_db_path):
        """Test that data persists between database connections"""
        # First connection
        db1 = SQLiteDatabase(temp_db_path)
        db1.create_tables()
        db1.create_session("persistent-session", "192.168.1.200")
        db1.close()

        # Second connection
        db2 = SQLiteDatabase(temp_db_path)
        session = db2.get_session("persistent-session")
        assert session is not None
        assert session["session_id"] == "persistent-session"
        db2.close()

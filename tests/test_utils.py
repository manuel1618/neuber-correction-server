"""
Tests for utility functions
"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.utils.session import (
    check_rate_limit,
    get_client_ip,
    get_session_id,
    log_usage,
    update_session_activity,
)
from app.utils.settings import Settings


class TestSettings:
    """Test application settings"""

    def test_settings_defaults(self):
        """Test default settings values"""
        settings = Settings()

        assert settings.database_path == "neuber_correction.db"
        assert settings.database_ttl == 3600 * 24  # 1 day
        assert settings.rate_limit_window == 60  # 1 minute
        assert settings.rate_limit_requests == 100  # 100 requests per minute

    def test_settings_environment_override(self):
        """Test settings override from environment variables"""
        with patch.dict(
            os.environ,
            {
                "DATABASE_PATH": "/custom/path.db",
                "DATABASE_TTL": "7200",
                "RATE_LIMIT_WINDOW": "120",
                "RATE_LIMIT_REQUESTS": "50",
            },
        ):
            settings = Settings()

            assert settings.database_path == "/custom/path.db"
            assert settings.database_ttl == 7200
            assert settings.rate_limit_window == 120
            assert settings.rate_limit_requests == 50

    def test_settings_invalid_environment_values(self):
        """Test settings with invalid environment values"""
        with patch.dict(
            os.environ,
            {
                "DATABASE_TTL": "invalid",
                "RATE_LIMIT_WINDOW": "invalid",
                "RATE_LIMIT_REQUESTS": "invalid",
            },
        ):
            # Should use defaults when environment values are invalid
            settings = Settings()

            assert settings.database_ttl == 3600 * 24
            assert settings.rate_limit_window == 60
            assert settings.rate_limit_requests == 100

    def test_settings_validation(self):
        """Test settings validation"""
        settings = Settings()

        # All values should be positive
        assert settings.database_ttl > 0
        assert settings.rate_limit_window > 0
        assert settings.rate_limit_requests > 0

        # Database path should be a string
        assert isinstance(settings.database_path, str)
        assert len(settings.database_path) > 0


class TestSessionManagement:
    """Test session management utilities"""

    def test_get_session_id_from_cookie(self):
        """Test getting session ID from cookie"""
        mock_request = MagicMock()
        mock_request.cookies = {"session_id": "test-session-123"}

        session_id = get_session_id(mock_request)
        assert session_id == "test-session-123"

    def test_get_session_id_generate_new(self):
        """Test generating new session ID when not present"""
        mock_request = MagicMock()
        mock_request.cookies = {}

        session_id = get_session_id(mock_request)
        assert session_id is not None
        assert len(session_id) > 0
        assert isinstance(session_id, str)

    def test_get_session_id_different_requests(self):
        """Test that different requests get different session IDs"""
        mock_request1 = MagicMock()
        mock_request1.cookies = {}

        mock_request2 = MagicMock()
        mock_request2.cookies = {}

        session_id1 = get_session_id(mock_request1)
        session_id2 = get_session_id(mock_request2)

        assert session_id1 != session_id2

    def test_get_client_ip_direct(self):
        """Test getting client IP from direct connection"""
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {}

        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_forwarded(self):
        """Test getting client IP from forwarded headers"""
        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"
        mock_request.headers = {"X-Forwarded-For": "203.0.113.1, 192.168.1.100"}

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_real_ip(self):
        """Test getting client IP from X-Real-IP header"""
        mock_request = MagicMock()
        mock_request.client.host = "10.0.0.1"
        mock_request.headers = {"X-Real-IP": "203.0.113.1"}

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"

    def test_get_client_ip_priority(self):
        """Test IP address header priority"""
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            "X-Real-IP": "198.51.100.1",
        }

        # Should prioritize X-Forwarded-For (first IP)
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_check_rate_limit_new_key(self, mock_db):
        """Test rate limiting with new key"""
        # Mock database to return None for new key
        mock_db.get_rate_limit.return_value = None

        result, rate_info = check_rate_limit(mock_db, "test-key")

        assert result is True
        assert rate_info["limit"] == 100
        assert rate_info["remaining"] == 99
        mock_db.create_rate_limit.assert_called_once()

    def test_check_rate_limit_within_window(self, mock_db):
        """Test rate limiting within window"""
        # Mock existing rate limit within window
        now = datetime.now()
        mock_rate_limit = {
            "key": "test-key",
            "requests": 50,
            "window_start": now - timedelta(seconds=30),  # Within 60s window
        }
        mock_db.get_rate_limit.return_value = mock_rate_limit

        result, rate_info = check_rate_limit(mock_db, "test-key")

        assert result is True
        assert rate_info["limit"] == 100
        assert rate_info["remaining"] == 49
        mock_db.update_rate_limit.assert_called_once_with(
            "test-key", 51, mock_rate_limit["window_start"]
        )

    def test_check_rate_limit_exceeded(self, mock_db):
        """Test rate limiting when limit exceeded"""
        # Mock existing rate limit at limit
        now = datetime.now()
        mock_rate_limit = {
            "key": "test-key",
            "requests": 100,  # At limit
            "window_start": now - timedelta(seconds=30),  # Within window
        }
        mock_db.get_rate_limit.return_value = mock_rate_limit

        result, rate_info = check_rate_limit(mock_db, "test-key")

        assert result is False
        assert rate_info["limit"] == 100
        assert rate_info["remaining"] == 0

    def test_check_rate_limit_window_expired(self, mock_db):
        """Test rate limiting when window expired"""
        # Mock existing rate limit with expired window
        now = datetime.now()
        mock_rate_limit = {
            "key": "test-key",
            "requests": 50,
            "window_start": now - timedelta(seconds=120),  # Outside 60s window
        }
        mock_db.get_rate_limit.return_value = mock_rate_limit

        result, rate_info = check_rate_limit(mock_db, "test-key")

        assert result is True
        assert rate_info["limit"] == 100
        assert rate_info["remaining"] == 99
        # Check that update_rate_limit was called with correct parameters
        mock_db.update_rate_limit.assert_called_once()
        call_args = mock_db.update_rate_limit.call_args
        assert call_args[0][0] == "test-key"  # key
        assert call_args[0][1] == 1  # requests
        # The timestamp should be close to now (within 1 second)
        call_timestamp = call_args[0][2]
        assert abs((call_timestamp - now).total_seconds()) < 1

    def test_check_rate_limit_database_error(self):
        """Test rate limiting with database error"""
        mock_db = MagicMock()
        mock_db.get_rate_limit.side_effect = Exception("Database error")

        # Should handle database errors gracefully
        result, rate_info = check_rate_limit(mock_db, "test-key")
        assert result is True
        assert "limit" in rate_info

    def test_check_rate_limit_edge_cases(self):
        """Test rate limiting edge cases"""
        # Test with None database
        result, rate_info = check_rate_limit(None, "test-key")
        assert result is True
        assert "limit" in rate_info

        # Test with empty key
        mock_db = MagicMock()
        mock_db.get_rate_limit.return_value = None
        result, rate_info = check_rate_limit(mock_db, "")
        assert result is True


class TestUsageLogging:
    """Test usage logging functionality"""

    def test_log_usage_success(self):
        """Test logging successful usage"""
        mock_db = MagicMock()
        mock_db.log_usage.return_value = None

        log_usage(
            db=mock_db,
            session_id="test-session",
            endpoint="/api/test",
            duration_ms=150,
            success=True,
            ip_address="192.168.1.100",
        )

        mock_db.log_usage.assert_called_once_with(
            "test-session", "/api/test", 150, True, "192.168.1.100", None
        )

    def test_log_usage_failure(self):
        """Test logging failed usage with error message"""
        mock_db = MagicMock()
        mock_db.log_usage.return_value = None

        log_usage(
            db=mock_db,
            session_id="test-session",
            endpoint="/api/test",
            duration_ms=200,
            success=False,
            ip_address="192.168.1.100",
            error_message="Test error",
        )

        mock_db.log_usage.assert_called_once_with(
            "test-session", "/api/test", 200, False, "192.168.1.100", "Test error"
        )

    def test_log_usage_database_error(self):
        """Test logging usage when database fails"""
        mock_db = MagicMock()
        mock_db.log_usage.side_effect = Exception("Database error")

        # Should not raise exception
        log_usage(
            db=mock_db,
            session_id="test-session",
            endpoint="/api/test",
            duration_ms=150,
            success=True,
            ip_address="192.168.1.100",
        )


class TestSessionActivity:
    """Test session activity updates"""

    def test_update_session_activity(self):
        """Test updating session activity"""
        mock_db = MagicMock()
        mock_db.update_session_activity.return_value = None

        update_session_activity(
            db=mock_db, session_id="test-session", ip_address="192.168.1.100"
        )

        mock_db.update_session_activity.assert_called_once_with(
            "test-session", "192.168.1.100"
        )

    def test_update_session_activity_database_error(self):
        """Test updating session activity when database fails"""
        mock_db = MagicMock()
        mock_db.update_session_activity.side_effect = Exception("Database error")

        # Should not raise exception
        update_session_activity(
            db=mock_db, session_id="test-session", ip_address="192.168.1.100"
        )


class TestUtilityIntegration:
    """Integration tests for utilities"""

    def test_full_session_workflow(self):
        """Test complete session workflow"""
        mock_db = MagicMock()
        mock_db.get_rate_limit.return_value = None

        # Test rate limiting
        result, rate_info = check_rate_limit(mock_db, "test-key")
        assert result is True
        assert rate_info["limit"] == 100

        # Test session activity update
        update_session_activity(mock_db, "test-session", "192.168.1.1")
        mock_db.update_session_activity.assert_called_once_with(
            "test-session", "192.168.1.1"
        )

        # Test usage logging
        log_usage(mock_db, "test-session", "/test", 100, True, "192.168.1.1")
        mock_db.log_usage.assert_called_once_with(
            "test-session", "/test", 100, True, "192.168.1.1", None
        )

    def test_settings_integration(self):
        """Test settings integration with rate limiting"""
        mock_db = MagicMock()
        mock_db.get_rate_limit.return_value = None

        result, rate_info = check_rate_limit(mock_db, "test-key")
        assert result is True
        assert rate_info["limit"] == 100  # Default from settings

    def test_error_handling_integration(self):
        """Test error handling across utilities"""
        mock_db = MagicMock()
        mock_db.get_rate_limit.side_effect = Exception("Database error")
        mock_db.update_session_activity.side_effect = Exception("Database error")
        mock_db.log_usage.side_effect = Exception("Database error")

        # All should handle errors gracefully
        result, rate_info = check_rate_limit(mock_db, "test-key")
        assert result is True
        assert "limit" in rate_info

        update_session_activity(mock_db, "test-session", "192.168.1.100")
        # Should not raise exception

        log_usage(
            db=mock_db,
            session_id="test-session",
            endpoint="/api/test",
            duration_ms=150,
            success=True,
            ip_address="192.168.1.100",
        )
        # Should not raise exception


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_session_id_edge_cases(self):
        """Test session ID generation edge cases"""
        mock_request = MagicMock()
        mock_request.cookies = {}

        # Generate multiple session IDs
        session_ids = set()
        for _ in range(100):
            session_id = get_session_id(mock_request)
            session_ids.add(session_id)

        # All should be unique
        assert len(session_ids) == 100

    def test_ip_address_edge_cases(self):
        """Test IP address extraction edge cases"""
        # Test with empty headers
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {}

        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.100"

        # Test with malformed headers
        mock_request.headers = {"X-Forwarded-For": "invalid-ip, 192.168.1.100"}

        ip = get_client_ip(mock_request)
        assert ip == "invalid-ip"  # Should return first value even if invalid

    def test_rate_limit_edge_cases(self):
        """Test rate limiting edge cases"""
        mock_db = MagicMock()

        # Test with None database
        with patch("app.utils.settings.Settings") as mock_settings:
            mock_settings.return_value.rate_limit_requests = 100
            mock_settings.return_value.rate_limit_window = 60

            result, rate_info = check_rate_limit(None, "test-key")
            assert result is True  # Should allow when database is None
            assert "limit" in rate_info

    def test_settings_edge_cases(self):
        """Test settings edge cases"""
        # Test with invalid environment values
        with patch.dict(os.environ, {"DATABASE_TTL": "invalid"}):
            settings = Settings()
            # Should fall back to default when invalid
            assert settings.database_ttl == 3600 * 24  # 1 day default

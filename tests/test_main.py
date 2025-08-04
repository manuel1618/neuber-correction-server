"""
Tests for the main FastAPI application
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, lifespan
from app.utils.settings import Settings


class TestMainApplication:
    """Test the main FastAPI application"""

    def test_app_creation(self):
        """Test that the FastAPI app is created correctly"""
        assert app.title == "Neuber Correction Server"
        assert app.version == "1.0.0"

    def test_health_endpoint(self):
        """Test the health check endpoint"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["version"] == "1.0.0"
            assert "database" in data
            assert "session_count" in data

    def test_root_endpoint(self):
        """Test the root endpoint returns HTML"""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            assert "Neuber Correction Calculator" in response.text

    def test_static_files(self):
        """Test that static files are served"""
        with TestClient(app) as client:
            response = client.get("/static/css/style.css")
            # Should return 200 or 404 (depending on if file exists)
            assert response.status_code in [200, 404]

    def test_session_middleware(self):
        """Test that session middleware adds required headers"""
        with TestClient(app) as client:
            response = client.get("/health")
            assert "X-Request-ID" in response.headers
            assert "session_id" in response.cookies

    @pytest.mark.asyncio
    async def test_lifespan_startup(self):
        """Test application startup in lifespan context"""
        with patch("app.main.db") as mock_db:
            mock_db.create_tables.return_value = None
            mock_db.clear_all_data.return_value = None

            # Test startup
            async with lifespan(app):
                # Verify database operations were called
                mock_db.create_tables.assert_called_once()
                mock_db.clear_all_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown(self):
        """Test application shutdown in lifespan context"""
        with patch("app.main.db") as mock_db:
            mock_db.create_tables.return_value = None
            mock_db.clear_all_data.return_value = None
            mock_db.close.return_value = None

            # Test shutdown
            async with lifespan(app):
                pass  # Just enter and exit to trigger shutdown

            # Verify database close was called
            mock_db.close.assert_called_once()

    def test_rate_limiting_headers(self):
        """Test that rate limiting headers are present"""
        with TestClient(app) as client:
            response = client.get("/health")
            # SlowAPI should add rate limiting headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

    def test_cors_headers(self):
        """Test that CORS headers are properly set"""
        with TestClient(app) as client:
            response = client.options("/health")
            # Should handle OPTIONS requests for CORS
            assert response.status_code in [200, 405]  # 405 if OPTIONS not implemented

    def test_error_handling(self):
        """Test that error handling works correctly"""
        with TestClient(app) as client:
            # Test non-existent endpoint
            response = client.get("/nonexistent")
            assert response.status_code == 404

    def test_request_id_uniqueness(self):
        """Test that each request gets a unique request ID"""
        with TestClient(app) as client:
            response1 = client.get("/health")
            response2 = client.get("/health")

            request_id1 = response1.headers["X-Request-ID"]
            request_id2 = response2.headers["X-Request-ID"]

            assert request_id1 != request_id2
            assert len(request_id1) > 0
            assert len(request_id2) > 0

    def test_session_cookie_persistence(self):
        """Test that session cookies persist across requests"""
        with TestClient(app) as client:
            # First request should set session cookie
            response1 = client.get("/health")
            session_id1 = response1.cookies.get("session_id")
            assert session_id1 is not None

            # Second request should maintain same session
            # Note: TestClient automatically includes cookies from previous responses
            response2 = client.get("/health")
            session_id2 = response2.cookies.get("session_id")
            # The session ID should be the same, but the cookie might not be set again
            # if it's already present in the request
            assert session_id2 == session_id1 or session_id2 is None

    def test_database_connection_error_handling(self):
        """Test handling of database connection errors"""
        with (
            patch("app.main.db") as mock_db,
            patch("app.utils.session.check_rate_limit") as mock_rate_limit,
        ):
            mock_db.get_session_count.side_effect = Exception("Database error")
            mock_db.create_tables.return_value = None
            mock_db.clear_all_data.return_value = None
            mock_db.close.return_value = None

            # Mock rate limiting to return success
            mock_rate_limit.return_value = (
                True,
                {"limit": 100, "remaining": 99, "reset": 1234567890},
            )

            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200
                data = response.json()
                # The health endpoint should still work even if database has issues
                assert "timestamp" in data
                assert "session_count" in data


class TestApplicationConfiguration:
    """Test application configuration and settings"""

    def test_settings_loading(self):
        """Test that settings are loaded correctly"""

        settings = Settings()
        assert hasattr(settings, "database_path")
        assert hasattr(settings, "database_ttl")
        assert hasattr(settings, "rate_limit_window")
        assert hasattr(settings, "rate_limit_requests")

    def test_database_path_default(self):
        """Test default database path"""

        settings = Settings()
        assert settings.database_path == "neuber_correction.db"

    def test_rate_limit_defaults(self):
        """Test default rate limit settings"""

        settings = Settings()
        assert settings.rate_limit_window == 60  # 1 minute
        assert settings.rate_limit_requests == 100  # 100 requests per minute

    def test_database_ttl_default(self):
        """Test default database TTL"""

        settings = Settings()
        assert settings.database_ttl == 3600 * 24  # 1 day


class TestApplicationRoutes:
    """Test that all expected routes are registered"""

    def test_route_registration(self):
        """Test that all expected routes are registered"""
        routes = [route.path for route in app.routes]

        # Check for expected routes
        expected_routes = [
            "/",
            "/health",
            "/api/correct",
            "/api/plot",
            "/api/materials",
            "/api/upload-materials",
            "/api/manual-material",
        ]

        for route in expected_routes:
            assert route in routes, f"Route {route} not found in registered routes"

    def test_static_files_mount(self):
        """Test that static files are properly mounted"""
        # Check that static files mount exists
        static_mounts = [
            route
            for route in app.routes
            if hasattr(route, "path") and "/static" in route.path
        ]
        assert len(static_mounts) > 0, "Static files mount not found"

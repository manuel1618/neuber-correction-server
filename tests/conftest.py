"""
Pytest configuration and shared fixtures
"""

import os
import tempfile
import time
from unittest.mock import MagicMock

import matplotlib
import pytest

# Configure matplotlib to use non-interactive backend for testing
matplotlib.use("Agg")

from app.db.sqlite3 import SQLiteDatabase


@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    yield db_path

    # Cleanup - wait a bit to ensure connections are closed
    if os.path.exists(db_path):
        try:
            # Try to delete the file
            os.unlink(db_path)
        except PermissionError:
            # If file is still in use, wait a bit and try again
            time.sleep(0.1)
            try:
                os.unlink(db_path)
            except PermissionError:
                # If still can't delete, just leave it - it will be cleaned up later
                pass


@pytest.fixture
def test_db(temp_db_path):
    """Create a test database instance"""
    db = SQLiteDatabase(temp_db_path)
    db.create_tables()
    yield db
    db.close()


@pytest.fixture
def mock_request():
    """Create a mock request object for testing"""
    request = MagicMock()
    request.cookies = {}
    request.client.host = "127.0.0.1"
    request.headers = {}
    return request


@pytest.fixture
def sample_materials():
    """Sample materials for testing"""
    return {
        "materials": [
            {
                "id": "test_steel",
                "name": "Test Steel",
                "properties": {"fty": 350, "ftu": 500, "E": 210000, "epsilon_u": 0.15},
            },
            {
                "id": "test_aluminum",
                "name": "Test Aluminum",
                "properties": {"fty": 200, "ftu": 280, "E": 70000, "epsilon_u": 0.12},
            },
        ]
    }


@pytest.fixture
def sample_correction_request():
    """Sample correction request for testing"""
    return {
        "material_name": "test_steel",
        "stress_values": [400.0, 500.0, 600.0],
        "custom_material": {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
        },
    }


@pytest.fixture
def sample_plot_request():
    """Sample plot request for testing"""
    return {
        "material_name": "test_steel",
        "stress_value": "400.0",
        "custom_material": {
            "yield_strength": 350.0,
            "sigma_u": 500.0,
            "elastic_mod": 210000.0,
            "eps_u": 0.15,
        },
    }


@pytest.fixture
def mock_db():
    """Create a mock database for testing"""
    db = MagicMock()
    db.get_session_count.return_value = 0
    db.get_rate_limit.return_value = None
    db.create_rate_limit.return_value = None
    db.update_rate_limit.return_value = None
    db.log_usage.return_value = None
    db.update_session_activity.return_value = None
    return db


# Pytest configuration
def pytest_configure(config):
    """Configure pytest"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    for item in items:
        # Mark tests based on their location
        if "test_main.py" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "test_api_routes.py" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)

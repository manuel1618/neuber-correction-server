"""
Settings for the application
"""

import os


class Settings:
    """Settings for the application"""

    def __init__(self):
        # Database settings
        self.database_path: str = os.getenv("DATABASE_PATH", "neuber_correction.db")
        self.database_ttl: int = self._get_int_env(
            "DATABASE_TTL", 3600 * 24
        )  # 1 day (24 hours)

        # Rate limiting settings
        self.rate_limit_window: int = self._get_int_env(
            "RATE_LIMIT_WINDOW", 60
        )  # 1 minute
        self.rate_limit_requests: int = self._get_int_env(
            "RATE_LIMIT_REQUESTS", 100
        )  # 100 requests per minute

    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer from environment variable with fallback to default"""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

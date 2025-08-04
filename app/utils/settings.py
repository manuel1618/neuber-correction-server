"""
Settings for the application
"""


class Settings:
    """Settings for the application"""

    database_path: str = "neuber_correction.db"
    database_ttl: int = 3600 * 24  # 1 day (24 hours)

    # Simplified rate limiting - generous limits for all functions
    rate_limit_window: int = 60  # 1 minute
    rate_limit_requests: int = 100  # 100 requests per minute (generous limit)

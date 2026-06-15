# rate_limit_config.py
"""
Configuration file for rate limiting settings.
"""

# Default rate limit for all endpoints
DEFAULT_RATE_LIMIT = 60  # requests
DEFAULT_RATE_WINDOW = 60  # seconds (1 minute)

# Rate limit for admin users
ADMIN_RATE_LIMIT = 200  # requests
ADMIN_RATE_WINDOW = 60  # seconds

# Custom rate limits for specific endpoints
# Format: 'endpoint': (requests_limit, window_in_seconds)
ENDPOINT_LIMITS = {
    # Messaging endpoints
    'channel-message': (30, 60),  # 30 channel messages per minute
    'direct-message': (20, 60),   # 20 DMs per minute
    'embed-message': (15, 60),    # 15 embeds per minute
    
    # API key management
    'keys': (10, 60),             # 10 key operations per minute
    
    # Activity and stats
    'activity': (5, 60),          # 5 activity queries per minute
    'activity/stats': (5, 60),    # 5 stats queries per minute
    
    # Health check (can be called more frequently)
    'health': (60, 60),           # 60 health checks per minute
}
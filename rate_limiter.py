import time
import logging
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger("rate_limiter")

class RateLimiter:
    """
    A simple rate limiter that limits requests per API key.
    """
    
    def __init__(self, 
                 default_limit=60,          # Default requests per window
                 default_window=60,         # Default window in seconds (1 minute)
                 admin_limit=120,           # Admin requests per window
                 admin_window=60,           # Admin window in seconds
                 endpoint_limits=None):     # Custom limits for specific endpoints
        
        self.default_limit = default_limit
        self.default_window = default_window
        self.admin_limit = admin_limit
        self.admin_window = admin_window
        
        # Set custom limits for specific endpoints
        self.endpoint_limits = endpoint_limits or {
            # Format: 'endpoint': (limit, window_in_seconds)
            'channel-message': (30, 60),      # 30 channel messages per minute
            'direct-message': (20, 60),       # 20 DMs per minute
            'embed-message': (15, 60),        # 15 embeds per minute
            'keys': (10, 60)                  # 10 key operations per minute
        }
        
        # Store request timestamps per key and endpoint
        # Format: {api_key: {endpoint: [timestamp1, timestamp2, ...]}}
        self.requests = defaultdict(lambda: defaultdict(list))
        
        # Store the last reset time for each API key
        self.last_reset = {}

    def is_rate_limited(self, api_key, endpoint=None, is_admin=False):
        """
        Check if the request should be rate limited.
        
        Args:
            api_key: The API key making the request
            endpoint: The endpoint being requested (optional)
            is_admin: Whether the API key belongs to an admin
            
        Returns:
            tuple: (is_limited, remaining, reset_in_seconds)
        """
        now = time.time()
        current_time = datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine the appropriate limit and window
        if is_admin:
            limit = self.admin_limit
            window = self.admin_window
        elif endpoint and endpoint in self.endpoint_limits:
            limit, window = self.endpoint_limits[endpoint]
        else:
            limit = self.default_limit
            window = self.default_window
        
        # Get the list of requests for this key and endpoint
        if endpoint:
            requests_list = self.requests[api_key][endpoint]
        else:
            # Aggregate all requests for this key if no endpoint is specified
            requests_list = []
            for endpoint_requests in self.requests[api_key].values():
                requests_list.extend(endpoint_requests)
        
        # Remove timestamps outside the window
        current_requests = [ts for ts in requests_list if now - ts < window]
        
        # Update the list with only current requests
        if endpoint:
            self.requests[api_key][endpoint] = current_requests
        else:
            # This is a simplified approach - in practice, you might want a more 
            # sophisticated way to prune old requests across all endpoints
            for e in list(self.requests[api_key].keys()):
                self.requests[api_key][e] = [ts for ts in self.requests[api_key][e] if now - ts < window]
        
        # Calculate reset time (when the oldest request will expire)
        if current_requests:
            oldest_request = min(current_requests)
            reset_in = max(0, window - (now - oldest_request))
            reset_time = datetime.fromtimestamp(now + reset_in).strftime('%Y-%m-%d %H:%M:%S')
        else:
            reset_in = 0
            reset_time = current_time
        
        # Calculate remaining requests
        remaining = max(0, limit - len(current_requests))
        
        # Check if limit is exceeded
        is_limited = len(current_requests) >= limit
        
        # Record this request if not limited
        if not is_limited:
            if endpoint:
                self.requests[api_key][endpoint].append(now)
            else:
                # For global rate limiting, we need to track the request somewhere
                self.requests[api_key]['global'] = self.requests[api_key].get('global', []) + [now]
        
        # Log the rate limit check
        if is_limited:
            logger.warning(f"Rate limit exceeded for key {api_key[:5]}... on {endpoint or 'global'}, " +
                          f"limit: {limit}, window: {window}s, reset at: {reset_time}")
        else:
            logger.debug(f"Rate limit check for key {api_key[:5]}... on {endpoint or 'global'}, " +
                        f"remaining: {remaining}/{limit}, reset in: {reset_in:.1f}s")
        
        return is_limited, remaining, reset_in
    
    def get_headers(self, api_key, endpoint=None, is_admin=False):
        """
        Get rate limiting headers for a response.
        
        Args:
            api_key: The API key that made the request
            endpoint: The endpoint that was requested (optional)
            is_admin: Whether the API key belongs to an admin
            
        Returns:
            dict: Headers to be included in the response
        """
        _, remaining, reset_in = self.is_rate_limited(api_key, endpoint, is_admin)
        
        return {
            "X-RateLimit-Limit": str(self.admin_limit if is_admin else 
                                     self.endpoint_limits.get(endpoint, (self.default_limit, 0))[0]),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(reset_in))
        }
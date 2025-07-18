"""
Rate limiting implementation for API endpoints
"""

import time
from typing import Dict, Tuple, List, Optional
import threading
from collections import defaultdict, deque
import logging
from backend.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter implementation using sliding window algorithm
    
    This class provides methods to check if a request should be rate limited
    based on the number of requests in a given time window.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RateLimiter, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Store request timestamps by user_id and endpoint
        # Format: {(user_id, endpoint): deque([timestamp1, timestamp2, ...])}
        self._request_history = defaultdict(lambda: deque(maxlen=100))
        
        # Rate limit configurations by endpoint
        # Format: {endpoint: (requests_per_minute, window_size_seconds)}
        self._rate_limits = {
            "pdf_export": (settings.PDF_EXPORT_RATE_LIMIT, 60)  # 10 requests per minute by default
        }
        
        self._initialized = True
        logger.info("Rate limiter initialized")
    
    def is_rate_limited(self, user_id: str, endpoint: str) -> Tuple[bool, Optional[int]]:
        """
        Check if a request should be rate limited
        
        Args:
            user_id: ID of the user making the request
            endpoint: Endpoint identifier (e.g., "pdf_export")
            
        Returns:
            Tuple of (is_limited, retry_after_seconds)
            - is_limited: True if request should be rate limited
            - retry_after_seconds: Seconds until rate limit expires, or None if not limited
        """
        with self._lock:
            # Get rate limit configuration for endpoint
            if endpoint not in self._rate_limits:
                # No rate limit for this endpoint
                return False, None
            
            requests_per_minute, window_size = self._rate_limits[endpoint]
            
            # Get request history for this user and endpoint
            key = (user_id, endpoint)
            history = self._request_history[key]
            
            # Current time
            current_time = time.time()
            
            # Remove expired entries (older than window_size)
            while history and history[0] < current_time - window_size:
                history.popleft()
            
            # Check if rate limit is exceeded
            if len(history) >= requests_per_minute:
                # Calculate time until oldest request expires
                oldest_request = history[0]
                retry_after = int(oldest_request + window_size - current_time) + 1
                
                logger.warning(f"Rate limit exceeded for user {user_id} on {endpoint}. "
                              f"Retry after {retry_after} seconds.")
                
                return True, retry_after
            
            # Add current request to history
            history.append(current_time)
            
            # Not rate limited
            return False, None
    
    def update_rate_limit(self, endpoint: str, requests_per_minute: int, window_size: int = 60) -> None:
        """
        Update rate limit configuration for an endpoint
        
        Args:
            endpoint: Endpoint identifier
            requests_per_minute: Maximum requests allowed in the window
            window_size: Window size in seconds (default: 60)
        """
        with self._lock:
            self._rate_limits[endpoint] = (requests_per_minute, window_size)
            logger.info(f"Updated rate limit for {endpoint}: {requests_per_minute} requests per {window_size} seconds")
    
    def get_rate_limit_config(self, endpoint: str) -> Optional[Tuple[int, int]]:
        """
        Get rate limit configuration for an endpoint
        
        Args:
            endpoint: Endpoint identifier
            
        Returns:
            Tuple of (requests_per_minute, window_size_seconds) or None if not configured
        """
        with self._lock:
            return self._rate_limits.get(endpoint)
    
    def clear_history(self, user_id: Optional[str] = None, endpoint: Optional[str] = None) -> None:
        """
        Clear rate limit history
        
        Args:
            user_id: Optional user ID to clear history for
            endpoint: Optional endpoint to clear history for
        """
        with self._lock:
            if user_id and endpoint:
                # Clear specific user and endpoint
                key = (user_id, endpoint)
                if key in self._request_history:
                    self._request_history[key].clear()
            elif user_id:
                # Clear all endpoints for user
                for key in list(self._request_history.keys()):
                    if key[0] == user_id:
                        self._request_history[key].clear()
            elif endpoint:
                # Clear all users for endpoint
                for key in list(self._request_history.keys()):
                    if key[1] == endpoint:
                        self._request_history[key].clear()
            else:
                # Clear all history
                self._request_history.clear()


# Global instance for easy access
rate_limiter = RateLimiter()
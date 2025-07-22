"""
Rate limiting utilities for API endpoints.

This module provides rate limiting functionality to prevent abuse
of resource-intensive operations like document exports.
"""

import logging
import time
from typing import Dict, Any, Optional, Tuple
import asyncio
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter for API endpoints.
    
    This class tracks and limits the frequency of operations
    to prevent abuse and ensure fair resource allocation.
    """
    
    # In-memory storage of user request counts
    _user_requests: Dict[str, Dict[str, Any]] = {}
    
    # Default rate limits
    DEFAULT_LIMITS = {
        "pdf_export": {"count": 10, "period": 3600},  # 10 per hour
        "docx_export": {"count": 10, "period": 3600},  # 10 per hour
        "default": {"count": 60, "period": 3600}       # 60 per hour
    }
    
    @classmethod
    async def check_rate_limit(
        cls,
        user_id: str,
        operation_type: str,
        custom_limits: Optional[Dict[str, Dict[str, int]]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if an operation would exceed rate limits.
        
        Args:
            user_id: ID of the user performing the operation
            operation_type: Type of operation (e.g., 'pdf_export')
            custom_limits: Optional custom rate limits
            
        Returns:
            Tuple[bool, Dict]: (allowed, limit_info)
            - allowed: Whether the operation is allowed
            - limit_info: Information about the rate limit
        """
        # Get the appropriate limit
        limits = custom_limits or cls.DEFAULT_LIMITS
        limit_config = limits.get(operation_type, limits.get("default"))
        
        max_count = limit_config["count"]
        period = limit_config["period"]
        
        # Get or create user tracking data
        user_key = f"{user_id}:{operation_type}"
        if user_key not in cls._user_requests:
            cls._user_requests[user_key] = {
                "count": 0,
                "period_start": time.time(),
                "requests": []
            }
        
        user_data = cls._user_requests[user_key]
        
        # Check if period has reset
        current_time = time.time()
        if current_time - user_data["period_start"] > period:
            # Reset counters for new period
            user_data["count"] = 0
            user_data["period_start"] = current_time
            user_data["requests"] = []
        
        # Clean up old requests
        user_data["requests"] = [
            req for req in user_data["requests"]
            if current_time - req["timestamp"] <= period
        ]
        
        # Update count based on actual requests within period
        user_data["count"] = len(user_data["requests"])
        
        # Check if limit exceeded
        allowed = user_data["count"] < max_count
        
        # Prepare limit info
        limit_info = {
            "allowed": allowed,
            "limit": max_count,
            "remaining": max(0, max_count - user_data["count"]),
            "reset": user_data["period_start"] + period,
            "reset_in_seconds": int(user_data["period_start"] + period - current_time)
        }
        
        # If allowed, increment counter
        if allowed:
            request_id = str(uuid.uuid4())
            user_data["requests"].append({
                "id": request_id,
                "timestamp": current_time,
                "operation_type": operation_type
            })
            user_data["count"] += 1
            
            # Update remaining count
            limit_info["remaining"] = max(0, max_count - user_data["count"])
        
        return allowed, limit_info
    
    @classmethod
    def record_operation(
        cls,
        user_id: str,
        operation_type: str,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Record a completed operation for rate limiting purposes.
        
        Args:
            user_id: ID of the user who performed the operation
            operation_type: Type of operation (e.g., 'pdf_export')
            success: Whether the operation was successful
            metadata: Optional additional metadata about the operation
        """
        user_key = f"{user_id}:{operation_type}"
        if user_key not in cls._user_requests:
            return
        
        # Find the most recent request and update it
        user_data = cls._user_requests[user_key]
        if user_data["requests"]:
            latest_request = user_data["requests"][-1]
            latest_request["success"] = success
            latest_request["completion_time"] = time.time()
            
            if metadata:
                latest_request["metadata"] = metadata
    
    @classmethod
    async def cleanup_old_data(cls):
        """Background task to clean up old rate limit data."""
        while True:
            try:
                current_time = time.time()
                keys_to_remove = []
                
                for user_key, user_data in cls._user_requests.items():
                    # If period has expired and no recent requests, remove the entry
                    period = cls.DEFAULT_LIMITS.get(
                        user_key.split(":")[-1], 
                        cls.DEFAULT_LIMITS["default"]
                    )["period"]
                    
                    if current_time - user_data["period_start"] > period * 2:
                        # Check if there are any recent requests
                        has_recent = False
                        for req in user_data["requests"]:
                            if current_time - req["timestamp"] <= period:
                                has_recent = True
                                break
                        
                        if not has_recent:
                            keys_to_remove.append(user_key)
                
                # Remove old entries
                for key in keys_to_remove:
                    cls._user_requests.pop(key, None)
                
                # Sleep for a while before next cleanup
                await asyncio.sleep(3600)  # 1 hour
                
            except Exception as e:
                logger.error(f"Error in rate limiter cleanup task: {e}")
                await asyncio.sleep(300)  # Retry after 5 minutes on error
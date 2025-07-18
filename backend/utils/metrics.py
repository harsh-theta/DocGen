"""
Metrics collection and monitoring for PDF generation performance
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import threading
import json
import os
from collections import deque

logger = logging.getLogger(__name__)

class PDFMetricsCollector:
    """
    Collects and stores metrics about PDF generation performance
    
    This class provides methods to track PDF generation metrics such as:
    - Generation time
    - File sizes
    - Success/failure rates
    - Resource usage
    
    Metrics are stored in memory with periodic flushing to disk
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PDFMetricsCollector, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._metrics_data = {
            "pdf_generation": {
                "count": 0,
                "success_count": 0,
                "failure_count": 0,
                "total_time_ms": 0,
                "avg_time_ms": 0,
                "max_time_ms": 0,
                "min_time_ms": float('inf'),
                "total_size_bytes": 0,
                "avg_size_bytes": 0,
                "max_size_bytes": 0,
            },
            "errors": {
                "count_by_type": {},
                "recent_errors": deque(maxlen=100)  # Store last 100 errors
            },
            "rate_limiting": {
                "total_limited_requests": 0,
                "limited_users": set()
            }
        }
        
        # Recent generation times for percentile calculations
        self._recent_generation_times = deque(maxlen=1000)  # Last 1000 generation times
        
        # Path for metrics storage
        self._metrics_file = os.path.join("logs", "pdf_metrics.json")
        os.makedirs(os.path.dirname(self._metrics_file), exist_ok=True)
        
        # Load existing metrics if available
        self._load_metrics()
        
        # Set up periodic flushing
        self._last_flush_time = time.time()
        self._flush_interval = 300  # 5 minutes
        
        self._initialized = True
        logger.info("PDF metrics collector initialized")
    
    def _load_metrics(self):
        """Load metrics from disk if available"""
        try:
            if os.path.exists(self._metrics_file):
                with open(self._metrics_file, 'r') as f:
                    stored_metrics = json.load(f)
                    
                    # Update metrics but keep runtime structures
                    for category in ["pdf_generation", "errors"]:
                        if category in stored_metrics:
                            for key, value in stored_metrics[category].items():
                                if key != "recent_errors" and key in self._metrics_data[category]:
                                    self._metrics_data[category][key] = value
                    
                    # Special handling for rate limiting since it has a set
                    if "rate_limiting" in stored_metrics:
                        self._metrics_data["rate_limiting"]["total_limited_requests"] = stored_metrics["rate_limiting"].get(
                            "total_limited_requests", 0)
                        # Convert list back to set
                        self._metrics_data["rate_limiting"]["limited_users"] = set(
                            stored_metrics["rate_limiting"].get("limited_users", []))
                    
                    logger.info(f"Loaded metrics from {self._metrics_file}")
        except Exception as e:
            logger.warning(f"Failed to load metrics from disk: {str(e)}")
    
    def _flush_metrics(self, force=False):
        """Flush metrics to disk if interval has passed or force is True"""
        current_time = time.time()
        if force or (current_time - self._last_flush_time) >= self._flush_interval:
            try:
                # Prepare metrics for serialization
                serializable_metrics = {
                    "pdf_generation": self._metrics_data["pdf_generation"].copy(),
                    "errors": {
                        "count_by_type": self._metrics_data["errors"]["count_by_type"].copy(),
                        "recent_errors": list(self._metrics_data["errors"]["recent_errors"])
                    },
                    "rate_limiting": {
                        "total_limited_requests": self._metrics_data["rate_limiting"]["total_limited_requests"],
                        "limited_users": list(self._metrics_data["rate_limiting"]["limited_users"])
                    },
                    "last_updated": datetime.now().isoformat()
                }
                
                with open(self._metrics_file, 'w') as f:
                    json.dump(serializable_metrics, f, indent=2)
                
                self._last_flush_time = current_time
                logger.debug(f"Metrics flushed to {self._metrics_file}")
            except Exception as e:
                logger.error(f"Failed to flush metrics to disk: {str(e)}")
    
    def record_generation_attempt(self, start_time: float, success: bool, 
                                 pdf_size: Optional[int] = None, 
                                 error_type: Optional[str] = None,
                                 error_message: Optional[str] = None,
                                 document_id: Optional[str] = None,
                                 user_id: Optional[str] = None) -> None:
        """
        Record metrics for a PDF generation attempt
        
        Args:
            start_time: Start time of generation (from time.time())
            success: Whether generation was successful
            pdf_size: Size of generated PDF in bytes (if successful)
            error_type: Type of error if generation failed
            error_message: Error message if generation failed
            document_id: ID of the document being processed
            user_id: ID of the user who requested the generation
        """
        with self._lock:
            end_time = time.time()
            generation_time_ms = int((end_time - start_time) * 1000)
            
            # Update general metrics
            self._metrics_data["pdf_generation"]["count"] += 1
            
            # Store generation time for percentile calculations
            self._recent_generation_times.append(generation_time_ms)
            
            if success:
                # Update success metrics
                self._metrics_data["pdf_generation"]["success_count"] += 1
                self._metrics_data["pdf_generation"]["total_time_ms"] += generation_time_ms
                
                # Update time stats
                if generation_time_ms > self._metrics_data["pdf_generation"]["max_time_ms"]:
                    self._metrics_data["pdf_generation"]["max_time_ms"] = generation_time_ms
                
                if generation_time_ms < self._metrics_data["pdf_generation"]["min_time_ms"]:
                    self._metrics_data["pdf_generation"]["min_time_ms"] = generation_time_ms
                
                # Calculate new average time
                success_count = self._metrics_data["pdf_generation"]["success_count"]
                if success_count > 0:
                    self._metrics_data["pdf_generation"]["avg_time_ms"] = (
                        self._metrics_data["pdf_generation"]["total_time_ms"] / success_count
                    )
                
                # Update size stats if provided
                if pdf_size is not None and pdf_size > 0:
                    self._metrics_data["pdf_generation"]["total_size_bytes"] += pdf_size
                    
                    if pdf_size > self._metrics_data["pdf_generation"]["max_size_bytes"]:
                        self._metrics_data["pdf_generation"]["max_size_bytes"] = pdf_size
                    
                    # Calculate new average size
                    self._metrics_data["pdf_generation"]["avg_size_bytes"] = (
                        self._metrics_data["pdf_generation"]["total_size_bytes"] / success_count
                    )
            else:
                # Update failure metrics
                self._metrics_data["pdf_generation"]["failure_count"] += 1
                
                # Record error information
                if error_type:
                    self._metrics_data["errors"]["count_by_type"][error_type] = (
                        self._metrics_data["errors"]["count_by_type"].get(error_type, 0) + 1
                    )
                
                # Add to recent errors
                error_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "error_type": error_type or "unknown",
                    "message": error_message or "No error message provided",
                    "generation_time_ms": generation_time_ms
                }
                
                if document_id:
                    error_entry["document_id"] = document_id
                
                if user_id:
                    error_entry["user_id"] = user_id
                
                self._metrics_data["errors"]["recent_errors"].append(error_entry)
            
            # Flush metrics periodically
            self._flush_metrics()
    
    def record_rate_limit_event(self, user_id: str) -> None:
        """
        Record a rate limiting event
        
        Args:
            user_id: ID of the user who was rate limited
        """
        with self._lock:
            self._metrics_data["rate_limiting"]["total_limited_requests"] += 1
            self._metrics_data["rate_limiting"]["limited_users"].add(user_id)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current metrics
        
        Returns:
            Dict containing metrics summary
        """
        with self._lock:
            # Calculate percentiles if we have data
            percentiles = {}
            if self._recent_generation_times:
                sorted_times = sorted(self._recent_generation_times)
                total = len(sorted_times)
                
                percentiles = {
                    "p50": sorted_times[int(total * 0.5)] if total > 0 else 0,
                    "p90": sorted_times[int(total * 0.9)] if total > 0 else 0,
                    "p95": sorted_times[int(total * 0.95)] if total > 0 else 0,
                    "p99": sorted_times[int(total * 0.99)] if total > 0 else 0
                }
            
            # Create a copy of metrics for the summary
            summary = {
                "pdf_generation": {
                    "count": self._metrics_data["pdf_generation"]["count"],
                    "success_count": self._metrics_data["pdf_generation"]["success_count"],
                    "failure_count": self._metrics_data["pdf_generation"]["failure_count"],
                    "success_rate": (
                        self._metrics_data["pdf_generation"]["success_count"] / 
                        self._metrics_data["pdf_generation"]["count"] * 100
                    ) if self._metrics_data["pdf_generation"]["count"] > 0 else 0,
                    "avg_time_ms": self._metrics_data["pdf_generation"]["avg_time_ms"],
                    "max_time_ms": self._metrics_data["pdf_generation"]["max_time_ms"],
                    "min_time_ms": (
                        self._metrics_data["pdf_generation"]["min_time_ms"] 
                        if self._metrics_data["pdf_generation"]["min_time_ms"] != float('inf') 
                        else 0
                    ),
                    "avg_size_kb": (
                        self._metrics_data["pdf_generation"]["avg_size_bytes"] / 1024
                    ) if self._metrics_data["pdf_generation"]["avg_size_bytes"] > 0 else 0,
                    "percentiles": percentiles
                },
                "errors": {
                    "total_count": self._metrics_data["pdf_generation"]["failure_count"],
                    "top_errors": sorted(
                        self._metrics_data["errors"]["count_by_type"].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:5]  # Top 5 errors
                },
                "rate_limiting": {
                    "total_limited_requests": self._metrics_data["rate_limiting"]["total_limited_requests"],
                    "unique_limited_users": len(self._metrics_data["rate_limiting"]["limited_users"])
                },
                "timestamp": datetime.now().isoformat()
            }
            
            return summary
    
    def reset_metrics(self) -> None:
        """Reset all metrics (mainly for testing)"""
        with self._lock:
            self.__init__()
            logger.warning("PDF metrics have been reset")


# Global instance for easy access
pdf_metrics = PDFMetricsCollector()
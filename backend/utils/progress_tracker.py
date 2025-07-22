"""
Progress tracking utilities for long-running operations.

This module provides functionality to track and report progress for
long-running operations like document exports.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
import uuid
from datetime import datetime
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class ProgressTracker:
    """
    Tracks progress of long-running operations and provides status updates.
    
    This class maintains a record of operation progress that can be queried
    by clients to show progress indicators and status messages.
    """
    
    # In-memory storage of active operations
    _active_operations: Dict[str, Dict[str, Any]] = {}
    
    # Maximum time to keep completed operations in memory (seconds)
    _retention_time = 3600  # 1 hour
    
    # Path for persistent storage
    _storage_dir = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "progress"))
    
    @classmethod
    def initialize(cls, storage_dir: Optional[Path] = None, retention_time: int = 3600):
        """
        Initialize the progress tracker with configuration.
        
        Args:
            storage_dir: Directory for persistent storage
            retention_time: Time to keep completed operations in memory (seconds)
        """
        if storage_dir:
            cls._storage_dir = storage_dir
        
        # Create storage directory if it doesn't exist
        os.makedirs(cls._storage_dir, exist_ok=True)
        
        cls._retention_time = retention_time
        
        # Start background cleanup task
        asyncio.create_task(cls._cleanup_old_operations())
    
    @classmethod
    def start_operation(
        cls, 
        operation_type: str,
        user_id: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start tracking a new operation.
        
        Args:
            operation_type: Type of operation (e.g., 'pdf_export', 'docx_export')
            user_id: ID of the user performing the operation
            document_id: Optional ID of the document being processed
            metadata: Optional additional metadata about the operation
            
        Returns:
            str: Operation ID for tracking
        """
        operation_id = f"{operation_type}_{uuid.uuid4().hex}"
        
        operation_data = {
            "id": operation_id,
            "type": operation_type,
            "user_id": user_id,
            "document_id": document_id,
            "status": "started",
            "progress": 0,
            "message": f"{operation_type.replace('_', ' ').title()} started",
            "start_time": datetime.now().isoformat(),
            "last_update_time": datetime.now().isoformat(),
            "completion_time": None,
            "metadata": metadata or {},
            "steps": [],
            "current_step": None,
            "total_steps": 0,
            "errors": []
        }
        
        cls._active_operations[operation_id] = operation_data
        cls._save_operation(operation_id, operation_data)
        
        logger.info(f"Started tracking operation: {operation_id} ({operation_type})")
        return operation_id
    
    @classmethod
    def update_progress(
        cls,
        operation_id: str,
        progress: Optional[int] = None,
        status: Optional[str] = None,
        message: Optional[str] = None,
        current_step: Optional[str] = None,
        total_steps: Optional[int] = None,
        error: Optional[str] = None,
        metadata_updates: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update the progress of an operation.
        
        Args:
            operation_id: ID of the operation to update
            progress: Optional progress percentage (0-100)
            status: Optional status update ('in_progress', 'completed', 'failed', etc.)
            message: Optional user-friendly message about the current status
            current_step: Optional description of the current step
            total_steps: Optional total number of steps in the operation
            error: Optional error message if something went wrong
            metadata_updates: Optional updates to the operation metadata
            
        Returns:
            Dict: Updated operation data
        """
        if operation_id not in cls._active_operations:
            # Try to load from persistent storage
            operation_data = cls._load_operation(operation_id)
            if not operation_data:
                logger.warning(f"Attempted to update unknown operation: {operation_id}")
                return {"error": "Operation not found"}
            
            cls._active_operations[operation_id] = operation_data
        
        operation_data = cls._active_operations[operation_id]
        
        # Update fields if provided
        if progress is not None:
            operation_data["progress"] = min(max(0, progress), 100)
        
        if status:
            operation_data["status"] = status
            
            # If completed or failed, set completion time
            if status in ["completed", "failed"]:
                operation_data["completion_time"] = datetime.now().isoformat()
        
        if message:
            operation_data["message"] = message
        
        if current_step:
            operation_data["current_step"] = current_step
            
            # Add to steps history if not already there
            if current_step not in [step.get("name") for step in operation_data["steps"]]:
                operation_data["steps"].append({
                    "name": current_step,
                    "start_time": datetime.now().isoformat(),
                    "status": "in_progress"
                })
        
        if total_steps is not None:
            operation_data["total_steps"] = total_steps
        
        if error:
            operation_data["errors"].append({
                "message": error,
                "time": datetime.now().isoformat()
            })
            
            # Update status to failed if not explicitly set
            if not status:
                operation_data["status"] = "failed"
        
        if metadata_updates:
            operation_data["metadata"].update(metadata_updates)
        
        # Update last update time
        operation_data["last_update_time"] = datetime.now().isoformat()
        
        # Save to persistent storage
        cls._save_operation(operation_id, operation_data)
        
        return operation_data
    
    @classmethod
    def complete_step(
        cls,
        operation_id: str,
        step_name: str,
        success: bool = True,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark a step as completed.
        
        Args:
            operation_id: ID of the operation
            step_name: Name of the step to complete
            success: Whether the step completed successfully
            message: Optional message about the step completion
            
        Returns:
            Dict: Updated operation data
        """
        if operation_id not in cls._active_operations:
            # Try to load from persistent storage
            operation_data = cls._load_operation(operation_id)
            if not operation_data:
                logger.warning(f"Attempted to complete step for unknown operation: {operation_id}")
                return {"error": "Operation not found"}
            
            cls._active_operations[operation_id] = operation_data
        
        operation_data = cls._active_operations[operation_id]
        
        # Find the step in the steps list
        for step in operation_data["steps"]:
            if step["name"] == step_name:
                step["status"] = "completed" if success else "failed"
                step["completion_time"] = datetime.now().isoformat()
                if message:
                    step["message"] = message
                break
        
        # Update last update time
        operation_data["last_update_time"] = datetime.now().isoformat()
        
        # Save to persistent storage
        cls._save_operation(operation_id, operation_data)
        
        return operation_data
    
    @classmethod
    def complete_operation(
        cls,
        operation_id: str,
        success: bool = True,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Mark an operation as completed.
        
        Args:
            operation_id: ID of the operation to complete
            success: Whether the operation completed successfully
            message: Optional completion message
            result: Optional result data
            
        Returns:
            Dict: Final operation data
        """
        status = "completed" if success else "failed"
        
        if not message:
            operation_type = cls._get_operation_type(operation_id)
            message = (
                f"{operation_type.replace('_', ' ').title()} completed successfully"
                if success else
                f"{operation_type.replace('_', ' ').title()} failed"
            )
        
        update_data = {
            "status": status,
            "progress": 100 if success else cls._get_current_progress(operation_id),
            "message": message,
            "completion_time": datetime.now().isoformat()
        }
        
        if result:
            update_data["result"] = result
        
        operation_data = cls.update_progress(operation_id, **update_data)
        
        return operation_data
    
    @classmethod
    def get_operation_status(cls, operation_id: str) -> Dict[str, Any]:
        """
        Get the current status of an operation.
        
        Args:
            operation_id: ID of the operation to check
            
        Returns:
            Dict: Current operation data or error if not found
        """
        if operation_id in cls._active_operations:
            return cls._active_operations[operation_id]
        
        # Try to load from persistent storage
        operation_data = cls._load_operation(operation_id)
        if operation_data:
            return operation_data
        
        return {"error": "Operation not found"}
    
    @classmethod
    def get_user_operations(
        cls, 
        user_id: str,
        operation_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get operations for a specific user.
        
        Args:
            user_id: ID of the user
            operation_type: Optional filter by operation type
            status: Optional filter by status
            limit: Maximum number of operations to return
            
        Returns:
            List[Dict]: List of matching operations
        """
        # First check in-memory operations
        matching_operations = []
        
        for op_data in cls._active_operations.values():
            if op_data.get("user_id") == user_id:
                if operation_type and op_data.get("type") != operation_type:
                    continue
                    
                if status and op_data.get("status") != status:
                    continue
                    
                matching_operations.append(op_data)
        
        # Sort by last update time (newest first)
        matching_operations.sort(
            key=lambda x: x.get("last_update_time", ""),
            reverse=True
        )
        
        # If we need more, check persistent storage
        if len(matching_operations) < limit:
            # This is a simplified approach - in a real system, you'd use a database
            # with proper querying capabilities
            storage_dir = cls._storage_dir
            if storage_dir.exists():
                for file_path in storage_dir.glob("*.json"):
                    # Skip if we've reached the limit
                    if len(matching_operations) >= limit:
                        break
                        
                    try:
                        with open(file_path, "r") as f:
                            op_data = json.load(f)
                            
                        # Skip if already in memory
                        if op_data.get("id") in cls._active_operations:
                            continue
                            
                        if op_data.get("user_id") == user_id:
                            if operation_type and op_data.get("type") != operation_type:
                                continue
                                
                            if status and op_data.get("status") != status:
                                continue
                                
                            matching_operations.append(op_data)
                    except Exception as e:
                        logger.warning(f"Error loading operation from {file_path}: {e}")
        
        # Re-sort after adding from storage
        matching_operations.sort(
            key=lambda x: x.get("last_update_time", ""),
            reverse=True
        )
        
        return matching_operations[:limit]
    
    @classmethod
    def _get_operation_type(cls, operation_id: str) -> str:
        """Get the operation type from an operation ID."""
        if operation_id in cls._active_operations:
            return cls._active_operations[operation_id].get("type", "unknown")
        
        # Try to extract from the ID itself
        parts = operation_id.split("_")
        if len(parts) > 0:
            return parts[0]
        
        return "unknown"
    
    @classmethod
    def _get_current_progress(cls, operation_id: str) -> int:
        """Get the current progress percentage for an operation."""
        if operation_id in cls._active_operations:
            return cls._active_operations[operation_id].get("progress", 0)
        
        return 0
    
    @classmethod
    def _save_operation(cls, operation_id: str, operation_data: Dict[str, Any]):
        """Save operation data to persistent storage."""
        try:
            file_path = cls._storage_dir / f"{operation_id}.json"
            with open(file_path, "w") as f:
                json.dump(operation_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving operation {operation_id} to storage: {e}")
    
    @classmethod
    def _load_operation(cls, operation_id: str) -> Optional[Dict[str, Any]]:
        """Load operation data from persistent storage."""
        try:
            file_path = cls._storage_dir / f"{operation_id}.json"
            if not file_path.exists():
                return None
                
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading operation {operation_id} from storage: {e}")
            return None
    
    @classmethod
    async def _cleanup_old_operations(cls):
        """Background task to clean up old operations."""
        while True:
            try:
                current_time = time.time()
                
                # Clean up in-memory operations
                operations_to_remove = []
                
                for op_id, op_data in cls._active_operations.items():
                    # Skip operations that are still in progress
                    if op_data.get("status") not in ["completed", "failed"]:
                        continue
                    
                    # Check if completion time exceeds retention period
                    completion_time = op_data.get("completion_time")
                    if completion_time:
                        try:
                            completion_dt = datetime.fromisoformat(completion_time)
                            completion_timestamp = completion_dt.timestamp()
                            
                            if current_time - completion_timestamp > cls._retention_time:
                                operations_to_remove.append(op_id)
                        except (ValueError, TypeError):
                            # If we can't parse the timestamp, skip this operation
                            pass
                
                # Remove old operations
                for op_id in operations_to_remove:
                    cls._active_operations.pop(op_id, None)
                
                # Sleep for a while before next cleanup
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error
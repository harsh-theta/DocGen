"""
Export status tracking endpoints.

This module provides API endpoints for tracking the status of export operations.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request

from backend.models.user import User
from backend.core.database import get_db
from backend.services.auth import get_current_user
from backend.utils.progress_tracker import ProgressTracker

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/export/status/{operation_id}")
async def get_export_status(
    operation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of an export operation.
    
    Args:
        operation_id: ID of the export operation to check
        request: FastAPI request object
        current_user: Authenticated user
        
    Returns:
        Dict: Current status of the export operation
    """
    # Get operation status
    status = ProgressTracker.get_operation_status(operation_id)
    
    # Check if operation exists
    if "error" in status:
        raise HTTPException(status_code=404, detail="Export operation not found")
    
    # Check if operation belongs to the current user
    if status.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have permission to view this export operation")
    
    return status

@router.get("/export/user-operations")
async def get_user_operations(
    request: Request,
    operation_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Get export operations for the current user.
    
    Args:
        request: FastAPI request object
        operation_type: Optional filter by operation type
        status: Optional filter by status
        limit: Maximum number of operations to return
        current_user: Authenticated user
        
    Returns:
        List[Dict]: List of export operations for the user
    """
    # Get user operations
    operations = ProgressTracker.get_user_operations(
        user_id=current_user.id,
        operation_type=operation_type,
        status=status,
        limit=limit
    )
    
    return {"operations": operations}
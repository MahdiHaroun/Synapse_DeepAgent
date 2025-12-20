"""
Chat router for compatibility with existing API structure.
Provides REST endpoints for WebSocket server information.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from Backend.api.database import get_db
from Backend.api import models, auth
from src.MainAgent.agent import MainAgent
from pathlib import Path
import os

router = APIRouter(prefix="/chat", tags=["Chat"])

# Initialize managers


@router.get("/info")
async def get_chat_info():
    """Get WebSocket server information."""
    return {
        "websocket_url": "ws://localhost:8071",
        "protocol": "WebSocket with chunked streaming",
        "message_format": "JSON",
        "supported_actions": [
            "auth", "set_thread", "file_start", "file_chunk", "file_end",
            "image_start", "image_chunk", "image_end", "chat", "cancel"
        ],
        "features": [
            "JWT Authentication",
            "Chunked File Upload (hex-encoded bytes)",
            "Chunked Image Upload with validation",
            "Real-time chat streaming",
            "Cancellation support via Redis",
            "Image analysis integration"
        ],
        "upload_directory": "/tmp/ws_uploads",
        "ports": {
            "rest_api": 8070,
            "websocket": 8071
        }
    }


@router.post("/eventbridge_target")
async def eventbridge_target(
    event_data: dict,
    db: Session = Depends(get_db)
):
    """
    EventBridge webhook target - receives scheduled events from AWS EventBridge
    """
    try:
        # Extract schedule information from event
        schedule_name = event_data.get("schedule_name", "unknown")
        task_data = event_data.get("task_data", {})
        query = task_data.get("query", event_data.get("content", ""))
        
        # Log the event
        print(f"EventBridge triggered: {schedule_name}")
        print(f"Query: {query}")
        
        # Invoke the main agent with the query
        if query:
            result = MainAgent.invoke(query)
            
            # Update last_triggered_at in database
            eventbridge_rule_name = event_data.get("eventbridge_rule_name")
            if eventbridge_rule_name:
                from datetime import datetime
                schedule = db.query(models.EventBridgeSchedule).filter(
                    models.EventBridgeSchedule.eventbridge_rule_name == eventbridge_rule_name
                ).first()
                if schedule:
                    schedule.last_triggered_at = datetime.now()
                    db.commit()
            
            return {
                "status": "success",
                "message": "Schedule executed successfully",
                "schedule_name": schedule_name,
                "result": str(result)
            }
        else:
            return {
                "status": "error",
                "message": "No query provided in event_data"
            }
            
    except Exception as e:
        print(f"Error executing scheduled task: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/file_cache/{thread_id}")
async def get_file_cache(
    thread_id: str,
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get file cache for a thread (REST endpoint).
    Note: Files are managed per-connection in WebSocket, not globally cached by thread.
    """
    thread = db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id
    ).first()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Check uploads directory for files with this thread_id
    upload_dir = Path("/tmp/ws_uploads")
    files = []
    
    if upload_dir.exists():
        for file_path in upload_dir.glob(f"*{thread_id}*"):
            if file_path.is_file():
                files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": file_path.stat().st_size
                })
    
    return {
        "thread_id": thread_id,
        "files": files,
        "note": "Files are managed per WebSocket connection. Use WebSocket API for real-time file management."
    }


@router.delete("/file_cache/{thread_id}")
async def clear_file_cache(
    thread_id: str,
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Clear file cache for a thread (REST endpoint)."""
    thread = db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id
    ).first()
    
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Remove files from uploads directory
    upload_dir = Path("/tmp/ws_uploads")
    removed_files = []
    
    if upload_dir.exists():
        for file_path in upload_dir.glob(f"*{thread_id}*"):
            if file_path.is_file():
                try:
                    os.remove(file_path)
                    removed_files.append(str(file_path))
                except Exception as e:
                    print(f"Failed to remove {file_path}: {e}")
    
    return {
        "thread_id": thread_id,
        "removed_files": removed_files,
        "status": "cleared"
    }


@router.get("/health")
async def health_check():
    """Check WebSocket server health."""
    return {
        "status": "healthy",
        "websocket_server": "running on port 8071",
        "upload_dir_exists": os.path.exists("/tmp/ws_uploads")
    }

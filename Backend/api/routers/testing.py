import uuid
import asyncio
import hashlib
import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.logger import logger
from Backend.api.database import get_db
from Backend.api import models, auth
from Backend.api.routers.ingestion.pipeline import ingest_pipeline
from sqlalchemy.orm import Session
from src.MainAgent.agent import get_main_agent
from src.MainAgent.tools.memory_tools import Context
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/testing", tags=["Testing"])


class ChatRequest(BaseModel):
    """Chat request for testing"""
    message: str = Field(..., min_length=1, max_length=5000)
    thread_id: str = Field(..., description="Thread ID for conversation")

class ChatResponse(BaseModel):
    """Chat response schema"""
    response: str = Field(..., description="AI assistant response")
    thread_id: str = Field(..., description="Thread ID for this conversation")
    timestamp: str = Field(..., description="Response timestamp")
    status: str = Field(default="success", description="Response status")
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    input_tokens: Optional[int] = Field(None, description="Input tokens used")
    cache_tokens: Optional[int] = Field(None, description="Cached tokens used")
    output_tokens: Optional[int] = Field(None, description="Output tokens generated")


def retrieve_file_ids_for_thread(thread_id: str, db: Session):
    """Get all file IDs associated with a thread"""
    # Get the thread's integer ID from its UUID
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id).first()
    if not thread:
        return []
    
    return [
        row.file_uuid
        for row in db.query(models.UploadedFiles.file_uuid)
        .filter(models.UploadedFiles.thread_id == thread.id)
        .all()
    ]


def get_file_context(file_ids: list, db: Session) -> str:
    """Build file context information"""
    if not file_ids:
        return ""
    
    files_info = []
    for idx, file_id in enumerate(file_ids, 1):
        file = db.query(models.UploadedFiles).filter(models.UploadedFiles.file_uuid == file_id).first()
        if file:
            file_type = file.filename.split('.')[-1].upper() if '.' in file.filename else 'UNKNOWN'
            files_info.append(f"  {idx}. [{file_type}] {file.filename}\n     File ID: {file_id}")
        else:
            files_info.append(f"  {idx}. Unknown file\n     File ID: {file_id}")
    
    if files_info:
        file_count = len(files_info)
        return f"\n\n{'='*60}\n[AVAILABLE FILES IN THIS CONVERSATION: {file_count} file(s)]\n" + "\n".join(files_info) + f"\n{'='*60}\n\nIMPORTANT: When user asks about 'the document', 'this file', 'the PDF', they refer to these files above.\n- For questions about content: Use search_retrieve_faiss (auto-uses all files)\n- For summarization: Use summarize_file with specific file_id\n- For comparison: Search each file separately and compare results\n- Multiple files: You can analyze all of them together or individually\n"
    return ""


@router.post("/chat/{thread_id}", response_model=ChatResponse)
async def test_chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Testing endpoint for chat with Context support (no streaming).
    
    - Validates thread ownership
    - Retrieves file context from database
    - Invokes agent with full context
    - Returns complete response (no streaming)
    """
    try:
        # Validate thread ownership
        thread = db.query(models.Thread).filter(
            models.Thread.uuid == request.thread_id,
            models.Thread.admin_id == current_user.id
        ).first()
        
        if not thread:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or access denied"
            )
        
    
        
        # Create Context object
        context = Context(
            user_id=str(current_user.id),
            user_name=current_user.username,
            thread_id=request.thread_id,
            files_ids=[],
            images_ids=[]
        )
        
        # Get main agent
        main_agent = await get_main_agent()
        
        # Invoke agent (blocking, no streaming)
        result = await main_agent.ainvoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config={"configurable": {"thread_id": request.thread_id}},
            context=context
        )
        
        # Extract response
        final_response = ""
        total_tokens = None
        input_tokens = None
        output_tokens = None
        cache_tokens = None
        
        if result and "messages" in result:
            # Get last assistant message
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and msg.content:
                    final_response = msg.content
                    break
                    
            # Extract token usage from last message
            for msg in result["messages"]:
                if hasattr(msg, "usage_metadata"):
                    usage = msg.usage_metadata
                    total_tokens = usage.get("total_tokens")
                    input_tokens = usage.get("input_tokens")
                    output_tokens = usage.get("output_tokens")
                    cache_tokens = usage.get("input_token_details", {}).get("cache_read")
        
        if not final_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response generated from agent"
            )
        
        logger.info(f"Test chat completed - Thread: {request.thread_id}, User: {current_user.name}")    
        
        return ChatResponse(
            response=final_response,
            thread_id=request.thread_id,
            timestamp=datetime.utcnow().isoformat(),
            status="success",
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            cache_tokens=cache_tokens,
            output_tokens=output_tokens
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test_chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}"
        )




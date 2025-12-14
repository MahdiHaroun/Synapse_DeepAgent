from fastapi import APIRouter, Depends, Form, HTTPException, logger, status , UploadFile, File 
import hashlib
from sqlalchemy.orm import Session
from Backend.api.database import get_db
from Backend.api import models, schemas, auth
from src.MainAgent.agent import get_main_agent
from src.MainAgent.tools.memory_tools import Context
from fastapi.responses import StreamingResponse
import json




file_cache = {}  # Structure: {thread_id: {file_hash: file_path}}


router = APIRouter(prefix="/chat" , tags=["Chat"])


@router.get("/current_file_cache/{thread_id}", status_code=status.HTTP_200_OK)
async def get_current_file_cache(thread_id: str , current_user: models.Admin = Depends(auth.get_current_user) , 
                           db: Session = Depends(get_db)):
    """
    Get the current file cache for a specific thread.
    """
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    cache = file_cache.get(thread_id, {})
    return {"file_cache": list(cache.keys())}




@router.delete("/clear_file_cache/{thread_id}", status_code=status.HTTP_200_OK)
async def clear_file_cache(thread_id: str , current_user: models.Admin = Depends(auth.get_current_user) , 
                           db: Session = Depends(get_db)):
    """
    Clear the file cache for a specific thread and delete temporary files.
    """
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    import os
    removed_files = []
    if thread_id in file_cache:
        # Delete physical files
        for file_hash, file_path in file_cache[thread_id].items():
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    removed_files.append(file_path)
                except Exception as e:
                    print(f"Failed to remove {file_path}: {e}")
        # Clear from cache
        del file_cache[thread_id]
    
    return {"detail": f"File cache cleared for thread {thread_id}", "removed_files": removed_files}



@router.post("/stream_response/{thread_id}")
async def stream_chat_simple(
    thread_id: str, 
    message: str = Form(...),
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db) ,
    file: UploadFile = File(None),
    
    
):
    """
    Real-time streaming chat endpoint.
    """
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    

    # Handle file upload - only 1 file per thread
    temp_file_path = None
    if file and file.filename:
        import os
        
        # Clear existing cache for this thread (only 1 file allowed)
        if thread_id in file_cache:
            for old_hash, old_path in file_cache[thread_id].items():
                if old_path and os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"Failed to remove old file {old_path}: {e}")
            file_cache[thread_id] = {}
        else:
            file_cache[thread_id] = {}
        
        # Upload new file
        file_content = await file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        temp_file_path = f"/tmp/{thread_id}_{file_hash}_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        file_cache[thread_id][file_hash] = temp_file_path

    user_message = message
    if temp_file_path:
        user_message += f" [Attached file at {temp_file_path}]"
    

    async def event_stream():
        """Generator that yields SSE."""
        
        admin_username = current_user.username
        if not admin_username:
            raise HTTPException(status_code=404, detail="unable to retrieve admin username")

            

        try:
            yield f"data: {json.dumps({'type': 'start', 'thread_id': thread_id})}\n\n"

            main_agent = await get_main_agent()
            async for event in main_agent.astream_events(
                    {"messages": [{"role": "user", "content": user_message}] , "thread_id": thread_id, },
                    config={"configurable": {"thread_id": thread_id}},
                    version="v2",
                    context=Context(user_id=admin_username),
                ):

                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        content_str = ""
                        if isinstance(content, list):
                            content_str = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
                        else:
                            content_str = str(content)
                        yield f"data: {json.dumps({'type': 'content', 'content': content_str})}\n\n"

                elif kind == "on_chain_end":
                    tokens_data = {}
                    output = event.get("data", {}).get("output")
                    if output and isinstance(output, dict) and "messages" in output:
                        for msg in output["messages"]:
                            if hasattr(msg, "usage_metadata"):
                                usage = msg.usage_metadata
                                tokens_data = {
                                    "total_tokens": usage.get("total_tokens"),
                                    "input_tokens": usage.get("input_tokens"),
                                    "output_tokens": usage.get("output_tokens"),
                                    "cache_tokens": usage.get("input_token_details", {}).get("cache_read")
                                }
                                break
                    yield f"data: {json.dumps({'type': 'end', 'tokens': tokens_data})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'thread_id': thread_id})}\n\n" 

    return StreamingResponse(
        event_stream(), 
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )   





@router.post("/stream_response_tools/{thread_id}")
async def stream_chat(
    thread_id: str, 
    message: str = Form(...),
    file: UploadFile = File(None),
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db) 
    
):
    """
    Real-time streaming chat endpoint.
    """
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Handle file upload - only 1 file per thread
    temp_file_path = None
    if file and file.filename:
        import os
        
        # Clear existing cache for this thread (only 1 file allowed)
        if thread_id in file_cache:
            for old_hash, old_path in file_cache[thread_id].items():
                if old_path and os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception as e:
                        print(f"Failed to remove old file {old_path}: {e}")
            file_cache[thread_id] = {}
        else:
            file_cache[thread_id] = {}
        
        # Upload new file
        file_content = await file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        temp_file_path = f"/tmp/{thread_id}_{file_hash}_{file.filename}"
        with open(temp_file_path, "wb") as f:
            f.write(file_content)
        file_cache[thread_id][file_hash] = temp_file_path

    user_message = message
    if temp_file_path:
        user_message += f" [Attached file at {temp_file_path}]"


    async def event_stream():
        """Generator that yields SSE."""
        
        admin_username = current_user.username
        if not admin_username:
            raise HTTPException(status_code=404, detail="unable to retrieve admin username")

            

        try:
            yield f"data: {json.dumps({'type': 'start', 'thread_id': thread_id})}\n\n"

            main_agent = await get_main_agent()
            async for event in main_agent.astream_events(
                    {"messages": [{"role": "user", "content": user_message}] , "thread_id": thread_id, },
                    config={"configurable": {"thread_id": thread_id}},
                    version="v2",
                    context=Context(user_id=admin_username),
                ):

                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        content_str = ""
                        if isinstance(content, list):
                            content_str = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
                        else:
                            content_str = str(content)
                        yield f"data: {json.dumps({'type': 'content', 'content': content_str})}\n\n"

                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name']})}\n\n"

                elif kind == "on_tool_end":
                    output = str(event["data"].get("output", ""))[:200]
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name'], 'output': output})}\n\n"

                elif kind == "on_chain_end":
                    tokens_data = {}
                    output = event.get("data", {}).get("output")
                    if output and isinstance(output, dict) and "messages" in output:
                        for msg in output["messages"]:
                            if hasattr(msg, "usage_metadata"):
                                usage = msg.usage_metadata
                                tokens_data = {
                                    "total_tokens": usage.get("total_tokens"),
                                    "input_tokens": usage.get("input_tokens"),
                                    "output_tokens": usage.get("output_tokens"),
                                    "cache_tokens": usage.get("input_token_details", {}).get("cache_read")
                                }
                                break
                    yield f"data: {json.dumps({'type': 'end', 'tokens': tokens_data})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'thread_id': thread_id})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )





    





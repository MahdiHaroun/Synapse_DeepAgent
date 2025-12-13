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


router = APIRouter(prefix="/chat")


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
    
    # Handle file upload
    temp_file_path = None
    if file and file.filename:
        file_content = await file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        if thread_id not in file_cache:
            file_cache[thread_id] = {}
        if file_hash in file_cache[thread_id]:
            temp_file_path = file_cache[thread_id][file_hash]
        else:
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
                    {"messages": [{"role": "user", "content": user_message}]},
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


    





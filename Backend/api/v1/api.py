from contextlib import asynccontextmanager
import uuid
import asyncio
import hashlib
import os
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.logger import logger
from src.MCP.mcp import get_mcp_client
from src.MainAgent.agent import main_agent
from pydantic import BaseModel, Field, validator
from typing import Optional
from langgraph.types import Command

# File cache to store file hashes and paths per thread
file_cache = {}  # Structure: {thread_id: {file_hash: file_path}}
 

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    thread_id: str


class ChatRequest(BaseModel):
    """Chat request schema with thread-based memory"""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    temp_file_path: Optional[str] = Field(None, description="Path to temporary uploaded file")
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message content"""
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()
    
    @validator('thread_id')
    def validate_thread_id(cls, v):
        """Validate or generate thread_id"""
        if v is None:
            # Generate new thread ID if not provided
            return str(uuid.uuid4())
        return v
class ChatResponse(BaseModel):
    """Chat response schema"""
    response: str = Field(..., description="AI assistant response")
    thread_id: str = Field(..., description="Thread ID for this conversation")
    timestamp: str = Field(..., description="Response timestamp")
    status: str = Field(default="success", description="Response status")
    total_tokens: Optional[int] = Field(None, description="Total tokens used in the conversation") 
    input_tokens: Optional[int] = Field(None, description="Input tokens used")
    cashe_tokens: Optional[int] = Field(None, description="Cached tokens used")
    output_tokens: Optional[int] = Field(None, description="Output tokens generated")



class desegion(BaseModel):
    a :str 
    thread_id : str

@app.post("/agent/query")
async def query_agent(request: QueryRequest):
    # Create agent per request (lightweight, uses cached tools/model)
    agent = main_agent
    
    result = await agent.astream_events(
        {"messages": [{"role": "user", "content": request.query}]},
        {"configurable": {"thread_id": request.thread_id}}
    )
    with open("output.txt", "w") as f:
        f.write(str(result))
        
    
    return {"result": result}

@app.post("/agent/stream-with-file", response_model=ChatResponse)
async def chat_with_file(
    message: str = Form(...),
    thread_id: str = Form(default=None),
    file: UploadFile = File(None)
):
    """
    Chat endpoint optimized for Swagger UI file uploads.
    
    - **message**: User's message (required)
    - **thread_id**: Optional thread ID for conversation continuity  
    - **file**: Optional file upload
    
    Returns AI response with thread_id for subsequent requests.
    """
    try:
        
        if not thread_id:
            thread_id = str(uuid.uuid4())
            
        temp_file_path = None
        
        
        if file is not None and file.filename:
            
            file_content = await file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            
            # Initialize thread cache if it doesn't exist
            if thread_id not in file_cache:
                file_cache[thread_id] = {}
            
            # Check if file exists in this thread's cache
            if file_hash in file_cache[thread_id]:
                temp_file_path = file_cache[thread_id][file_hash]
                logger.info(f"Using cached file for thread {thread_id}: {temp_file_path}")
            else:
                
                temp_file_path = f"/tmp/{thread_id}_{file_hash}_{file.filename}"
                
                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(file_content)
                
                # Cache file for this specific thread
                file_cache[thread_id][file_hash] = temp_file_path
                logger.info(f"Cached new file for thread {thread_id}: {temp_file_path}")

        
        config = {
            "recursion_limit": 50,
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        
        user_message = message
        if temp_file_path:
            user_message += f" [Attached file at {temp_file_path}]"
        
        
        try:
            final_response = ""
            async for event in main_agent.astream_events(
                {"messages": [{"role": "user", "content": user_message}]},
                config={"configurable": {"thread_id": thread_id}},
                version="v2",
                stream_mode="updates"
            ):
                kind = event["event"]

                with open("event_new.txt", "w") as f:
                    f.write(str(event) + "\n")

                with open("kind_new .txt", "w") as f:
                    f.write(str(kind) + "\n")


                
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        final_response += content
                        logger.info(f"[AI Stream] {content}")
                
                
                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    logger.info(f"[Tool Called] {tool_name}")
                    final_response += f"\n[Using tool: {tool_name}]\n"
                
                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    tool_output = event["data"].get("output", "")
                    logger.info(f"[Tool Result] {tool_name}: {str(tool_output)[:100]}...")
                    if tool_output:
                        final_response += f"[Tool result: {str(tool_output)[:200]}...]\n"

                elif kind == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    
                    if output and "messages" in output:
                        messages = output["messages"]
                        
                        for msg in messages:
                            
                            if hasattr(msg, "usage_metadata"):
                                usage = msg.usage_metadata
                                total_tokens = usage.get("total_tokens")
                                input_tokens = usage.get("input_tokens")
                                output_tokens = usage.get("output_tokens")
                                cache_tokens = usage.get("input_token_details", {}).get("cache_read")

                    else:
                        print("No output/messages found in this event!")



            
                        
        except asyncio.TimeoutError:
            logger.error(f"Graph execution timeout for thread {thread_id}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again or simplify your query."
            )
        
        # Validate response
        if not final_response:
            logger.error("No response generated from graph")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response"
            )
        
        logger.info(f"Chat completed successfully - Thread: {thread_id}")

        


    
        return ChatResponse(
                response=final_response,
                thread_id=thread_id,
                timestamp=datetime.utcnow().isoformat(),
                status="success",
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                cashe_tokens=cache_tokens,
                output_tokens=output_tokens,
            )
        
        

        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in chat_with_file endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    



@app.post("/contuinue" , response_model=ChatResponse )
async def continue_chat(request: desegion):
    try:
        
        result = await main_agent.ainvoke(
            Command( 
                resume={"decisions": [{"type": request.a}]}  # or "edit", "reject"
            ), 
            {"configurable": {"thread_id": request.thread_id}}
        )
        
        # Extract response content from the result
        response_content = ""
        if result and "messages" in result:
            # Get the last message content
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                response_content = last_message.content
            else:
                response_content = str(last_message)
        else:
            response_content = f"Action '{request.a}' processed successfully"
        
        return ChatResponse(
            response=response_content,
            thread_id=request.thread_id,
            timestamp=datetime.utcnow().isoformat(),
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error in continue_chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to continue chat: {str(e)}"
        )


@app.get("/admin/file-cache/{thread_id}")
async def get_file_cache_status(thread_id: str):
    """Get current file cache status for specific thread"""
    thread_cache = file_cache.get(thread_id, {})
    cache_info = {}
    
    for file_hash, file_path in thread_cache.items():
        file_exists = os.path.exists(file_path) if file_path else False
        cache_info[file_hash] = {
            "file_path": file_path,
            "exists": file_exists,
            "filename": os.path.basename(file_path) if file_path else None
        }
    
    return {
        "thread_id": thread_id,
        "cache_size": len(thread_cache),
        "cached_files": cache_info,
        "total_threads": len(file_cache),
        "all_threads": list(file_cache.keys())
    }


@app.delete("/admin/file-cache/{thread_id}")
async def clear_file_cache(thread_id: str):
    """Clear the file cache for specific thread and remove temporary files"""
    removed_files = 0
    errors = []
    
    if thread_id in file_cache:
        thread_cache = file_cache[thread_id]
        
        for file_hash, file_path in thread_cache.items():
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    removed_files += 1
            except Exception as e:
                errors.append(f"Error removing {file_path}: {str(e)}")
        
        # Remove thread's cache
        del file_cache[thread_id]
        message = f"File cache cleared for thread {thread_id}"
    else:
        message = f"No cache found for thread {thread_id}"
    
    return {
        "message": message,
        "thread_id": thread_id,
        "removed_files": removed_files,
        "errors": errors if errors else None
    }


@app.get("/admin/file-cache")
async def get_all_file_caches():
    """Get file cache status for all threads"""
    all_caches = {}
    total_files = 0
    
    for thread_id, thread_cache in file_cache.items():
        cache_info = {}
        for file_hash, file_path in thread_cache.items():
            file_exists = os.path.exists(file_path) if file_path else False
            cache_info[file_hash] = {
                "file_path": file_path,
                "exists": file_exists,
                "filename": os.path.basename(file_path) if file_path else None
            }
            total_files += 1
        
        all_caches[thread_id] = {
            "cache_size": len(thread_cache),
            "cached_files": cache_info
        }
    
    return {
        "total_threads": len(file_cache),
        "total_cached_files": total_files,
        "threads": all_caches
    }


@app.delete("/admin/file-cache")
async def clear_all_file_caches():
    """Clear all file caches and remove all temporary files"""
    removed_files = 0
    errors = []
    cleared_threads = list(file_cache.keys())
    
    for thread_id, thread_cache in file_cache.items():
        for file_hash, file_path in thread_cache.items():
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    removed_files += 1
            except Exception as e:
                errors.append(f"Error removing {file_path}: {str(e)}")
    
    file_cache.clear()
    
    return {
        "message": "All file caches cleared",
        "cleared_threads": cleared_threads,
        "removed_files": removed_files,
        "errors": errors if errors else None
    }
   


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)# To run the FastAPI app, use the command:
    # uvicorn Backend.api.v1.api:app --reload
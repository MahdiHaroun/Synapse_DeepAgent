from contextlib import asynccontextmanager
import uuid
import asyncio
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.logger import logger
from src.MCP.mcp import get_mcp_client
from src.MainAgent.agent import main_agent
from pydantic import BaseModel, Field, validator
from typing import Optional
from langgraph.types import Command
 

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    thread_id: str


class ChatRequest(BaseModel):
    """Chat request schema with thread-based memory"""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    thread_id: Optional[str] = Field(None, description="Thread ID for conversation continuity")
    
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

@app.post("/agent/stream" , response_model=ChatResponse )
async def chat(request: ChatRequest):
    """
    Main chat endpoint with thread-based memory.
    
    - **message**: User's message (required)
    - **thread_id**: Optional thread ID for conversation continuity
    
    Returns AI response with thread_id for subsequent requests.
    """
    try:
        
        
        # Configure graph execution with thread-based checkpointing
        config = {
            "recursion_limit": 50,
            "configurable": {
                "thread_id": request.thread_id
            }
        }
        
        # Invoke the graph with streaming
        try:
            final_response = ""
            async for event in main_agent.astream_events(
                {"messages": [{"role": "user", "content": request.message}]},
                config={"configurable": {"thread_id": request.thread_id}},
                version="v2",
                stream_mode="updates"
            ):
                kind = event["event"]
                
                # Stream AI message content
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        final_response += content
                        logger.info(f"[AI Stream] {content}")
                
                # Stream tool calls and results
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
                        
        except asyncio.TimeoutError:
            logger.error(f"Graph execution timeout for thread {request.thread_id}")
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
            
        
        
        logger.info(f"Chat completed successfully - Thread: {request.thread_id}")
        
        
        return ChatResponse(
            response=final_response,
            thread_id=request.thread_id,
            timestamp=datetime.utcnow().isoformat(),
            status="success"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )
@app.post("/contuinue" , response_model=ChatResponse )
async def continue_chat(request: desegion):
    try:
        # Execute the continuation command
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
   


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)# To run the FastAPI app, use the command:
    # uvicorn Backend.api.v1.api:app --reload
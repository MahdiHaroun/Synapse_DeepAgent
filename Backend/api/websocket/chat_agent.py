from src.MainAgent.tools.memory_tools import Context
from Backend.api.websocket.redis_cancel import is_cancelled
from src.MainAgent.agent import get_main_agent
from Backend.api.database import get_db
from Backend.api.models import UploadedFiles
from Backend.api.database import sessionLocal
from Backend.api import models



async def update_thread_last_active(thread_id: str):
    """Update the last_active timestamp of a thread to the current time."""
    db = sessionLocal()
    try:
        thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id).first()
        if thread:
            from datetime import datetime
            thread.last_interaction = datetime.utcnow()
            db.commit()
    finally:
        db.close()

async def stream_chat(
    thread_id: str,
    user_id: str,
    user_name: str,
    message: str,
    file_path: str, 
    show_tools_responses: bool = False
):
    """Stream chat responses from the main agent with cancellation support."""
    print(f"[DEBUG] stream_chat called with show_tools_responses={show_tools_responses} (type: {type(show_tools_responses)})")
    try:
        main_agent = await get_main_agent()
        context = Context(
            user_id=user_id,
            user_name=user_name,
            thread_id=thread_id,
            file_path = file_path
            
        )
        
   
        if file_path:
            file_context = (
                "\n\nThe user has uploaded the following file for context:\n"
                f"{file_path}\n"
                f"The realative path to access the file is {file_path}\n"
            )
        else:
            file_context = ""

        
        # Append file context to user message
        enhanced_message = message + "\n" + file_context
        
        async for event in main_agent.astream_events(
            {"messages": [{"role": "user", "content": enhanced_message}], "thread_id": thread_id},
            config={"configurable": {"thread_id": thread_id}},
            context=context
        ):
            # Check cancellation
            if await is_cancelled(thread_id):
                yield {"type": "cancelled"}
                return

            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    content_str = ""
                    if isinstance(content, list):
                        content_str = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
                    else:
                        content_str = str(content)
                    yield {"type": "content", "content": content_str}
                
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown_tool")
                print(f"[DEBUG] Tool start detected: {tool_name}, show_tools_responses={show_tools_responses}")
                if show_tools_responses:
                    yield {"type": "tool_start", "tool_name": tool_name}
            elif kind == "on_tool_end":
                tool_name = event.get("name", "unknown_tool")
                tool_output = event["data"].get("output", "")
                print(f"[DEBUG] Tool end detected: {tool_name}, show_tools_responses={show_tools_responses}")
                if show_tools_responses:
                    yield {"type": "tool_end", "tool_name": tool_name, "output": str(tool_output)}

            elif kind == "on_chain_end":
                output = event.get("data", {}).get("output", {})
                # Extract only JSON-serializable data from output
                tokens = {}
                if isinstance(output, dict):
                    # Try to extract token usage info if available
                    if "usage_metadata" in output:
                        tokens = output["usage_metadata"]
                    elif "token_usage" in output:
                        tokens = output["token_usage"]
                yield {"type": "end", "tokens": tokens}

        
    except Exception as e:
        yield {"type": "error", "message": f"Chat error: {str(e)}"}

    finally:
        await update_thread_last_active(thread_id)

        
        

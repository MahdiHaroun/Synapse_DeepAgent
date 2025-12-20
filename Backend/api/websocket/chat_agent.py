from src.MainAgent.tools.memory_tools import Context
from Backend.api.websocket.redis_cancel import is_cancelled
from src.MainAgent.agent import get_main_agent
from Backend.api.database import get_db
from Backend.api.models import UploadedFiles


async def stream_chat(
    thread_id: str,
    user_id: str,
    user_name: str,
    message: str,
    file_ids: list
):
    """Stream chat responses from the main agent with cancellation support."""
    try:
        main_agent = await get_main_agent()
        context = Context(
            user_id=user_id,
            user_name=user_name,
            thread_id=thread_id,
            files_ids=file_ids,
            images_ids=[]
        )
        
        # Build comprehensive file context information
        file_context = ""
        if file_ids:
            db = next(get_db())
            try:
                files_info = []
                for idx, file_id in enumerate(file_ids, 1):
                    file = db.query(UploadedFiles).filter(UploadedFiles.file_id == file_id).first()
                    if file:
                        file_type = file.filename.split('.')[-1].upper() if '.' in file.filename else 'UNKNOWN'
                        files_info.append(f"  {idx}. [{file_type}] {file.filename}\n     File ID: {file_id}")
                    else:
                        files_info.append(f"  {idx}. Unknown file\n     File ID: {file_id}")
                
                if files_info:
                    file_count = len(files_info)
                    file_context = f"\n\n{'='*60}\n[AVAILABLE FILES IN THIS CONVERSATION: {file_count} file(s)]\n" + "\n".join(files_info) + f"\n{'='*60}\n\nIMPORTANT: When user asks about 'the document', 'this file', 'the PDF', they refer to these files above.\n- For questions about content: Use search_retrieve_faiss (auto-uses all files)\n- For summarization: Use summarize_file with specific file_id\n- For comparison: Search each file separately and compare results\n- Multiple files: You can analyze all of them together or individually\n"
            finally:
                db.close()
        
        # Append file context to user message
        enhanced_message = message + file_context
        
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

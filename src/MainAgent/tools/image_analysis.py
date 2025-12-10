from src.LLMs.AWS_LLMs.llms import sonnet_3_5_vision_llm
from langchain_core.messages import HumanMessage, ToolMessage
from langchain.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing import Annotated
from src.States.state import DeepAgentState 




@tool
def analyze_image(
    image_path: str,
    question: str = "Describe this image in detail",
    state: Annotated[DeepAgentState, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None
) -> Command:
    """Analyze an image and cache the result for reuse.
    
    Args:
        image_path: Absolute path to the image file or just filename
        question: Question to ask about the image
        state: Agent state for caching
        tool_call_id: Tool call identifier
        
    Returns:
        Command with cached or new analysis result
    """
    import base64
    import os
    import glob

    # Check cache first
    filename = os.path.basename(image_path)
    cache_key = f"image_analysis_{filename}_{question}"
    cached_files = state.get("files", {}) if state else {}
    
    if cache_key in cached_files:
        return Command(
            update={"messages": [ToolMessage(f"Using cached analysis for {filename}\n\n{cached_files[cache_key]}", tool_call_id=tool_call_id)]}
        )
    
    try:
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
            ]
        )
        result = sonnet_3_5_vision_llm.invoke([message])
        
        # Handle list content from ChatBedrock
        if isinstance(result.content, list):
            analysis = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in result.content)
        else:
            analysis = result.content
        
        # Cache the analysis result
        return Command(
            update={
                "files": {cache_key: analysis},
                "messages": [ToolMessage(f"Analyzed {filename} and cached result\n\n{analysis}", tool_call_id=tool_call_id)]
            }
        )
    except Exception as e:
        error_msg = f"Error analyzing image: {str(e)}"
        return Command(
            update={"messages": [ToolMessage(error_msg, tool_call_id=tool_call_id)]}
        )
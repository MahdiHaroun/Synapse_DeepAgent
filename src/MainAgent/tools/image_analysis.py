from src.LLMs.AWS_LLMs.llms import sonnet_3_5_vision_llm
from langchain_core.messages import HumanMessage
from langchain.tools import tool 




@tool
def analyze_image(image_path: str, question: str = "Describe this image in detail") -> str:
    """Analyze an image and answer questions about it.
    
    Args:
        image_path: Absolute path to the image file or just filename
        question: Question to ask about the image
        
    Returns:
        Analysis result from the vision model
    """
    import base64
    import os
    import glob

    
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
        return result.content
    except Exception as e:
        return f"Error analyzing image: {str(e)}"
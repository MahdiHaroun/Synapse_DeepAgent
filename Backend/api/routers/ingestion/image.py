from src.LLMs.AWS_LLMs.llms import sonnet_3_5_vision_llm 
import imghdr
from PIL import Image
import os, base64
from langchain_core.messages import HumanMessage




class ImageProcessor:
    def __init__(self):
        self.llm = sonnet_3_5_vision_llm  

    async def validate_image(self, path: str):
        if imghdr.what(path) not in ("jpeg", "png", "webp"):
            raise ValueError("Invalid image type")
        with Image.open(path) as img:
            img.verify()

    async def normalize_image(self, path: str):
        with Image.open(path) as img:
            img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            normalized_path = path + "_normalized.png"
            img.save(normalized_path, format="PNG", optimize=True)
        return normalized_path
    

    async def analyze_image(self, normalized_path:str) -> str:
        with open(normalized_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        message = HumanMessage(
            content=[
                {"type": "text", "text": "Briefly describe this image in detail for RAG ingestion. Focus on key elements, colors, objects, and context."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
            ]
        )
        result = self.llm.invoke([message])
        analysis = ""
        if isinstance(result.content, list):
            analysis = "".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in result.content)
        else:
            analysis = result.content
        return analysis
    

     
    

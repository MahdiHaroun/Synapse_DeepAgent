'''

from langchain_openai import ChatOpenAI
from pathlib import Path    
from dotenv import load_dotenv
import os

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

def get_openai_gpt4_llm():
    openai_gpt4 = ChatOpenAI(model_name="gpt-4o-mini", temperature=0 , model_kwargs={"parallel_tool_calls": False})
    return openai_gpt4


openai_gpt4_llm = get_openai_gpt4_llm()

'''
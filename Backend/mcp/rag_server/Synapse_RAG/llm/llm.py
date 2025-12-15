from functools import lru_cache
from langchain_groq import ChatGroq
import os
from pathlib import Path
from dotenv import load_dotenv






@lru_cache()
def get_groq_llama3_llm():
    groq_llama3_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
    return groq_llama3_llm

groq_llama3_llm = get_groq_llama3_llm()

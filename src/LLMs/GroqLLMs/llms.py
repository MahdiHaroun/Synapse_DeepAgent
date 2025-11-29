from functools import lru_cache
from langchain_groq import ChatGroq
import os
from pathlib import Path
from dotenv import load_dotenv

from src.logging.logger import logger 

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Verify GROQ_API_KEY is loaded
if not os.getenv("GROQ_API_KEY"):
    raise ValueError(
        f"GROQ_API_KEY not found in environment variables. "
        f"Please check your .env file at: {env_path}"
    )

@lru_cache()
def get_groq_GPT_OSS_llm():
    logger.info("Initializing GPT OSS model...")
    groq_gpt_oss_llm = ChatGroq(model="openai/gpt-oss-safeguard-20b", temperature=0.7)
    logger.info("Successfully initialized ChatGroq with model openai/gpt-oss-safeguard-20b")
    return groq_gpt_oss_llm

groq_gpt_oss_llm = get_groq_GPT_OSS_llm()



@lru_cache()
def get_groq_moonshotai_llm():
    logger.info("Initializing moonshotai model...")
    groq_moonshotai_llm = ChatGroq(model="moonshotai/kimi-k2-instruct-0905", temperature=0.7)
    logger.info("Successfully initialized ChatGroq with model moonshotai/moonshot-70b")
    return groq_moonshotai_llm

groq_moonshotai_llm = get_groq_moonshotai_llm()


@lru_cache()
def get_groq_llama3_llm():
    logger.info("Initializing llama3 model...")
    groq_llama3_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
    logger.info("Successfully initialized ChatGroq with model llama-3.3-70b-versatile")
    return groq_llama3_llm

groq_llama3_llm = get_groq_llama3_llm()


if __name__ == "__main__":
    
    
    print("Testing Groq GPT OSS LLM:")
    print(get_groq_GPT_OSS_llm())
    print("\nTesting Groq MoonshotAI LLM:")
    print(get_groq_moonshotai_llm())
    print("\nTesting Groq Llama3 LLM:")
    print(get_groq_llama3_llm())


from langchain_aws import BedrockEmbeddings
import boto3 
from functools import lru_cache 
from dotenv import load_dotenv
import os
#load_dotenv("/app/.env")
from pathlib import Path


env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")




@lru_cache 
def get_bedrock_embeddings():
    bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1") 
    titan_embed_v1 = BedrockEmbeddings(
        client=bedrock,
        model_id="amazon.titan-embed-text-v1"
    )
    return titan_embed_v1


titan_embed_v1 = get_bedrock_embeddings()

from langchain_aws import BedrockEmbeddings
import boto3 
from functools import lru_cache 





@lru_cache 
def get_bedrock_embeddings():
    bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1") 
    titan_embed_v1 = BedrockEmbeddings(
        client=bedrock,
        model_id="amazon.titan-embed-text-v1"
    )
    return titan_embed_v1


titan_embed_v1 = get_bedrock_embeddings()

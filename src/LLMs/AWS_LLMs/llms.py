from langchain_aws import BedrockLLM, ChatBedrock
import boto3
from functools import lru_cache


@lru_cache
def get_sonnet_3_5_llm():
    bedrock = boto3.client("bedrock-runtime", region_name="eu-central-1")
    anthropic_claude_3_5_sonnet = BedrockLLM(
        client=bedrock,
        model_id="anthropic-claude-3-5-sonnet-20240620-v1-0",
        temperature=0.7,
    )
    return anthropic_claude_3_5_sonnet


@lru_cache
def get_sonnet_3_5_vision_llm():
    """Get Claude 3.5 Sonnet with vision support for image analysis."""
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    return ChatBedrock(
        client=bedrock,
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        model_kwargs={"temperature": 0.7}
    )


sonnet_3_5_llm = get_sonnet_3_5_llm()
sonnet_3_5_vision_llm = get_sonnet_3_5_vision_llm()
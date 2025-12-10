from langchain_aws import ChatBedrock
import boto3
from functools import lru_cache


@lru_cache
def get_sonnet_3_5_llm():
    """Get Claude 3.5 Sonnet with tool support."""
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    return ChatBedrock(
        client=bedrock,
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        model_kwargs={"temperature": 0.7}
    )


@lru_cache
def get_sonnet_3_5_vision_llm():
    """Get Claude 3.5 Sonnet with vision support for image analysis."""
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    return ChatBedrock(
        client=bedrock,
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        model_kwargs={"temperature": 0.7}
    )


@lru_cache
def get_sonnet_4_llm():
    """Get Claude Sonnet 4 with tool support."""
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    return ChatBedrock(
        client=bedrock,
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        model_kwargs={"temperature": 0.7}
    )


sonnet_3_5_llm = get_sonnet_3_5_llm()
sonnet_3_5_vision_llm = get_sonnet_3_5_vision_llm()
sonnet_4_llm = get_sonnet_4_llm()
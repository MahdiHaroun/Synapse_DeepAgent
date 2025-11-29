from mcp.server.fastmcp import FastMCP
import boto3
from botocore.exceptions import ClientError

mcp = FastMCP("S3" , host="0.0.0.0", port=3000)


s3 = boto3.client("s3")

@mcp.tool()
async def list_buckets():
    """List all S3 buckets"""
    try:
        response = s3.list_buckets()
        buckets = [bucket['Name'] for bucket in response.get('Buckets', [])]
        return {"buckets": buckets}
    except ClientError as e:
        return {"error": str(e)}

@mcp.tool()
async def list_objects(bucket_name: str):
    """List objects in a specified S3 bucket"""
    try:
        response = s3.list_objects_v2(Bucket=bucket_name)
        contents = response.get('Contents', [])
        objects = [obj['Key'] for obj in contents] if contents else []
        return {"objects": objects}
    except ClientError as e:
        return {"error": str(e)}

@mcp.tool()
async def read_object(bucket_name: str, object_key: str, decode_utf8: bool = True):
    """Get an object from a specified S3 bucket"""
    try:
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        data = response['Body'].read()
        content = data.decode('utf-8') if decode_utf8 else data
        return {"content": content}
    except ClientError as e:
        return {"error": str(e)}
    

@mcp.tool()
async def get_object_metadata(bucket_name: str, object_key: str):
    """
    Get metadata for an S3 object: last modified, size, content type, custom metadata.
    """
    try:
        response = s3.head_object(Bucket=bucket_name, Key=object_key)
        metadata = {
            "last_modified": response['LastModified'].isoformat(),
            "size_bytes": response['ContentLength'],
            "content_type": response['ContentType'],
            "etag": response.get('ETag'),
            "metadata": response.get('Metadata', {})  
        }
        return metadata
    except ClientError as e:
        return {"error": str(e)}
    


if __name__ == "__main__":
    mcp.run(transport="sse")



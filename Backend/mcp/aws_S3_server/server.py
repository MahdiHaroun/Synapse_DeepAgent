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
    

@mcp.tool()
async def generate_presigned_url(bucket_name: str, object_key: str, expiration: int = 3600):
    """
    Generate a presigned URL to access an S3 object.
    """
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_key},
            ExpiresIn=expiration
        )
        return {"presigned_url": url}
    except ClientError as e:
        return {"error": str(e)}
    

@mcp.tool()
async def download_object(bucket_name: str, object_key: str):
    """
    Download an S3 object to a local file.
    """
    try:
        download_path = f"saved_downloads/{object_key.replace('/', '_')}"
        s3.download_file(bucket_name, object_key, download_path)
        return {"message": f"Object {object_key} downloaded to {download_path}"}
    except ClientError as e:
        return {"error": str(e)}
    

@mcp.tool()
async def download_object_by_url(presigned_url: str, download_path: str):
    """
    Download an S3 object using a presigned URL to a local file.
    """
    import requests
    try:
        response = requests.get(presigned_url)
        response.raise_for_status()
        with open(download_path, 'wb') as f:
            f.write(response.content)
        return {"message": f"Object downloaded to {download_path}"}
    except requests.RequestException as e:
        return {"error": str(e)}
    

@mcp.tool()
async def upload_object(bucket_name: str, object_key: str, file_path: str):
    """
    Upload a local file to an S3 bucket.
    """
    try:
        s3.upload_file(file_path, bucket_name, object_key)
        return {"message": f"File {file_path} uploaded to {bucket_name}/{object_key}"}
    except ClientError as e:
        return {"error": str(e)}
    
if __name__ == "__main__":
    mcp.run(transport="sse")



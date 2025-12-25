from mcp.server.fastmcp import FastMCP
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
from pathlib import Path
mcp = FastMCP("S3" , host="0.0.0.0", port=3000)

env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")

s3 = boto3.client("s3")


"""
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

"""




@mcp.tool()
async def list_objects(thread_id: str):
    """
    List objects inside bucket_name/thread_id/ and return full S3 keys.
    """
    try:
        prefix = f"{thread_id}/"

        response = s3.list_objects_v2(
            Bucket= "synapse-openapi-schemas",
            Prefix=prefix
        )

        contents = response.get("Contents", [])
        
        # Return full S3 keys
        objects = [obj["Key"] for obj in contents if obj["Key"] != prefix]

        return {
            "objects": objects,
            "prefix": prefix
        }

    except ClientError as e:
        return {"error": str(e)}



@mcp.tool()
async def read_object(thread_id: str, bucket_name: str, object_key: str, decode_utf8: bool = True):
    """Get an object from a specified S3 bucket"""
    try:
        s3_key = f"{thread_id}/{object_key}"
        response = s3.get_object(Bucket=bucket_name, Key=s3_key)
        data = response['Body'].read()
        content = data.decode('utf-8') if decode_utf8 else data
        return {"content": content}
    except ClientError as e:
        return {"error": str(e)}
    

@mcp.tool()
async def get_object_metadata(thread_id: str, bucket_name: str, object_key: str):
    """
    Get metadata for an S3 object: last modified, size, content type, custom metadata.
    """
    try:
        s3_key = f"{thread_id}/{object_key}"
        response = s3.head_object(Bucket=bucket_name, Key=s3_key)
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
async def generate_presigned_url(thread_id: str, bucket_name: str, object_key: str, expiration: int = 3600):
    """
    Generate a presigned URL for s3://bucket/thread_id/object_key
    """
    try:
        # Full S3 key inside the thread folder
        s3_key = f"{thread_id}/{object_key}"

        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=expiration
        )

        return {
            "presigned_url": url,
            "s3_key": s3_key,
            "expires_in_seconds": expiration
        }

    except ClientError as e:
        return {"error": str(e)}

    

@mcp.tool()
async def download_object(thread_id: str, bucket_name: str, object_key: str) -> dict:
    """
    Download an S3 object from bucket_name/thread_id/object_key
    and save it locally in saved_downloads/.
    """
    try:
        # Build the full S3 key inside the thread folder
        s3_key = f"{thread_id}/{object_key}"

        # Ensure local folder exists
        os.makedirs("saved_downloads", exist_ok=True)

        # Replace slashes for safe local filename


        download_path = f"/shared/{thread_id}/saved_downloads/{object_key.replace('/', '_')}"

        os.makedirs(os.path.dirname(download_path), exist_ok=True)

        s3.download_file(bucket_name, s3_key, download_path)

        return {
            "message": f"Downloaded s3://{bucket_name}/{s3_key} to {download_path}",
            "local_path": download_path,
            
        }

    except ClientError as e:
        return {"error": str(e)}

    

@mcp.tool()
async def download_object_by_url(presigned_url: str , thread_id: str) -> dict:
    """
    Download an S3 object using a presigned URL to a shared volume.
    """
    import os
    import requests
    from urllib.parse import urlparse

    try:
        # Extract filename safely
        parsed = urlparse(presigned_url)
        filename = parsed.path.split("/")[-1]

        download_path = f"/shared/{thread_id}/saved_downloads/{filename}"

        os.makedirs(os.path.dirname(download_path), exist_ok=True)

        with requests.get(presigned_url, stream=True) as r:
            r.raise_for_status()
            with open(download_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

        return {"message": f"Object downloaded to {download_path}"}

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def upload_object(thread_id: str, object_key: str, relative_path: str):
    """
    Upload a local file to an S3 bucket under a specific thread_id folder.
    
    Args:
        thread_id: Thread ID for organizing files
        object_key: Desired S3 object key (filename in S3)
        relative_path: Path relative to /shared/{thread_id}/ (e.g., 'documents/file.pdf', 'analysis_images/chart.png', 'saved_downloads/data.xlsx')
    
    Resulting S3 path: bucket_name/thread_id/object_key
    """
    try:
        bucket_name = "synapse-openapi-schemas"
    
        s3_key = f"{thread_id}/{object_key}"
        file_path = f"/shared/{thread_id}/{relative_path}"
        
        if not os.path.exists(file_path):
            return {"error": f"File not found at {file_path}"}
        
        s3.upload_file(file_path, bucket_name, s3_key)

        return {
            "message": f"File uploaded to s3://{bucket_name}/{s3_key}",
            "s3_key": s3_key,
            "source_path": file_path
        }

    except ClientError as e:
        return {"error": str(e)}
    


if __name__ == "__main__":
    mcp.run(transport="sse")




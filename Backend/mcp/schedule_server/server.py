from mcp.server.fastmcp import FastMCP
import random 
import resend
import datetime
import os
import boto3
import base64
from pathlib import Path
from dotenv import load_dotenv



env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Set AWS credentials
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")

resend.api_key = os.getenv("RESEND_API_KEY")

mcp = FastMCP("Schedule" , host="0.0.0.0", port=3070)


@mcp.tool()
async def send_email_from_schedule_jobs(
    subject: str,
    html_content: str,
    s3_key: str = None
):
    """
    Send an email with optional attachment using Resend.
    
    Args:
        subject: Email subject line
        html_content: HTML content of the email
        s3_key: S3 key of the attachment to download (format: "thread_id/filename.pdf")
    Returns:
        dict: Result of the email sending operation
    """
    attachment_content = None
    filename = None
    
    # Download attachment from S3 if s3_key is provided
    if s3_key:
        s3 = boto3.client("s3", region_name="eu-central-1")
        bucket_name = "synapse-openapi-schemas"
        
        try:
            # Download file content to memory
            response = s3.get_object(Bucket=bucket_name, Key=s3_key)
            attachment_content = response['Body'].read()
            filename = os.path.basename(s3_key)
        except s3.exceptions.NoSuchKey:
            return {"success": False, "error": f"File not found in S3: {s3_key}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to download from S3: {str(e)}"}

    params = {
        "from": "noreply@optichoice.me",
        "to": ["mahdiharoun44@gmail.com"],
        "subject": subject,
        "html": html_content
    }
    
    # Add attachment if downloaded
    if attachment_content and filename:
        # Resend requires base64 encoding for content
        attachment_base64 = base64.b64encode(attachment_content).decode('utf-8')
        params["attachments"] = [{
            "filename": filename,
            "content": attachment_base64
        }]
    elif s3_key:
        return {"success": False, "error": "Failed to prepare attachment"}
    
    try:
        response = resend.Emails.send(params)
        return {"success": True, "id": response.get("id"), "message": "Email sent successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    


if __name__ == "__main__":
    mcp.run(transport="sse")
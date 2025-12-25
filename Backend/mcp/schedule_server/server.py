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
    file_name: str = None,
    thread_id: str = "schedule_jobs",
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
    
    
  
    file_path= f"/shared/{thread_id}/{file_name}"

    if file_name and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            attachment_content = f.read()
            filename = file_name
    elif file_name:
        return {"success": False, "error": "Attachment file not found"}

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
    elif file_name:
        return {"success": False, "error": "Failed to prepare attachment"}
    
    try:
        response = resend.Emails.send(params)
        return {"success": True, "id": response.get("id"), "message": "Email sent successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    


if __name__ == "__main__":
    mcp.run(transport="sse")
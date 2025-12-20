from mcp.server import FastMCP 
from mcp.server.fastmcp import Context
import httpx
from starlette.responses import HTMLResponse
import urllib.parse
from dotenv import load_dotenv
import os
from pathlib import Path
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mimetypes
import io
import boto3
import resend

# Load .env from mounted volume
#load_dotenv("/app/.env")
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)


os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")
os.environ["RESEND_API_KEY"] = os.getenv("RESEND_API_KEY")
print(f"RESEND_API_KEY loaded strarting with: {os.getenv('RESEND_API_KEY')[:5]}...")

"""
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

"""

# Initialize the MCP server
mcp = FastMCP("GoogleGmail", host="0.0.0.0", port=3050)

# Google OAuth credentials
CLIENT_ID = os.getenv("GOOGLE_GMAIL_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_GMAIL_CLIENT_SECRET")

# Debug: Print credential status (without exposing actual values)
print(f"CLIENT_ID loaded: {'Yes' if CLIENT_ID else 'No'}")
print(f"CLIENT_SECRET loaded: {'Yes' if CLIENT_SECRET else 'No'}")
if CLIENT_ID:
    print(f"CLIENT_ID starts with: {CLIENT_ID[:10]}...")
REDIRECT_URI = "http://localhost:3050/oauth2callback"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify"
]

# Default user email
DEFAULT_USER_EMAIL = "mahdiharoun44@gmail.com"

# Store tokens - single user setup
user_tokens = {}

# Validate credentials on startup
if not CLIENT_ID or not CLIENT_SECRET:
    print("WARNING: GOOGLE_GMAIL_CLIENT_ID or GOOGLE_GMAIL_CLIENT_SECRET not set in environment variables!")
    print("Please set these variables in your .env file for Gmail authentication to work.")

async def refresh_access_token(email: str):
    """Refresh the access token using the refresh token"""
    if email not in user_tokens or not user_tokens[email].get("refresh_token"):
        return False
    
    refresh_token = user_tokens[email]["refresh_token"]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            user_tokens[email]["access_token"] = data.get("access_token")
            return True
    
    return False

async def get_valid_token(email: str):
    """Get a valid access token, refreshing if necessary"""
    if email not in user_tokens or not user_tokens[email].get("access_token"):
        return None
    
    # Try with current token first
    access_token = user_tokens[email]["access_token"]
    
    # Test if token is valid
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/gmail/v1/users/me/profile",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 200:
            return access_token
        
        # Token expired, try to refresh
        if response.status_code == 401:
            if await refresh_access_token(email):
                return user_tokens[email]["access_token"]
    
    return None


@mcp.tool()
async def gmail_generate_auth_url(email: str = DEFAULT_USER_EMAIL):
    """
    Generate Google OAuth 2.0 authentication URL for Gmail. Returns the full URL that the user must visit in their browser.
    
    Args:
        email: The email address for the user (default: mahdiharoun44@gmail.com)
    
    Returns:
        str: The complete OAuth URL to visit for authentication
    """
    print(f"Generating auth URL for email: {email}")
    print(f"CLIENT_ID: {'SET' if CLIENT_ID else 'NOT SET'}")
    print(f"CLIENT_SECRET: {'SET' if CLIENT_SECRET else 'NOT SET'}")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        return "ERROR: Gmail OAuth credentials not configured. Please set GOOGLE_GMAIL_CLIENT_ID and GOOGLE_GMAIL_CLIENT_SECRET in .env file"
    
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": " ".join(SCOPES),
        "state": email,
        "login_hint": email
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"Generated URL: {url[:100]}...")
    return {"auth_url": url}


@mcp.tool()
async def gmail_check_auth_status(email: str = DEFAULT_USER_EMAIL):
    """
    Check if the user is authenticated for Gmail
    
    Args:
        email: User's email address (default: mahdiharoun44@gmail.com)
    """
    token = await get_valid_token(email)
    if token:
        return {"authenticated": True, "email": email}
    return {"authenticated": False, "email": email, "message": "Use generate_auth_url() to authenticate"}

@mcp.tool()
async def gmail_revoke_access(email: str = DEFAULT_USER_EMAIL):
    """
    Revoke Gmail authentication for a specific email
    
    Args:
        email: User's email address to revoke (default: mahdiharoun44@gmail.com)
    """
    if email in user_tokens:
        access_token = user_tokens[email].get("access_token")
        if access_token:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": access_token}
                    )
                except Exception:
                    pass
        
        del user_tokens[email]
        return {"success": True, "message": f"Access revoked for {email}"}
    return {"success": False, "message": f"No authentication found for {email}"}

@mcp.custom_route("/oauth2callback", methods=["GET"])
async def handle_oauth_callback(ctx: Context):
    """Handle the OAuth callback from Google"""
    code = ctx.query_params.get("code")
    email = ctx.query_params.get("state", DEFAULT_USER_EMAIL)
    
    if not code:
        return HTMLResponse("<h1>Error: No authorization code received</h1>", status_code=400)
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            user_tokens[email] = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token")
            }
            return HTMLResponse(f"<h1>Success! {email} authenticated for Gmail. You can close this window now.</h1>")
        else:
            return HTMLResponse(f"<h1>Error: {response.text}</h1>", status_code=400)

@mcp.tool()
async def list_messages(email: str = DEFAULT_USER_EMAIL, max_results: int = 10, query: str = ""):
    """
    List messages from Gmail inbox
    
    Args:
        email: User's email address (default: mahdiharoun44@gmail.com)
        max_results: Maximum number of messages to return (default: 10)
        query: Gmail search query (e.g., "from:someone@example.com", "is:unread", "subject:meeting")
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Use generate_auth_url() first"}
    
    async with httpx.AsyncClient() as client:
        params = {"maxResults": max_results}
        if query:
            params["q"] = query
        
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            
            result = []
            for msg in messages:
                msg_id = msg.get("id")
                # Get message details
                msg_response = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date"]}
                )
                
                if msg_response.status_code == 200:
                    msg_data = msg_response.json()
                    headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
                    result.append({
                        "id": msg_id,
                        "from": headers.get("From", ""),
                        "to": headers.get("To", ""),
                        "subject": headers.get("Subject", ""),
                        "date": headers.get("Date", ""),
                        "snippet": msg_data.get("snippet", "")
                    })
            
            return {"messages": result, "count": len(result)}
        else:
            return {"error": response.text}

@mcp.tool()
async def read_message(message_id: str, email: str = DEFAULT_USER_EMAIL):
    """
    Read a specific message from Gmail
    
    Args:
        message_id: The ID of the message to read
        email: User's email address (default: mahdiharoun44@gmail.com)
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Use generate_auth_url() first"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"}
        )
        
        if response.status_code == 200:
            msg_data = response.json()
            headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
            
            # Extract body
            body = ""
            if "parts" in msg_data.get("payload", {}):
                for part in msg_data["payload"]["parts"]:
                    if part.get("mimeType") == "text/plain":
                        body_data = part.get("body", {}).get("data", "")
                        if body_data:
                            body = base64.urlsafe_b64decode(body_data).decode("utf-8")
                            break
            else:
                body_data = msg_data.get("payload", {}).get("body", {}).get("data", "")
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode("utf-8")
            
            return {
                "id": message_id,
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "body": body,
                "snippet": msg_data.get("snippet", "")
            }
        else:
            return {"error": response.text}

@mcp.tool()
async def send_email(to: str, subject: str, body: str, email: str = DEFAULT_USER_EMAIL):
    """
    Send an email via Gmail
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text)
        email: Sender's email address (default: mahdiharoun44@gmail.com)
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Use generate_auth_url() first"}
    
    # Create message
    message = MIMEText(body)
    message['to'] = to
    message['from'] = email
    message['subject'] = subject
    
    # Encode message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"raw": raw_message}
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message_id": result.get("id"),
                "thread_id": result.get("threadId"),
                "message": f"Email sent successfully to {to}"
            }
        else:
            return {"error": response.text}



@mcp.tool()
async def send_email_with_attachment(
    to: str,
    subject: str,
    body: str,
    attachment_s3_key: str,
    thread_id: str,
    bucket_name: str = "synapse-openapi-schemas",
    email: str = DEFAULT_USER_EMAIL
):
    """
    Send an email via Gmail with an attachment from S3 (in-memory).
    """
    # Get OAuth token
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Use gmail_generate_auth_url() first"}

    # Download attachment from S3 in-memory
    s3 = boto3.client("s3", region_name="eu-central-1")
    try:
        attachment_buffer = io.BytesIO()
        s3.download_fileobj(bucket_name, attachment_s3_key, attachment_buffer)
        attachment_buffer.seek(0)
        filename = os.path.basename(attachment_s3_key)
    except Exception as e:
        return {"error": f"Failed to download attachment from S3: {str(e)}"}

    # Determine content type
    content_type, _ = mimetypes.guess_type(filename)
    if content_type is None:
        content_type = "application/octet-stream"
    main_type, sub_type = content_type.split("/", 1)

    # Create multipart message
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = email
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Attach S3 file
    try:
        if main_type == "text":
            attachment = MIMEText(attachment_buffer.read().decode("utf-8"), _subtype=sub_type)
        else:
            attachment = MIMEBase(main_type, sub_type)
            attachment.set_payload(attachment_buffer.read())
            encoders.encode_base64(attachment)
        attachment.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(attachment)
    except Exception as e:
        return {"error": f"Failed to attach file: {str(e)}"}

    # Convert to RFC822
    rfc822_message = message.as_bytes()

    # Send via Gmail simple upload
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.googleapis.com/upload/gmail/v1/users/me/messages/send?uploadType=media",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "message/rfc822",
                "Content-Length": str(len(rfc822_message)),
            },
            content=rfc822_message
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "message_id": result.get("id"),
                "thread_id": result.get("threadId"),
                "message": f"Email with attachment '{filename}' sent successfully to {to}"
            }
        else:
            return {"error": f"Failed to send email: {response.status_code} - {response.text}"}


@mcp.tool()
async def search_messages(search_query: str, email: str = DEFAULT_USER_EMAIL, max_results: int = 20):
    """
    Search for messages in Gmail using Gmail search syntax
    
    Args:
        search_query: Gmail search query (e.g., "from:boss@company.com subject:urgent", "is:unread after:2025/11/01")
        email: User's email address (default: mahdiharoun44@gmail.com)
        max_results: Maximum number of results (default: 20)
    """
    return await list_messages(email=email, max_results=max_results, query=search_query)


@mcp.tool()
async def list_attachments(message_id: str, email: str = DEFAULT_USER_EMAIL):
    """
    List all attachments in a message
    
    Args:
        message_id: The ID of the message
        email: User's email address (default: mahdiharoun44@gmail.com)
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Use generate_auth_url() first"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"format": "full"}
        )
        
        if response.status_code == 200:
            msg_data = response.json()
            attachments = []
            
            def extract_attachments(parts):
                for part in parts:
                    if part.get("filename") and part.get("body", {}).get("attachmentId"):
                        attachments.append({
                            "filename": part.get("filename"),
                            "mimeType": part.get("mimeType"),
                            "size": part.get("body", {}).get("size", 0),
                            "attachmentId": part.get("body", {}).get("attachmentId")
                        })
                    if "parts" in part:
                        extract_attachments(part["parts"])
            
            if "parts" in msg_data.get("payload", {}):
                extract_attachments(msg_data["payload"]["parts"])
            
            return {
                "message_id": message_id,
                
                "attachments": attachments,
                "count": len(attachments)
            }
        else:
            return {"error": response.text}

@mcp.tool()
async def download_attachment(message_id: str, attachment_id: str, save_path: str, email: str = DEFAULT_USER_EMAIL):
    """
    Download an attachment from a Gmail message
    
    Args:
        message_id: The ID of the message containing the attachment
        attachment_id: The ID of the attachment (get from list_attachments)
        save_path: Full path where to save the file (e.g., "/tmp/document.pdf")
        email: User's email address (default: mahdiharoun44@gmail.com)
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Use generate_auth_url() first"}
    
    async with httpx.AsyncClient() as client:
        # Get attachment data
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 200:
            attachment_data = response.json()
            data = attachment_data.get("data", "")
            
            # Decode base64 data
            file_data = base64.urlsafe_b64decode(data)
            
            # Save to file
            try:
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                with open(save_path, "wb") as f:
                    f.write(file_data)
                
                return {
                    "success": True,
                    "saved_to": save_path,
                    "size": len(file_data),
                    "message": f"Attachment downloaded successfully to {save_path}"
                }
            except Exception as e:
                return {"error": f"Failed to save file: {str(e)}"}
        else:
            return {"error": response.text}





# Run the server
if __name__ == "__main__":
    mcp.run(transport="sse")


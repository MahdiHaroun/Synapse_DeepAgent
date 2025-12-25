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
from datetime import datetime, timedelta
import logging
from database import SessionLocal, engine, Base
from models import GmailToken
import os
import httpx

logger = logging.getLogger(__name__)

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
#DEFAULT_USER_EMAIL = "mahdiharoun44@gmail.com"

# Initialize database tables
def init_token_storage():
    """Create gmail_tokens table if it doesn't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Gmail token storage initialized")
    except Exception as e:
        logger.error(f"Failed to initialize token storage: {e}")

# Initialize on startup
init_token_storage()

# Validate credentials on startup
if not CLIENT_ID or not CLIENT_SECRET:
    print("WARNING: GOOGLE_GMAIL_CLIENT_ID or GOOGLE_GMAIL_CLIENT_SECRET not set in environment variables!")
    print("Please set these variables in your .env file for Gmail authentication to work.")

def save_tokens(email: str, access_token: str, refresh_token: str, expires_in: int):
    """Save tokens to database with expiry timestamp"""
    db = SessionLocal()
    try:
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        
        # Check if token exists
        token = db.query(GmailToken).filter(GmailToken.email == email).first()
        
        if token:
            # Update existing token
            token.access_token = access_token
            token.refresh_token = refresh_token
            token.expires_at = expires_at
            token.updated_at = datetime.now()
        else:
            # Create new token
            token = GmailToken(
                email=email,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at
            )
            db.add(token)
        
        db.commit()
        logger.info(f"Tokens saved for {email}, expires at {expires_at}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save tokens for {email}: {e}")
        return False
    finally:
        db.close()

def get_stored_tokens(email: str):
    """Retrieve tokens from database"""
    db = SessionLocal()
    try:
        token = db.query(GmailToken).filter(GmailToken.email == email).first()
        if token:
            return {
                "access_token": token.access_token,
                "refresh_token": token.refresh_token,
                "expires_at": token.expires_at
            }
        return None
    except Exception as e:
        logger.error(f"Failed to get tokens for {email}: {e}")
        return None
    finally:
        db.close()

def delete_tokens(email: str):
    """Delete tokens from database"""
    db = SessionLocal()
    try:
        token = db.query(GmailToken).filter(GmailToken.email == email).first()
        if token:
            db.delete(token)
            db.commit()
            logger.info(f"Tokens deleted for {email}")
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete tokens for {email}: {e}")
        return False
    finally:
        db.close()

async def refresh_access_token(email: str):
    """Refresh the access token using the refresh token"""
    tokens = get_stored_tokens(email)
    if not tokens or not tokens.get("refresh_token"):
        logger.warning(f"No refresh token found for {email}")
        return False
    
    refresh_token = tokens["refresh_token"]
    
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
            # Save refreshed token (refresh_token stays the same)
            expires_in = data.get("expires_in", 3600)
            save_tokens(email, data.get("access_token"), refresh_token, expires_in)
            logger.info(f"Access token refreshed for {email}")
            return True
        else:
            logger.error(f"Failed to refresh token for {email}: {response.status_code} - {response.text}")
            # If invalid_grant, delete tokens to force re-auth
            if "invalid_grant" in response.text:
                delete_tokens(email)
    
    return False

async def get_valid_token(email: str):
    """Get a valid access token, refreshing if necessary based on expiry timestamp"""
    tokens = get_stored_tokens(email)
    
    if not tokens:
        logger.info(f"No tokens found for {email}")
        return None
    
    # Check if token is expired based on stored timestamp
    expires_at = tokens["expires_at"]
    now = datetime.now()
    
    # Add 5 minute buffer before expiry
    if now >= (expires_at - timedelta(minutes=5)):
        logger.info(f"Token expired for {email}, refreshing...")
        if await refresh_access_token(email):
            # Get updated token
            tokens = get_stored_tokens(email)
            return tokens["access_token"] if tokens else None
        else:
            logger.error(f"Failed to refresh token for {email}")
            return None
    
    # Token is still valid
    return tokens["access_token"]


@mcp.tool()
async def gmail_generate_auth_url(email: str ):
    """
    Generate Google OAuth 2.0 authentication URL for Gmail. Only needed for first-time authentication.
    
    Args:
        email: The email address for the user (default: mahdiharoun44@gmail.com)
    
    Returns:
        dict: Contains auth_url if authentication needed, or status if already authenticated
    """
    logger.info(f"Checking auth status for {email}")
    
    # Check if user already has valid tokens
    tokens = get_stored_tokens(email)
    if tokens:
        logger.info(f"User {email} already authenticated")
        return {
            "authenticated": True,
            "email": email,
            "message": "Already authenticated. No need to re-authenticate."
        }
    
    logger.info(f"Generating auth URL for {email} (first-time authentication)")
    
    if not CLIENT_ID or not CLIENT_SECRET:
        return {"error": "Gmail OAuth credentials not configured. Please set GOOGLE_GMAIL_CLIENT_ID and GOOGLE_GMAIL_CLIENT_SECRET in .env file"}
    
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "access_type": "offline",
        "scope": " ".join(SCOPES),
        "state": email,
        "login_hint": email
    }
    # Only add prompt=consent for first-time auth (no stored tokens)
    # This ensures we get a refresh token on first auth
    if not tokens:
        params["prompt"] = "consent"
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    logger.info("Generated URL for first-time auth")
    return {"auth_url": url, "first_time": True}


@mcp.tool()
async def gmail_check_auth_status(email: str ):
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
async def gmail_revoke_access(email: str):
    """
    Revoke Gmail authentication for a specific email
    
    Args:
        email: User's email address to revoke (default: mahdiharoun44@gmail.com)
    """
    tokens = get_stored_tokens(email)
    if tokens:
        access_token = tokens.get("access_token")
        if access_token:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": access_token}
                    )
                    logger.info(f"Revoked access token for {email} at Google")
                except Exception as e:
                    logger.warning(f"Failed to revoke at Google: {e}")
        
        # Delete from database
        if delete_tokens(email):
            return {"success": True, "message": f"Access revoked for {email}"}
        else:
            return {"success": False, "message": f"Failed to delete tokens for {email}"}
    return {"success": False, "message": f"No authentication found for {email}"}

@mcp.custom_route("/oauth2callback", methods=["GET"])
async def handle_oauth_callback(ctx: Context):
    """Handle the OAuth callback from Google"""
    code = ctx.query_params.get("code")
    email = ctx.query_params.get("state")
    
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
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in", 3600)
            
            if not refresh_token:
                logger.error(f"No refresh token received for {email}")
                return HTMLResponse(
                    "<h1>Error: No refresh token received. Please revoke access and try again.</h1>",
                    status_code=400
                )
            
            # Save tokens to database
            if save_tokens(email, access_token, refresh_token, expires_in):
                logger.info(f"Tokens saved successfully for {email}")
                return HTMLResponse(
                    f"<h1>✅ Success! {email} authenticated for Gmail.</h1>"
                    f"<p>You can close this window now. You won't need to re-authenticate.</p>"
                )
            else:
                return HTMLResponse("<h1>Error: Failed to save tokens</h1>", status_code=500)
        else:
            logger.error(f"OAuth error: {response.text}")
            return HTMLResponse(f"<h1>Error: {response.text}</h1>", status_code=400)

@mcp.tool()
async def list_messages(email: str, max_results: int = 10, query: str = ""):
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
async def read_message(message_id: str, email: str):
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
async def send_email(to: str, subject: str, body: str, email: str ):
    """
    Send an email via Gmail
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text) "required"
        email: Sender's email address 
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
    attachment_relative_path: str,
    thread_id: str,
    email: str = "mahdiharoun44@gmail.com",
):
    """
    Send an email via Gmail with an attachment from the shared Docker volume.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        attachment_relative_path: Path relative to /shared/{thread_id}/ (e.g., 'documents/file.pdf', 'analysis_images/chart.png', 'saved_downloads/file.xlsx')
        thread_id: Thread ID for locating the file
        email: Sender's email address (default: mahdiharoun44@gmail.com)
    """
    # Get OAuth token
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Use gmail_generate_auth_url() first"}

    # Build full path from thread_id and relative path
    attachment_path = f"/shared/{thread_id}/{attachment_relative_path}"
    
    # Extract filename from relative path
    attachment_name = os.path.basename(attachment_relative_path)

    if not os.path.exists(attachment_path):
        return {"error": f"Attachment not found at {attachment_path}"}

    # Detect MIME type
    content_type, _ = mimetypes.guess_type(attachment_path)
    if content_type is None:
        content_type = "application/octet-stream"
    main_type, sub_type = content_type.split("/", 1)

    # Build email
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = email
    message["subject"] = subject
    message.attach(MIMEText(body, "plain"))

    # Attach file from shared volume
    try:
        with open(attachment_path, "rb") as f:
            file_data = f.read()

        attachment = MIMEBase(main_type, sub_type)
        attachment.set_payload(file_data)
        encoders.encode_base64(attachment)

        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment_name
        )

        message.attach(attachment)

    except Exception as e:
        return {"error": f"Failed to attach file: {str(e)}"}

    # Convert to RFC822
    rfc822_message = message.as_bytes()

    # Send via Gmail API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.googleapis.com/upload/gmail/v1/users/me/messages/send?uploadType=media",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "message/rfc822",
            },
            content=rfc822_message
        )

    if response.status_code == 200:
        result = response.json()
        return {
            "success": True,
            "message_id": result.get("id"),
            "thread_id": result.get("threadId"),
            "message": f"Email with attachment '{attachment_name}' sent successfully to {to}"
        }
    else:
        return {"error": f"Failed to send email: {response.status_code} - {response.text}"}





@mcp.tool()
async def search_messages(search_query: str, email: str, max_results: int = 20):
    """
    Search for messages in Gmail using Gmail search syntax
    
    Args:
        search_query: Gmail search query (e.g., "from:boss@company.com subject:urgent", "is:unread after:2025/11/01")
        email: User's email address (default: mahdiharoun44@gmail.com)
        max_results: Maximum number of results (default: 20)
    """
    return await list_messages(email=email, max_results=max_results, query=search_query)


@mcp.tool()
async def list_attachments(message_id: str, email: str):
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
async def download_attachment(message_id: str, attachment_id: str, save_path: str, email: str):
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
    Base.metadata.create_all(bind=engine)
    mcp.run(transport="sse")


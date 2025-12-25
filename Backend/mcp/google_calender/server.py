from mcp.server import FastMCP 
from mcp.server.fastmcp import Context
import httpx
from datetime import datetime, timedelta
from starlette.responses import HTMLResponse
import urllib.parse
from dotenv import load_dotenv
import os
from pathlib import Path
import logging
from database import SessionLocal, engine, Base
from models import CalendarToken

logger = logging.getLogger(__name__)

# Load .env from mounted volume
#load_dotenv("/app/.env")

env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)





# Initialize the MCP server
mcp = FastMCP("GoogleCalendar", host="0.0.0.0", port=3030)

# Google OAuth credentials
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:3030/oauth2callback"
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events"
]

# Initialize database tables
def init_db():
    """Initialize the calendar_tokens table if it doesn't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Calendar token storage initialized")
    except Exception as e:
        logger.error(f"Failed to initialize token storage: {e}")

# Initialize database on startup
init_db()

def save_tokens(email: str, access_token: str, refresh_token: str, expires_in: int):
    """Save or update tokens in the database"""
    db = SessionLocal()
    try:
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        # Check if token exists
        token = db.query(CalendarToken).filter(CalendarToken.email == email).first()
        
        if token:
            # Update existing token
            token.access_token = access_token
            if refresh_token:
                token.refresh_token = refresh_token
            token.expires_at = expires_at
            token.updated_at = datetime.utcnow()
        else:
            # Create new token
            token = CalendarToken(
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
    """Retrieve tokens from the database"""
    db = SessionLocal()
    try:
        token = db.query(CalendarToken).filter(CalendarToken.email == email).first()
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
    """Delete tokens from the database"""
    db = SessionLocal()
    try:
        token = db.query(CalendarToken).filter(CalendarToken.email == email).first()
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

async def refresh_access_token(email: str, refresh_token: str) -> dict:
    """Refresh the access token using the refresh token"""
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
            # Save the new access token
            expires_in = data.get("expires_in", 3600)
            save_tokens(email, data["access_token"], refresh_token, expires_in)
            return {"access_token": data["access_token"], "success": True}
        else:
            # If refresh fails (e.g., refresh token revoked), delete stored tokens
            if "invalid_grant" in response.text:
                delete_tokens(email)
            return {"success": False, "error": response.text}

async def get_valid_token(email: str) -> str:
    """Get a valid access token, refreshing if necessary"""
    tokens = get_stored_tokens(email)
    
    if not tokens:
        return None
    
    # Check if token is expired or will expire in the next 5 minutes
    expires_at = tokens["expires_at"]
    buffer_time = datetime.utcnow() + timedelta(minutes=5)
    
    if expires_at <= buffer_time:
        # Token expired or about to expire, refresh it
        if tokens["refresh_token"]:
            result = await refresh_access_token(email, tokens["refresh_token"])
            if result.get("success"):
                return result["access_token"]
            else:
                return None
        else:
            return None
    
    return tokens["access_token"]

@mcp.tool()
async def generate_auth_url(email: str):
    """
    Returns the Google OAuth 2.0 consent page URL.
    
    Args:
        email: the email address for the user who will the event be written for him
    """
    # Check if user already has valid tokens
    existing_token = await get_valid_token(email)
    if existing_token:
        return {"message": f"Already authenticated for {email}", "authenticated": True}
    
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    # Check if this is a first-time authentication
    tokens = get_stored_tokens(email)
    prompt_value = "consent" if not tokens else "select_account"

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url, "authenticated": False}

@mcp.tool()
async def check_auth_status(email: str):
    """
    Check if the user is authenticated
    
    Args:
        email: User's email address
    """
    token = await get_valid_token(email)
    if token:
        return {"authenticated": True, "email": email}
    return {"authenticated": False, "email": email}

@mcp.tool()
async def revoke_access(email: str):
    """
    Revoke authentication for a specific email
    
    Args:
        email: User's email address to revoke
    """
    tokens = get_stored_tokens(email)
    if tokens:
        # Revoke the token with Google
        access_token = tokens.get("access_token")
        if access_token:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": access_token}
                    )
                except Exception:
                    pass  # Continue even if revoke fails
        
        # Remove from database
        delete_tokens(email)
        return {"success": True, "message": f"Access revoked for {email}"}
    return {"success": False, "message": f"No authentication found for {email}"}

@mcp.custom_route("/oauth2callback", methods=["GET"])
async def handle_oauth_callback(ctx: Context):
    """Handle the OAuth callback from Google"""
    code = ctx.query_params.get("code")
    email = ctx.query_params.get("state")
    
    if not code or not email:
        return HTMLResponse("<h1>Error: No authorization code or email received</h1>", status_code=400)
    
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
            
            # Save tokens to database with expiry time
            save_tokens(email, access_token, refresh_token, expires_in)
            
            return HTMLResponse(f"<h1>Success! {email} authenticated. You can close this window now.</h1>")
        else:
            return HTMLResponse(f"<h1>Error: {response.text}</h1>", status_code=400)

@mcp.tool()
async def list_calendar_events(email: str, max_events: int = 10):
    """
    List upcoming events from your Google Calendar
    
    Args:
        email: User's email address
        max_events: Maximum number of events to return
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Please use generate_auth_url() first"}
    
    now = datetime.utcnow().isoformat() + "Z"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "maxResults": max_events,
                "timeMin": now,
                "singleEvents": True,
                "orderBy": "startTime"
            }
        )
        
        if response.status_code == 200:
            events = response.json().get("items", [])
            result = []
            for event in events:
                result.append({
                    "title": event.get("summary", "No title"),
                    "start": event.get("start", {}).get("dateTime", event.get("start", {}).get("date")),
                    "end": event.get("end", {}).get("dateTime", event.get("end", {}).get("date")),
                    "id": event.get("id")
                })
            return {"events": result}
        else:
            return {"error": response.text}

@mcp.tool()
async def add_calendar_event(
    email: str, title: str, start_time: str, end_time: str, description: str = "", file_url: str = "",
    Attachment_Title: str = "" , location: str = "" , organizer_email: str = "" , attendee_email: str = ""):
    """
    Add a new event to your Google Calendar
    
    Args:
        email: User's email address
        title: Event title (e.g., "Team Meeting")
        start_time: Start time (e.g., "2025-11-16T10:00:00")
        end_time: End time (e.g., "2025-11-16T11:00:00")
        description: Event description (optional)
        file_url: URL of the attachment file (optional)
        Attachment_Title: Title of the attachment (optional)
        location: Event location (optional)
        organizer_email: Organizer's email address (optional)
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Please use generate_auth_url() first"}
    
    event_data = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start_time, "timeZone": "UTC+3"},
        "end": {"dateTime": end_time, "timeZone": "UTC+3"}, 
        "attachments": [
            {
                "fileUrl": file_url,
                "title": Attachment_Title
            }
        ],
        "location": location,
        "organizer": {
            "email": organizer_email
        },
        "attendees": [
            {
                "email": attendee_email
            }
        ]
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json=event_data
        )
        
        if response.status_code == 200:
            event = response.json()
            return {
                "success": True,
                "event_id": event.get("id"),
                "link": event.get("htmlLink")
            }
        else:
            return {"error": response.text}

@mcp.tool()
async def delete_calendar_event(email: str, event_id: str):
    """
    Delete an event from your Google Calendar
    
    Args:
        email: User's email address
        event_id: The ID of the event to delete
    """
    access_token = await get_valid_token(email)
    if not access_token:
        return {"error": f"User {email} not authenticated. Please use generate_auth_url() first"}
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if response.status_code == 204:
            return {"success": True, "message": "Event deleted"}
        else:
            return {"error": response.text}


# Run the server
if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    mcp.run(transport="sse")


    #python -m Backend.mcp.aws_S3_server.server
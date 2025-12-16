from mcp.server import FastMCP 
from mcp.server.fastmcp import Context
import httpx
from datetime import datetime
from starlette.responses import HTMLResponse
import urllib.parse
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from mounted volume
load_dotenv("/app/.env")



"""env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)
"""

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

# Store tokens for multiple users - key is email address
user_tokens = {}

@mcp.tool()
async def generate_auth_url(email: str):
    """
    Returns the Google OAuth 2.0 consent page URL.
    
    Args:
        email: the email address for the user who will the event be written for him
    """
    base_url = "https://accounts.google.com/o/oauth2/v2/auth"

    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "scope": " ".join(SCOPES),
        "state": email
    }

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    return {"auth_url": url}

@mcp.tool()
async def check_auth_status(email: str):
    """
    Check if the user is authenticated
    
    Args:
        email: User's email address
    """
    if email in user_tokens and user_tokens[email].get("access_token"):
        return {"authenticated": True, "email": email}
    return {"authenticated": False, "email": email}

@mcp.tool()
async def revoke_access(email: str):
    """
    Revoke authentication for a specific email
    
    Args:
        email: User's email address to revoke
    """
    if email in user_tokens:
        # Optionally, revoke the token with Google
        access_token = user_tokens[email].get("access_token")
        if access_token:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": access_token}
                    )
                except Exception:
                    pass  # Continue even if revoke fails
        
        # Remove from local storage
        del user_tokens[email]
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
            user_tokens[email] = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token")
            }
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
    if email not in user_tokens or not user_tokens[email].get("access_token"):
        return {"error": f"User {email} not authenticated. Please use generate_auth_url() first"}
    
    access_token = user_tokens[email]["access_token"]
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
    if email not in user_tokens or not user_tokens[email].get("access_token"):
        return {"error": f"User {email} not authenticated. Please use generate_auth_url() first"}
    
    access_token = user_tokens[email]["access_token"]
    
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
    if email not in user_tokens or not user_tokens[email].get("access_token"):
        return {"error": f"User {email} not authenticated. Please use generate_auth_url() first"}
    
    access_token = user_tokens[email]["access_token"]
    
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
    mcp.run(transport="sse")


    #python -m Backend.mcp.aws_S3_server.server
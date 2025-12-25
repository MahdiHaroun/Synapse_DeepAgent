from mcp.server.fastmcp import FastMCP
import random 
import resend
import os
from pathlib import Path
from dotenv import load_dotenv
import redis 

# Load .env from mounted volume
#load_dotenv("/app/.env")
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Initialize Redis client
# Use environment variable or default to docker service name
redis_host = os.getenv("REDIS_HOST", "redis")
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

# Initialize Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")

mcp = FastMCP("Auth" , host="0.0.0.0", port=3060)


def generate_otp():
    return random.randint(100000, 999999)


@mcp.tool()
async def clear_all_otps(email: str):
    """Clear all stored OTPs for a specific email (testing only)"""

    # Build Redis key for this email
    key = f"otp:{email.lower().strip()}"

    if redis_client.exists(key):
        redis_client.delete(key)
        return {"status": f"Cleared OTP for {email}"}

    return {"status": f"No OTP found for {email}"}

@mcp.tool()
async def send_otp(action: str, email: str):
    """Generate and send OTP to user's email"""
    
    otp = generate_otp()
    
    # Store in Redis with 5 minute expiration
    redis_key = f"otp:{email}"
    redis_client.setex(redis_key, 300, str(otp))  # 300 seconds TTL
    
    print(f"Sending OTP {otp} to email {email}") 
     
    resend.Emails.send({
        "from": "noreply@optichoice.me",
        "to": [email],
        "subject": action,
        "html": f"<p>Your OTP code to perform {action} is: <strong>{otp}</strong></p>"
    })
    
    return {"status": "OTP sent"}


@mcp.tool()
def verify_otp(otp: str, email: str) -> dict:
    """
    Verify provided OTP code.
    
    Args:
        otp: The 6-digit OTP code to verify
        email: User's email address (default: mahdiharoun44@gmail.com)
    
    Returns:
        dict: Verification result with verified status and reason
    """
    print(f"Verifying OTP for {email}: {otp}")
    
    redis_key = f"otp:{email}"
    stored_otp = redis_client.get(redis_key)
    
    if not stored_otp:
        return {"verified": False, "reason": f"No OTP found for {email}. Please request OTP first using send_otp or OTP expired."}

    # Convert both to string for comparison and strip whitespace
    provided_otp = str(otp).strip()
    
    if stored_otp != provided_otp:
        print(f"OTP mismatch: stored={stored_otp}, provided={provided_otp}")
        return {"verified": False, "reason": "OTP invalid. Please check the code and try again."}

    # Delete OTP after successful verification
    redis_client.delete(redis_key)

    return {"verified": True, "email": email, "message": "OTP verified successfully!"}
    

if __name__ == "__main__":
    mcp.run(transport="sse")



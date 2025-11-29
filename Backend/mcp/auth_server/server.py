from mcp.server.fastmcp import FastMCP
import random 
import resend
import datetime
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Initialize Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")

mcp = FastMCP("Auth" , host="0.0.0.0", port=3060)

otp_storage = {}   # email -> {"otp":1234, "expires":datetime}

def generate_otp():
    return random.randint(100000, 999999)
@mcp.tool()
async def clear_all_otps():
    """Clear all stored OTPs (for testing purposes)"""
    otp_storage.clear()
    return {"status": "All OTPs cleared"}

@mcp.tool()
async def send_otp(action: str):
    """Generate and send OTP to user's email (simulated)"""
    email = "mahdiharoun44@gmail.com"
    otp = generate_otp()
    expires = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)

    otp_storage[email] = {
        "otp": otp,
        "expires": expires
    }
    print(f"Sending OTP {otp} to email {email}") 
     
            
    resend.Emails.send({
            "from": "noreply@optichoice.me",
            "to": "mahdiharoun44@gmail.com",
            "subject": action,
            "html": f"<p>Your OTP code to perform {action} is: <strong>{otp}</strong></p>"
        })
    
    return {"status": "OTP sent"}


@mcp.tool()
def verify_otp(otp: str, email: str = "mahdiharoun44@gmail.com") -> dict:
    """
    Verify provided OTP code.
    
    Args:
        otp: The 6-digit OTP code to verify
        email: User's email address (default: mahdiharoun44@gmail.com)
    
    Returns:
        dict: Verification result with verified status and reason
    """
    print(f"Verifying OTP for {email}: {otp}")
    print(f"Current OTP storage: {otp_storage}")
    
    if email not in otp_storage:
        return {"verified": False, "reason": f"No OTP generated for {email}. Please request OTP first using send_otp."}

    data = otp_storage[email]
    
    current_time = datetime.datetime.utcnow()
    print(f"Current time: {current_time}, Expires: {data['expires']}")

    if current_time > data["expires"]:
        del otp_storage[email]
        return {"verified": False, "reason": "OTP expired. Please request a new OTP."}

    # Convert both to string for comparison and strip whitespace
    stored_otp = str(data["otp"])
    provided_otp = str(otp).strip()
    
    if stored_otp != provided_otp:
        print(f"OTP mismatch: stored={stored_otp}, provided={provided_otp}")
        return {"verified": False, "reason": "OTP invalid. Please check the code and try again."}

    # Delete OTP after successful verification
    del otp_storage[email]

    return {"verified": True, "email": email, "message": "OTP verified successfully!"}
    

if __name__ == "__main__":
    mcp.run(transport="sse")



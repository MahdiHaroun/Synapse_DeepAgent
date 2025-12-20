"""
Test script for sending email with attachment using Resend API
"""
import os
import boto3
import resend
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set AWS credentials
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")

# Set Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")

def test_send_email_with_s3_attachment():
    """Test sending email with attachment from S3"""
    
    # Configuration
    s3_key = "schedule/5b5e01795ab147beb16fd3aa3d27307e.pdf"  # Change to your actual S3 key
    bucket_name = "synapse-openapi-schemas"
    
    print(f"Testing email with attachment from S3...")
    print(f"Bucket: {bucket_name}")
    print(f"Key: {s3_key}")
    
    try:
        # Step 1: Download from S3
        print("\n1. Downloading file from S3...")
        s3 = boto3.client("s3", region_name="eu-central-1")
        
        # Check if file exists
        try:
            s3.head_object(Bucket=bucket_name, Key=s3_key)
            print("   ✓ File exists in S3")
        except Exception as e:
            print(f"   ✗ File not found: {e}")
            return
        
        # Download file content
        response = s3.get_object(Bucket=bucket_name, Key=s3_key)
        attachment_content = response['Body'].read()
        filename = os.path.basename(s3_key)
        print(f"   ✓ Downloaded {len(attachment_content)} bytes")
        print(f"   ✓ Filename: {filename}")
        
        # Step 2: Prepare email
        print("\n2. Preparing email...")
        params = {
            "from": "noreply@optichoice.me",
            "to": ["mahdiharoun44@gmail.com"],
            "subject": "Test Email with PDF Attachment",
            "html": "<h1>Test Email</h1><p>This is a test email with a PDF attachment from S3.</p>"
        }
        
        # Step 3: Add attachment
        print("\n3. Adding attachment...")
        # Resend requires base64 encoding for content
        attachment_base64 = base64.b64encode(attachment_content).decode('utf-8')
        params["attachments"] = [{
            "filename": filename,
            "content": attachment_base64
        }]
        print(f"   ✓ Attachment added: {filename}")
        print(f"   ✓ Base64 encoded: {len(attachment_base64)} chars")
        
        # Step 4: Send email
        print("\n4. Sending email via Resend...")
        result = resend.Emails.send(params)
        
        print("\n✅ SUCCESS!")
        print(f"   Email ID: {result.get('id')}")
        print(f"   Message: Email sent successfully")
        
        return {"success": True, "result": result}
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def test_send_simple_email():
    """Test sending a simple email without attachment"""
    
    print("Testing simple email without attachment...")
    
    try:
        params = {
            "from": "noreply@optichoice.me",
            "to": ["mahdiharoun44@gmail.com"],
            "subject": "Simple Test Email",
            "html": "<h1>Hello!</h1><p>This is a simple test email without attachments.</p>"
        }
        
        result = resend.Emails.send(params)
        
        print("\n✅ SUCCESS!")
        print(f"   Email ID: {result.get('id')}")
        
        return {"success": True, "result": result}
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    print("="*60)
    print("RESEND EMAIL TEST SCRIPT")
    print("="*60)
    
    # Test 1: Simple email
    print("\n" + "="*60)
    print("TEST 1: Simple Email (No Attachment)")
    print("="*60)
    result1 = test_send_simple_email()
    
    # Test 2: Email with S3 attachment
    print("\n" + "="*60)
    print("TEST 2: Email with S3 Attachment")
    print("="*60)
    result2 = test_send_email_with_s3_attachment()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Simple Email: {'✅ PASS' if result1['success'] else '❌ FAIL'}")
    print(f"Email with Attachment: {'✅ PASS' if result2['success'] else '❌ FAIL'}")
    print("="*60)

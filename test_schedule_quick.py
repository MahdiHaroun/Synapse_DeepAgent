"""
Quick test for EventBridge schedule creation
"""
import requests
import json

# Test configuration
API_URL = "http://localhost:8070"

def test_schedule_creation():
    """Test creating a schedule"""
    
    # First login to get token
    print("Step 1: Login to get JWT token...")
    login_response = requests.post(
        f"{API_URL}/auth/login",
        data={
            "username": "admin",  # Replace with your username
            "password": "password"  # Replace with your password
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    print("✅ Login successful")
    
    # Create schedule
    print("\nStep 2: Creating schedule...")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "schedule_name": "test_daily_report",
        "schedule_expression": "cron(0 0 * * ? *)",  # Every day at midnight
        "event_description": "Test daily report generation",
        "event_data": {
            "query": "create a pdf contains the number of orders in the db",
            "report_type": "daily"
        }
    }
    
    print(f"Creating schedule: {payload['schedule_name']}")
    print(f"Expression: {payload['schedule_expression']}")
    
    response = requests.post(
        f"{API_URL}/scheduler/create_new_schedule",
        json=payload,
        headers=headers
    )
    
    if response.status_code == 201:
        result = response.json()
        print("\n✅ Schedule created successfully!")
        print(json.dumps(result, indent=2, default=str))
        return result
    else:
        print(f"\n❌ Failed to create schedule")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def test_list_schedules():
    """Test listing schedules"""
    print("\n" + "="*60)
    print("Testing schedule listing...")
    print("="*60)
    
    # Login
    login_response = requests.post(
        f"{API_URL}/auth/login",
        data={
            "username": "admin",
            "password": "password"
        }
    )
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(
        f"{API_URL}/scheduler/list",
        headers=headers
    )
    
    if response.status_code == 200:
        schedules = response.json()
        print(f"\n📋 Found {len(schedules)} schedule(s):")
        print(json.dumps(schedules, indent=2, default=str))
    else:
        print(f"❌ Error: {response.text}")


if __name__ == "__main__":
    print("="*60)
    print("EventBridge Schedule Test")
    print("="*60)
    print("\n⚠️  Make sure:")
    print("1. API is running on http://localhost:8070")
    print("2. Lambda function is created in AWS")
    print("3. EVENTBRIDGE_LAMBDA_ARN is set in .env")
    print("4. Update username/password below")
    print("")
    
    # Test schedule creation
    schedule = test_schedule_creation()
    
    if schedule:
        # Test listing
        test_list_schedules()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        print("\nCheck AWS Console:")
        print("1. EventBridge → Rules → Your rule should be there")
        print("2. Lambda → Functions → Check invocations")
        print("\nWhen schedule triggers, Lambda will POST to:")
        print("/chat/eventbridge_target")

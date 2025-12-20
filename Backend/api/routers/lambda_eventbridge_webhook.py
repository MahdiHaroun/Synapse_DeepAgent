import json
import urllib3

def lambda_handler(event, context):
    """
    Simple Lambda function that receives EventBridge events
    and forwards them to your API endpoint
    """
    
    # Get webhook URL and data from event
    webhook_url = event.get('webhook_url', 'http://your-domain.com/chat/eventbridge_target')
    
    # Remove webhook_url from event before sending
    event_copy = event.copy()
    event_copy.pop('webhook_url', None)
    
    # Send POST request to webhook
    http = urllib3.PoolManager()
    
    try:
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(event_copy),
            headers={'Content-Type': 'application/json' }
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Event forwarded successfully',
                'response_status': response.status
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }

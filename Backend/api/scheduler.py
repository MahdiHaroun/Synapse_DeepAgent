import boto3
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv("Backend/api/.env")


class EventBridgeScheduler:
    """Simple EventBridge Scheduler using Lambda as target"""
    
    def __init__(self):
        self.scheduler_client = boto3.client(
            'scheduler',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'eu-central-1'),
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        logger.info("EventBridge scheduler service initialized")
    
    def create_schedule(
        self,
        rule_name: str,
        schedule_expression: str,
        event_description: str,
        target_url: str,
        event_data: dict
    ) -> dict:
        """Create EventBridge Schedule with Lambda target"""
        try:
            # Get Lambda ARN
            lambda_arn = os.getenv("EVENTBRIDGE_LAMBDA_ARN")
            if not lambda_arn:
                return {
                    "success": False,
                    "error": "EVENTBRIDGE_LAMBDA_ARN not set in .env"
                }

            # Get Role ARN (required for EventBridge Scheduler)
            role_arn = os.getenv("EVENTBRIDGE_SCHEDULER_ROLE_ARN")
            if not role_arn:
                return {
                    "success": False,
                    "error": "EVENTBRIDGE_SCHEDULER_ROLE_ARN not set in .env. Run: ./setup_scheduler_role.sh"
                }
            dead_letter_queue_arn = os.getenv("EVENTBRIDGE_DEAD_LETTER_QUEUE_ARN")
            if not dead_letter_queue_arn:
                return {
                    "success": False,
                    "error": "EVENTBRIDGE_DEAD_LETTER_QUEUE_ARN not set in .env. set it to enable dead letter queue."
                }

            # Add metadata to event data
            event_data["eventbridge_rule_name"] = rule_name
            event_data["webhook_url"] = target_url
            
            # Create schedule
            response = self.scheduler_client.create_schedule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                ScheduleExpressionTimezone = "Asia/Amman",
                Description=event_description,
                State='ENABLED',
                FlexibleTimeWindow={'Mode': 'OFF'},
                Target={
                    'Arn': lambda_arn,
                    'DeadLetterConfig': {
                        "Arn": dead_letter_queue_arn
                    },
                    'RoleArn': role_arn,
                    'Input': json.dumps(event_data)
                }

            )
            
            logger.info(f"Schedule created: {rule_name}")
            return {
                "success": True,
                "rule_arn": response['ScheduleArn'],
                "rule_name": rule_name
            }

        except Exception as e:
            logger.error(f"Error creating schedule: {e}")
            return {"success": False, "error": str(e)}
        



    
    def delete_schedule(self, rule_name: str) -> dict:
        """Delete an EventBridge schedule"""
        try:
            self.scheduler_client.delete_schedule(
                Name=rule_name
            )
            logger.info(f"Deleted schedule: {rule_name}")
            
            return {
                'success': True,
                'message': f'Schedule deleted: {rule_name}'
            }
            
        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_schedules(self) -> list:
        """List all EventBridge schedules"""
        try:
            response = self.scheduler_client.list_schedules()
            schedules = []
            
            for schedule in response.get('Schedules', []):
                schedules.append({
                    'name': schedule['Name'],
                    'arn': schedule['Arn'],
                    'schedule': schedule.get('ScheduleExpression', 'N/A'),
                    'state': schedule['State']
                })
            
            return schedules
            
        except Exception as e:
            logger.error(f"Error listing schedules: {e}")
            return []
    
    def enable_schedule(self, rule_name: str) -> dict:
        """Enable a disabled schedule"""
        try:
            # Get existing schedule details
            existing = self.scheduler_client.get_schedule(
                Name=rule_name
            )
            
            # Update with new state
            self.scheduler_client.update_schedule(
                Name=rule_name,
                ScheduleExpression=existing['ScheduleExpression'],
                ScheduleExpressionTimezone=existing.get('ScheduleExpressionTimezone', 'Asia/Amman'),
                FlexibleTimeWindow=existing['FlexibleTimeWindow'],
                Target=existing['Target'],
                State='ENABLED',
                Description=existing.get('Description', '')
            )
            logger.info(f"Enabled schedule: {rule_name}")
            return {'success': True, 'message': f'Schedule enabled: {rule_name}'}
        except Exception as e:
            logger.error(f"Error enabling schedule: {e}")
            return {'success': False, 'error': str(e)}
    
    def disable_schedule(self, rule_name: str) -> dict:
        """Disable a schedule without deleting it"""
        try:
            # Get existing schedule details
            existing = self.scheduler_client.get_schedule(
                Name=rule_name
            )
            
            # Update with new state
            self.scheduler_client.update_schedule(
                Name=rule_name,
                ScheduleExpression=existing['ScheduleExpression'],
                ScheduleExpressionTimezone=existing.get('ScheduleExpressionTimezone', 'Asia/Amman'),
                FlexibleTimeWindow=existing['FlexibleTimeWindow'],
                Target=existing['Target'],
                State='DISABLED',
                Description=existing.get('Description', '')
            )
            
            return {'success': True, 'message': f'Schedule disabled: {rule_name}'}
        except Exception as e:
            logger.error(f"Error disabling schedule: {e}")
            return {'success': False, 'error': str(e)}

# Global EventBridge scheduler instance
eventbridge_scheduler = EventBridgeScheduler()
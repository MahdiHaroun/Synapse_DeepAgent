from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from Backend.api import models, schemas
from Backend.api.database import get_db
from Backend.api.auth import get_current_user
from Backend.api.scheduler import eventbridge_scheduler
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import logging
import os

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])
logger = logging.getLogger(__name__)


class CreateScheduleRequest(BaseModel):
    schedule_name: str
    schedule_expression: str  # e.g., "cron(0 10 * * ? *)" or "rate(5 minutes)"
    event_description: str
    event_data: dict = {}


class ScheduleResponse(BaseModel):
    id: int
    schedule_name: str
    schedule_expression: str
    event_description: str
    eventbridge_rule_arn: Optional[str]
    is_active: bool
    created_at: datetime


@router.post("/create_new_schedule", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_new_schedule(
    request: CreateScheduleRequest,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(get_current_user)
):
    """
    Create a new AWS EventBridge schedule
    
    Schedule Expression Examples:
    - Cron: "cron(0 10 * * ? *)" - Every day at 10:00 AM UTC
    - Cron: "cron(0/15 * * * ? *)" - Every 15 minutes
    - Cron: "cron(0 9 ? * MON-FRI *)" - Every weekday at 9:00 AM
    - Rate: "rate(5 minutes)" - Every 5 minutes
    - Rate: "rate(1 hour)" - Every hour
    - Rate: "rate(1 day)" - Every day
    
    Note: AWS EventBridge uses 6-field cron expressions (minute hour day month day_of_week year)
    """
    try:
        # Generate unique rule name
        rule_name = f"synapse_{request.schedule_name.replace(' ', '_')}_{current_user.id}_{datetime.now().timestamp()}".replace('.', '_')
        
        # API endpoint that will receive POST requests from EventBridge
        # Using /chat/eventbridge_target as the webhook endpoint
        webhook_url = os.getenv("EVENTBRIDGE_WEBHOOK_URL", "http://localhost:8070/chat/eventbridge_target")
        
        # Prepare event data with schedule metadata
        event_data = {
            "schedule_name": request.schedule_name,
            "schedule_expression": request.schedule_expression,
            "event_description": request.event_description,
            "admin_id": current_user.id,
            "task_data": request.event_data
        }
        
        # Create EventBridge rule
        result = eventbridge_scheduler.create_schedule(
            rule_name=rule_name,
            schedule_expression=request.schedule_expression,
            event_description=request.event_description,
            target_url=webhook_url,
            event_data=event_data
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create EventBridge schedule: {result.get('error')}"
            )
        
        # Save to database
        db_schedule = models.EventBridgeSchedule(
            admin_id=current_user.id,
            schedule_name=request.schedule_name,
            schedule_expression=request.schedule_expression,
            event_description=request.event_description,
            event_data=request.event_data,
            eventbridge_rule_name=rule_name,
            eventbridge_rule_arn=result['rule_arn'],
            is_active=True
        )
        
        db.add(db_schedule)
        db.commit()
        db.refresh(db_schedule)
        
        logger.info(f"Created schedule: {request.schedule_name} for user {current_user.id}")
        
        return db_schedule
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating schedule: {str(e)}"
        )


@router.get("/list", response_model=list[ScheduleResponse])
async def list_schedules(
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(get_current_user)
):
    """List all schedules for the current user"""
    schedules = db.query(models.EventBridgeSchedule).filter(
        models.EventBridgeSchedule.admin_id == current_user.id
    ).all()
    
    return schedules


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(get_current_user)
):
    """Delete a schedule"""
    schedule = db.query(models.EventBridgeSchedule).filter(
        models.EventBridgeSchedule.id == schedule_id,
        models.EventBridgeSchedule.admin_id == current_user.id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Delete from EventBridge
    result = eventbridge_scheduler.delete_schedule(schedule.eventbridge_rule_name)
    
    if not result['success']:
        logger.warning(f"Failed to delete EventBridge rule: {result.get('error')}")
    
    # Delete from database
    db.delete(schedule)
    db.commit()
    
    return {"message": f"Schedule {schedule.schedule_name} deleted successfully"}


@router.post("/{schedule_id}/disable")
async def disable_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(get_current_user)
):
    """Disable a schedule without deleting it"""
    schedule = db.query(models.EventBridgeSchedule).filter(
        models.EventBridgeSchedule.id == schedule_id,
        models.EventBridgeSchedule.admin_id == current_user.id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    
    result = eventbridge_scheduler.disable_schedule(schedule.eventbridge_rule_name)
    
    if not result['success']:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable schedule: {result.get('error')}"
        )
    
    # Update database
    schedule.is_active = False
    db.commit()
    
    return {"message": f"Schedule {schedule.schedule_name} disabled successfully"}


@router.post("/{schedule_id}/enable")
async def enable_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(get_current_user)
):
    """Enable a disabled schedule"""
    schedule = db.query(models.EventBridgeSchedule).filter(
        models.EventBridgeSchedule.id == schedule_id,
        models.EventBridgeSchedule.admin_id == current_user.id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Enable in EventBridge
    result = eventbridge_scheduler.enable_schedule(schedule.eventbridge_rule_name)
    
    if not result['success']:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable schedule: {result.get('error')}"
        )
    
    # Update database
    schedule.is_active = True
    db.commit()
    
    return {"message": f"Schedule {schedule.schedule_name} enabled successfully"}


@router.post("/webhook")
async def eventbridge_webhook(
    event_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint that receives POST requests from AWS EventBridge
    
    This is where EventBridge will send events when schedules trigger.
    You'll need to set this up as an API Destination in EventBridge.
    """
    try:
        logger.info(f"Received EventBridge webhook: {event_data}")
        
        # Extract schedule information from event
        # Process the event and trigger appropriate actions
        # For example, call your agent, send email, etc.
        
        # Log the execution
        # You can add logic here to execute the scheduled task
        
        return {
            "status": "success",
            "message": "Event received and processed",
            "received_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing EventBridge webhook: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing event: {str(e)}"
        )

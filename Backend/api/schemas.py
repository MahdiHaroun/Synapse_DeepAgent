from pydantic import BaseModel, EmailStr, Field, field_serializer, ConfigDict
from typing import Optional, Union
from datetime import datetime



class ChatRequest(BaseModel):
    """Chat request schema""" 
    message: str = Field(..., description="User message to the AI assistant")




class ChatResponse(BaseModel):
    """Chat response schema"""
    response: str = Field(..., description="AI assistant response")
    thread_id: str = Field(..., description="Thread ID for this conversation")
    timestamp: str = Field(..., description="Response timestamp")
    status: str = Field(default="success", description="Response status")
    total_tokens: Optional[int] = Field(None, description="Total tokens used in the conversation") 
    input_tokens: Optional[int] = Field(None, description="Input tokens used")
    cashe_tokens: Optional[int] = Field(None, description="Cached tokens used")
    output_tokens: Optional[int] = Field(None, description="Output tokens generated")

class AdminCreate(BaseModel):
    name: str
    email: EmailStr
    password: str


class AdminUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class Admin_Response(BaseModel):
    
    name: str 
    email: EmailStr
    
    
    
    class Config:
        from_attributes = True

class Token(Admin_Response):
    
    access_token: str
    token_type: str


class AdminOut(BaseModel):
    Confirmation: str


class AdminInfo(BaseModel):
    id: int
    username: str
    name: str
    email: EmailStr
    is_verified: bool

    class Config:
        from_attributes = True


class PrivilegeCreate(BaseModel):
    name: str = Field(..., description="Unique privilege name")
    description: Optional[str] = Field(None, description="Privilege description")


class PrivilegeUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated privilege name")
    description: Optional[str] = Field(None, description="Updated privilege description")


class PrivilegeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str = Field(..., description="Unique role name")
    privilege_ids: list[int] = Field(default=[], description="List of privilege IDs to attach to this role")


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated role name")
    privilege_ids: Optional[list[int]] = Field(None, description="Updated list of privilege IDs")


class RoleOut(BaseModel):
    id: int
    name: str
    privileges: list[PrivilegeOut] = []

    class Config:
        from_attributes = True

class Admin_login(BaseModel):   #used form instead
    email: EmailStr
    password: str


class TokenData(BaseModel):
    id: Optional[str] = None


class ThreadCreate(BaseModel):
    uuid: str


class ThreadOut(BaseModel):
    id: int
    uuid: str
    last_interaction: Optional[datetime]
    is_active: bool
    admin_id: int

    class Config:
        from_attributes = True
        json_encoders = {
            'datetime': lambda v: v.isoformat() if v else None
        }
    
    @classmethod
    def model_validate(cls, obj):
        if hasattr(obj, 'last_interaction') and obj.last_interaction:
            obj.last_interaction

class ProtocolCreate(BaseModel):
    sequence_description: str


class ScheduledTaskCreate(BaseModel):
    task_name: str = Field(..., description="Name of the scheduled task")
    task_type: str = Field(..., description="Type: 'cron', 'interval', or 'one_time'")
    task_description: Optional[str] = Field(None, description="Description of what the task does")
    
    # For cron tasks
    cron_expression: Optional[str] = Field(None, description="Cron expression (e.g., '0 9 * * *')")
    
    # For interval tasks
    interval_seconds: Optional[int] = Field(None, description="Interval in seconds")
    interval_minutes: Optional[int] = Field(None, description="Interval in minutes")
    interval_hours: Optional[int] = Field(None, description="Interval in hours")
    
    # For one_time tasks
    run_date: Optional[str] = Field(None, description="ISO datetime string for one-time execution")
    
    # Task data (what the agent should do)
    task_data: dict = Field(..., description="Task parameters (e.g., {'prompt': 'Send daily report'})")


class ScheduledTaskUpdate(BaseModel):
    task_name: Optional[str] = None
    task_description: Optional[str] = None
    is_active: Optional[bool] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    interval_minutes: Optional[int] = None
    interval_hours: Optional[int] = None
    run_date: Optional[str] = None
    task_data: Optional[dict] = None


class ScheduledTaskOut(BaseModel):
    id: int
    admin_id: int
    task_name: str
    task_type: str
    task_description: Optional[str]
    cron_expression: Optional[str]
    interval_seconds: Optional[int]
    interval_minutes: Optional[int]
    interval_hours: Optional[int]
    run_date: Optional[str]
    task_data: dict
    is_active: bool
    created_at: str
    next_run_at: Optional[str]
    last_run_at: Optional[str]
    
    class Config:
        from_attributes = True


    


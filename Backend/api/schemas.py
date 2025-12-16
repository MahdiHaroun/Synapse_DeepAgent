from pydantic import BaseModel, EmailStr, Field
from typing import Optional



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
    username: str
    email: EmailStr
    password: str


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
    last_interaction: Optional[str] = None
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

    


from Backend.api.database import Base 
from sqlalchemy import Column, Integer, String, Boolean , ForeignKey, Text, JSON
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship


class Admin(Base):
    __tablename__ = "admin"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, unique=False, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)

    threads = relationship(
        "Thread",
        back_populates="admin",
        cascade="all, delete-orphan"  # DB cascade only
    )
    files = relationship(
        "UploadedFiles",
        back_populates="admin",
        cascade="all, delete-orphan"
    )
    
    eventbridge_schedules = relationship(
        "EventBridgeSchedule",
        back_populates="admin",
        cascade="all, delete-orphan"
    )
    

class Thread(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("admin.id"), nullable=False, index=True)
    last_interaction = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)

    admin = relationship("Admin", back_populates="threads")
    files = relationship("UploadedFiles", back_populates="thread", cascade="all, delete-orphan")


class UploadedFiles(Base): 
    __tablename__ = "uploaded_files"
    file_id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_date = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    thread_id = Column(String, ForeignKey("threads.uuid"), nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("admin.id"), nullable=False, index=True)
    
    thread = relationship("Thread", back_populates="files")
    admin = relationship("Admin", back_populates="files")



class EventBridgeSchedule(Base):
    """AWS EventBridge scheduled events"""
    __tablename__ = "eventbridge_schedules"
    
    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("admin.id"), nullable=False, index=True)
    
    # Schedule information
    schedule_name = Column(String, nullable=False)
    schedule_expression = Column(String, nullable=False)  # e.g., "cron(0 10 * * ? *)"
    event_description = Column(Text, nullable=False)
    event_data = Column(JSON, nullable=False, default={})
    
    # AWS EventBridge details
    eventbridge_rule_name = Column(String, unique=True, nullable=False, index=True)
    eventbridge_rule_arn = Column(String, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text('now()'))
    last_triggered_at = Column(TIMESTAMP(timezone=True), nullable=True)
    
    admin = relationship("Admin", back_populates="eventbridge_schedules")


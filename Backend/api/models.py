from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey,
    Text, JSON, Table
)
from sqlalchemy.sql.sqltypes import TIMESTAMP
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship
from Backend.api.database import Base



admin_roles = Table(
    "admin_roles",
    Base.metadata,
    Column("admin_id", Integer, ForeignKey("admin.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_privileges = Table(
    "role_privileges",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("privilege_id", Integer, ForeignKey("privileges.id", ondelete="CASCADE"), primary_key=True),
)


class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)

    threads = relationship("Thread", back_populates="admin", cascade="all, delete-orphan")
    files = relationship("UploadedFiles", back_populates="admin", cascade="all, delete-orphan")
    schedules = relationship("EventBridgeSchedule", back_populates="admin", cascade="all, delete-orphan")
    roles = relationship("Role", secondary=admin_roles, back_populates="admins")


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)
    last_interaction = Column(TIMESTAMP(timezone=True), index=True)
    is_active = Column(Boolean, default=True)

    admin = relationship("Admin", back_populates="threads")
    files = relationship("UploadedFiles", back_populates="thread", cascade="all, delete-orphan")



class UploadedFiles(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True)
    file_uuid = Column(String, unique=True, nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    upload_date = Column(TIMESTAMP(timezone=True), server_default=text("now()"))

    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)
    thread_id = Column(Integer, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)

    admin = relationship("Admin", back_populates="files")
    thread = relationship("Thread", back_populates="files")



class EventBridgeSchedule(Base):
    __tablename__ = "eventbridge_schedules"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("admin.id", ondelete="CASCADE"), nullable=False)

    schedule_name = Column(String, nullable=False)
    schedule_expression = Column(String, nullable=False)
    event_description = Column(Text, nullable=False)
    event_data = Column(JSON, nullable=False, default=dict)

    eventbridge_rule_name = Column(String, unique=True, nullable=False, index=True)
    eventbridge_rule_arn = Column(String)

    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"))
    last_triggered_at = Column(TIMESTAMP(timezone=True))

    admin = relationship("Admin", back_populates="schedules")



class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)

    admins = relationship("Admin", secondary=admin_roles, back_populates="roles")
    privileges = relationship("Privilege", secondary=role_privileges, back_populates="roles")




class Privilege(Base):
    __tablename__ = "privileges"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)

    roles = relationship("Role", secondary=role_privileges, back_populates="privileges")

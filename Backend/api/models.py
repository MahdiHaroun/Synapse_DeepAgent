from Backend.api.database import Base 
from sqlalchemy import Column, Integer, String, Boolean , ForeignKey 
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


class Thread(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, nullable=False, index=True)
    admin_id = Column(Integer, ForeignKey("admin.id"), nullable=False, index=True)
    last_interaction = Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, default=True, index=True)

    admin = relationship("Admin", back_populates="threads")





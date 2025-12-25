from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.sql import func
from database import Base

class GmailToken(Base):
    __tablename__ = "gmail_tokens"

    email = Column(String(255), primary_key=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<GmailToken(email='{self.email}')>"

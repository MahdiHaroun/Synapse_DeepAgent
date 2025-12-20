"""
Database migration script for scheduled_tasks table

Run this after updating the models to create the new table.
The table will be created automatically by SQLAlchemy when the app starts,
but you can also run this manually if needed.
"""

from Backend.api.database import engine
from Backend.api.models import Base

def migrate():
    """Create all tables including the new scheduled_tasks table"""
    Base.metadata.create_all(bind=engine)
    print("Database migration completed successfully!")
    print("Created table: scheduled_tasks")

if __name__ == "__main__":
    migrate()

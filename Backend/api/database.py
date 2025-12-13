from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv("Backend/api/.env")


SQLALCHEMY_DATABASE_URL = os.getenv("db_url")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

sessionLocal = sessionmaker(autocommit = False , autoflush= False , bind = engine)

Base = declarative_base()

def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()        



if __name__ == "__main__":
    # Test the database connection
    try:
        with engine.connect() as connection:
        
            print("Database connection successful")
    except Exception as e:
        print("Database connection failed:", e)
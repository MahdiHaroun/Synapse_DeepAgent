from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status 
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from Backend.api import database
from Backend.api import models, schemas
import os
load_dotenv("Backend/api/.env")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 60


oauth2_scheme = OAuth2PasswordBearer(tokenUrl='admins/login')#The tokenUrl='login' means the frontend will get tokens by calling your /login endpoint (that’s where users log in).


def create_access_token(data: dict):
    to_encode = data.copy()
    # Set the expiration time for the token
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        id: str = payload.get("user_id")
        

        if id is None:
            raise credentials_exception

        token_data = schemas.TokenData(id=str(id))
    except JWTError:
        raise credentials_exception
    
    return token_data


def verify_websocket_token(token: str) -> dict:
    """
    Verify JWT token for WebSocket connections.
    Returns user data dict or None if invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user_name = payload.get("user_name")
        
        if user_id is None:
            return None
        
        return {
            "user_id": int(user_id),
            "user_name": user_name
        }
    except JWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = verify_access_token(token, credentials_exception)
    admin = db.query(models.Admin).filter(models.Admin.id == token_data.id).first()
    
    return admin


def get_mongo_client():
    from pymongo import MongoClient
    mongo_url = os.getenv("mongo_url")
    client = MongoClient(mongo_url)
    return client
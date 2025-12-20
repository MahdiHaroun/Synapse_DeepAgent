from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from Backend.api import database, models, schemas, utils, auth
from langgraph.store.mongodb import MongoDBStore
import os
from pymongo import MongoClient

router = APIRouter(prefix="/admins", tags=["Authentication"])

mongo_uri = os.getenv("MONGODB_URI")
mongo_client = MongoClient(mongo_uri)
mongo_db = mongo_client["Synapse_admins_info"] 


def save_user_info(user_info: dict, admin_username: str) -> str:
    """Save user information in the long-term store."""
    try:
        long_term_store = MongoDBStore(
            collection=mongo_db["synapse_agent_store"]
        )
        store = long_term_store
        user_id = admin_username
        
        print(f"DEBUG: Attempting to save user_info for user_id: {user_id}")
        print(f"DEBUG: user_info: {user_info}")
        print(f"DEBUG: store type: {type(store)}")
        
        
        store.put(("users",), user_id, user_info)
        
        return "Successfully saved user info."
    except Exception as e:
        print(f"ERROR in save_user_info: {e}")
        import traceback
        traceback.print_exc()
        return f"Error saving user info: {str(e)}"





@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schemas.AdminOut)
async def register(admin_details: schemas.AdminCreate, db: Session = Depends(database.get_db)):
    """
    Register a new admin user.
    """
    # Check if the email already exists
    existing_admin = db.query(models.Admin).filter(models.Admin.email == admin_details.email).first()
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    # Hash the password
    hashed_password = utils.hash(admin_details.password)
    admin_details.password = hashed_password
    admin_details.username = admin_details.email.split("@")[0]  # Set username from email prefix

    
    # Create new admin instance
    new_admin = models.Admin(**admin_details.dict())
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    # Save user info to long-term store
    user_info = {
        "name": new_admin.name,
        "email": new_admin.email,
    }
    try:
        save_user_info(user_info, new_admin.username)
    except Exception as e:
        raise HTTPException(status_code=500, detail="internal error saving user info")
    
    return {
        "Confirmation": "Welcome aboard, " + new_admin.name + "!",
    }


@router.post("/login", response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.Admin).filter(models.Admin.email == user_credentials.username).first() 
    
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")
    
    if not utils.verify(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN ,detail="Invalid credentials")
    

    access_token = auth.create_access_token(data={"user_id": user.id , "user_name" : user.username} )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "name": user.name,
        "username": user.username,
        "email": user.email
    }





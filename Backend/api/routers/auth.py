from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from Backend.api import database, models, schemas, utils, auth


router = APIRouter(prefix="/admins", tags=["Authentication"])




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
    
    return {
        "Confirmation": "Welcome aboard, " + new_admin.name + "!",
        "id": new_admin.id,
        "name": new_admin.name,
        "email": new_admin.email,
        "username": new_admin.username
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





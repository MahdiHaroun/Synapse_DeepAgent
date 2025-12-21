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


def has_role(admin: models.Admin, role_name: str) -> bool:
    """Check if admin has a specific role."""
    return any(role.name == role_name for role in admin.roles) 


def save_user_info(user_info: dict, admin_username: str ) -> str:
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


def update_user_roles_in_store(admin: models.Admin, db: Session) -> str:
    """Update user roles and privileges in the long-term store."""
    try:
        long_term_store = MongoDBStore(
            collection=mongo_db["synapse_agent_store"]
        )
        
        # Get existing user info
        existing_item = long_term_store.get(("users",), admin.username)
        
        if existing_item:
            user_info = existing_item.value
        else:
            user_info = {
                "name": admin.name,
                "email": admin.email
            }
        
        # Update roles and privileges
        roles_data = []
        
        for role in admin.roles:
            role_privileges = [
                {
                    "name": priv.name,
                    "description": priv.description
                }
                for priv in role.privileges
            ]
            
            roles_data.append({
                "name": role.name,
                "privileges": role_privileges
            })
        
        user_info["roles"] = roles_data
        
        if roles_data:
            role_names = [r["name"] for r in roles_data]
            total_privileges = sum(len(r["privileges"]) for r in roles_data)
            user_info["role_description"] = f"Has roles: {', '.join(role_names)} with {total_privileges} total privileges"
        else:
            user_info["role_description"] = "No roles assigned"
        
        long_term_store.put(("users",), admin.username, user_info)
        return "Successfully updated user roles."
    except Exception as e:
        print(f"ERROR in update_user_roles_in_store: {e}")
        import traceback
        traceback.print_exc()
        return f"Error updating user roles: {str(e)}"





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
    username = admin_details.email.split("@")[0]  # Set username from email prefix

    # Create new admin instance with additional fields
    new_admin = models.Admin(
        name=admin_details.name,
        username=username,
        email=admin_details.email,
        password_hash=hashed_password,
        is_verified=False
    )
    
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
        "Confirmation": "Welcome aboard, " + new_admin.name + "!" + "you will receive an email to verify your account soon.",
    }


@router.post("/login", response_model=schemas.Token)
async def login(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.Admin).filter(models.Admin.email == user_credentials.username).first() 
    
    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials")
    
    if not utils.verify(user_credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN ,detail="Invalid credentials")
    

    access_token = auth.create_access_token(data={"user_id": user.id , "user_name" : user.username} )
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "name": user.name,
        "username": user.username,
        "email": user.email
    }




@router.get("/me", response_model=schemas.AdminInfo)
async def get_current_admin(current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Get the currently authenticated admin user.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return current_user 


@router.post("/add_role/{username}/{role_id}", status_code=status.HTTP_200_OK)
async def add_role_to_admin(
    username: str,
    role_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Add a role to an admin user. Only superadmins can assign roles.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(status_code=403, detail="Forbidden: Only superadmins can assign roles.")
    
    user = db.query(models.Admin).filter(models.Admin.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    
    # Check if role already assigned
    if role in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role.name}' already assigned to user '{username}'"
        )
    
    
    user.roles.append(role)
    db.commit()
    db.refresh(user)
    
    # Update MongoDB store with all roles and privileges
    try:
        update_user_roles_in_store(user, db)
    except Exception as e:
        print(f"Warning: Failed to update MongoDB: {e}")
    
    return {
        "detail": f"Role '{role.name}' added to user '{username}' successfully.",
        "roles": [r.name for r in user.roles]
    }


@router.delete("/remove_role/{username}/{role_id}", status_code=status.HTTP_200_OK)
async def remove_role_from_admin(
    username: str,
    role_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Remove a role from an admin user. Only superadmins can remove roles.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(status_code=403, detail="Forbidden: Only superadmins can remove roles.")
    
    user = db.query(models.Admin).filter(models.Admin.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    
    # Check if role is assigned
    if role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role.name}' not assigned to user '{username}'"
        )
    
    # Remove role from user
    user.roles.remove(role)
    db.commit()
    db.refresh(user)
    
    # Update MongoDB store with remaining roles and privileges
    try:
        update_user_roles_in_store(user, db)
    except Exception as e:
        print(f"Warning: Failed to update MongoDB: {e}")
    
    return {
        "detail": f"Role '{role.name}' removed from user '{username}' successfully.",
        "roles": [r.name for r in user.roles]
    }


@router.put("/update/{username}", status_code=status.HTTP_200_OK)
async def update_admin(
    username: str,
    admin_update: schemas.AdminUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Update admin information (name, email, password).
    Only the admin themselves or a superadmin can update.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Check if user is updating themselves or is a superadmin
    if current_user.username != username and not has_role(current_user, "superadmin"):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: You can only update your own information unless you're a superadmin."
        )
    
    # Find the user to update
    user = db.query(models.Admin).filter(models.Admin.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update fields if provided
    updated_fields = []
    if admin_update.name is not None:
        user.name = admin_update.name
        updated_fields.append("name")
    
    if admin_update.email is not None:
        # Check if email already exists for another user
        existing = db.query(models.Admin).filter(
            models.Admin.email == admin_update.email,
            models.Admin.username != username
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use by another user"
            )
        user.email = admin_update.email
        updated_fields.append("email")
    
    if admin_update.password is not None:
        user.password_hash = utils.hash(admin_update.password)
        updated_fields.append("password")
    
    if not updated_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update"
        )
    
    # Commit changes to database
    db.commit()
    db.refresh(user)
    
    # Update MongoDB store (only name and email, not password)
    try:
        long_term_store = MongoDBStore(collection=mongo_db["synapse_agent_store"])
        existing_item = long_term_store.get(("users",), user.username)
        
        if existing_item:
            user_info = existing_item.value
            if admin_update.name is not None:
                user_info["name"] = user.name
            if admin_update.email is not None:
                user_info["email"] = user.email
            long_term_store.put(("users",), user.username, user_info)
    except Exception as e:
        print(f"Warning: Failed to update MongoDB: {e}")
        # Don't fail the request if MongoDB update fails
    
    return {
        "detail": f"Successfully updated {', '.join(updated_fields)} for user '{username}'.",
        "updated_fields": updated_fields
    }


@router.delete("/delete/{username}", status_code=status.HTTP_200_OK)
async def delete_admin(
    username: str,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Delete an admin user.
    Only superadmins can delete users.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(status_code=403, detail="Forbidden: Only superadmins can delete users.")
    
    user = db.query(models.Admin).filter(models.Admin.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user_id = user.id
    
    # Delete user from database
    db.delete(user)
    db.commit()
    
    # Delete from MongoDB store
    try:
        long_term_store = MongoDBStore(collection=mongo_db["synapse_agent_store"])
        long_term_store.delete(("users",), username)
    except Exception as e:
        print(f"Warning: Failed to delete from MongoDB: {e}")
    
    # Delete all user's threads (they are cascade deleted from DB, but need S3/MongoDB cleanup)
    try:
        threads = db.query(models.Thread).filter(models.Thread.admin_id == user_id).all()
        
        if threads:
            import boto3
            s3 = boto3.client("s3")
            bucket_name = "synapse-openapi-schemas"
            
            for thread in threads:
                thread_id = thread.uuid
                
                # S3 cleanup
                prefix = f"{thread_id}/"
                try:
                    paginator = s3.get_paginator("list_objects_v2")
                    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                        contents = page.get("Contents", [])
                        if contents:
                            s3.delete_objects(
                                Bucket=bucket_name,
                                Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]}
                            )
                except Exception as e:
                    print(f"S3 cleanup failed for thread {thread_id}: {e}")
            
            # MongoDB checkpoints cleanup
            thread_ids = [thread.uuid for thread in threads]
            try:
                mongo_client_local = MongoClient(os.getenv("MONGODB_URI"))
                mongo_db_memory = mongo_client_local["Synapse_memory_db"]
                checkpoints_collection = mongo_db_memory["checkpoints"]
                checkpoints_collection.delete_many({"thread_id": {"$in": thread_ids}})
            except Exception as e:
                print(f"MongoDB checkpoints cleanup failed: {e}")
    except Exception as e:
        print(f"Warning: Failed to cleanup user's threads: {e}")

    
    
    return {"detail": f"User '{username}' deleted successfully."}



@router.get("/list_admins", status_code=status.HTTP_200_OK, response_model=list[schemas.AdminInfo])
async def list_admins(db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    List all admin users.
    Only superadmins can list all users.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(status_code=403, detail="Forbidden: Only superadmins can list all users.")
    
    admins = db.query(models.Admin).all()
    return admins

@router.get("/get_user_info/{username}", status_code=status.HTTP_200_OK)
async def get_user_info_endpoint(username: str,
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Get user information from the long-term store.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        long_term_store = MongoDBStore(
            collection=mongo_db["synapse_agent_store"]
        )
        
        # Retrieve data from store
        result = long_term_store.get(("users",), username)
        
        if result:
            return {"user_info": result.value}
        else:
            raise HTTPException(status_code=404, detail="User info not found in store")
    except Exception as e:
        print(f"ERROR in get_user_info_endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal error retrieving user info")
    

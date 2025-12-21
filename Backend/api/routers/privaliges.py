from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from Backend.api import database, models, schemas, auth
from Backend.api.routers.auth import has_role

router = APIRouter(prefix="/privileges", tags=["Privileges"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.PrivilegeOut)
async def create_privilege(
    privilege: schemas.PrivilegeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Create a new privilege
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    

    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to create a privilege"
        )
    
    # Check if privilege already exists
    existing = db.query(models.Privilege).filter(
        models.Privilege.name == privilege.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privilege '{privilege.name}' already exists"
        )
    
    # Create new privilege
    new_privilege = models.Privilege(
        name=privilege.name,
        description=privilege.description
    )
    
    db.add(new_privilege)
    db.commit()
    db.refresh(new_privilege)
    
    return new_privilege


@router.get("/", response_model=List[schemas.PrivilegeOut])
async def list_privileges(
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    List all privileges.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to view privileges"
        )
    
    privileges = db.query(models.Privilege).all()
    return privileges


@router.get("/{privilege_id}", response_model=schemas.PrivilegeOut)
async def get_privilege(
    privilege_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Get a specific privilege by ID.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to view privilege"
        )
    
    privilege = db.query(models.Privilege).filter(
        models.Privilege.id == privilege_id
    ).first()
    
    if not privilege:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privilege with ID {privilege_id} not found"
        )
    
    return privilege


@router.put("/{privilege_id}", response_model=schemas.PrivilegeOut)
async def update_privilege(
    privilege_id: int,
    privilege_update: schemas.PrivilegeUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Update a privilege
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to update privilege"
        )
    
    
    privilege = db.query(models.Privilege).filter(
        models.Privilege.id == privilege_id
    ).first()
    
    if not privilege:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privilege with ID {privilege_id} not found"
        )
    
    # Update fields if provided
    updated_fields = []
    
    if privilege_update.name is not None:
        # Check if new name already exists for another privilege
        existing = db.query(models.Privilege).filter(
            models.Privilege.name == privilege_update.name,
            models.Privilege.id != privilege_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Privilege name '{privilege_update.name}' already exists"
            )
        
        privilege.name = privilege_update.name
        updated_fields.append("name")
    
    if privilege_update.description is not None:
        privilege.description = privilege_update.description
        updated_fields.append("description")
    
    if not updated_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update"
        )
    
    db.commit()
    db.refresh(privilege)
    
    return privilege


@router.delete("/{privilege_id}", status_code=status.HTTP_200_OK)
async def delete_privilege(
    privilege_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Delete a privilege. 
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to delete privilege"
        )
    
    
    privilege = db.query(models.Privilege).filter(
        models.Privilege.id == privilege_id
    ).first()
    
    if not privilege:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privilege with ID {privilege_id} not found"
        )
    
    privilege_name = privilege.name
    
    # Delete the privilege
    db.delete(privilege)
    db.commit()
    
    return {
        "detail": f"Privilege '{privilege_name}' (ID: {privilege_id}) deleted successfully"
    }

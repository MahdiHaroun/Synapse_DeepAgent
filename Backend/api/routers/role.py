from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from Backend.api import database, models, schemas, auth
from Backend.api.routers.auth import has_role

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.RoleOut)
async def create_role(
    role: schemas.RoleCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Create a new role with attached privileges. Only superadmins can create roles.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to create a role"
        )
    
    # Check if role already exists
    existing = db.query(models.Role).filter(
        models.Role.name == role.name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role.name}' already exists"
        )
    
    # Create new role
    new_role = models.Role(name=role.name)
    
    # Attach privileges if provided
    if role.privilege_ids:
        privileges = db.query(models.Privilege).filter(
            models.Privilege.id.in_(role.privilege_ids)
        ).all()
        
        if len(privileges) != len(role.privilege_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more privilege IDs not found"
            )
        
        new_role.privileges = privileges
    
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    
    return new_role


@router.get("/", response_model=List[schemas.RoleOut])
async def list_roles(
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    List all roles with their privileges.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to view roles"
        )
    
    roles = db.query(models.Role).all()
    return roles


@router.get("/{role_id}", response_model=schemas.RoleOut)
async def get_role(
    role_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Get a specific role by ID with its privileges.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to view role"
        )
    
    role = db.query(models.Role).filter(
        models.Role.id == role_id
    ).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )
    
    return role


@router.put("/{role_id}", response_model=schemas.RoleOut)
async def update_role(
    role_id: int,
    role_update: schemas.RoleUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Update a role's name and/or privileges. Only superadmins can update roles.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to update role"
        )
    
    # Find the role
    role = db.query(models.Role).filter(
        models.Role.id == role_id
    ).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )
    
    # Update fields if provided
    updated_fields = []
    
    if role_update.name is not None:
        # Check if new name already exists for another role
        existing = db.query(models.Role).filter(
            models.Role.name == role_update.name,
            models.Role.id != role_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role name '{role_update.name}' already exists"
            )
        
        role.name = role_update.name
        updated_fields.append("name")
    
    if role_update.privilege_ids is not None:
        # Update privileges
        privileges = db.query(models.Privilege).filter(
            models.Privilege.id.in_(role_update.privilege_ids)
        ).all()
        
        if len(privileges) != len(role_update.privilege_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more privilege IDs not found"
            )
        
        role.privileges = privileges
        updated_fields.append("privileges")
    
    if not updated_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided to update"
        )
    
    db.commit()
    db.refresh(role)
    
    return role


@router.delete("/{role_id}", status_code=status.HTTP_200_OK)
async def delete_role(
    role_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Delete a role. Only superadmins can delete roles.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to delete role"
        )
    
    # Find the role
    role = db.query(models.Role).filter(
        models.Role.id == role_id
    ).first()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )
    
    role_name = role.name
    
    # Delete the role
    db.delete(role)
    db.commit()
    
    return {
        "detail": f"Role '{role_name}' (ID: {role_id}) deleted successfully"
    }


@router.post("/{role_id}/privileges/{privilege_id}", status_code=status.HTTP_200_OK)
async def attach_privilege_to_role(
    role_id: int,
    privilege_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Attach a single privilege to a role.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to attach privilege to role"
        )
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )
    
    privilege = db.query(models.Privilege).filter(
        models.Privilege.id == privilege_id
    ).first()
    if not privilege:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privilege with ID {privilege_id} not found"
        )
    
    # Check if already attached
    if privilege in role.privileges:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privilege '{privilege.name}' already attached to role '{role.name}'"
        )
    
    role.privileges.append(privilege)
    db.commit()
    
    return {
        "detail": f"Privilege '{privilege.name}' attached to role '{role.name}' successfully"
    }


@router.delete("/{role_id}/privileges/{privilege_id}", status_code=status.HTTP_200_OK)
async def detach_privilege_from_role(
    role_id: int,
    privilege_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """
    Detach a privilege from a role.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not has_role(current_user, "superadmin"):
        raise HTTPException(      
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to detach privilege from role"
        )
    
    role = db.query(models.Role).filter(models.Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with ID {role_id} not found"
        )
    
    privilege = db.query(models.Privilege).filter(
        models.Privilege.id == privilege_id
    ).first()
    if not privilege:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Privilege with ID {privilege_id} not found"
        )
    
    # Check if attached
    if privilege not in role.privileges:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Privilege '{privilege.name}' not attached to role '{role.name}'"
        )
    
    role.privileges.remove(privilege)
    db.commit()
    
    return {
        "detail": f"Privilege '{privilege.name}' detached from role '{role.name}' successfully"
    }

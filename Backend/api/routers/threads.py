from fastapi import APIRouter , HTTPException , Depends , status  
import uuid 
from Backend.api.database import get_db
from Backend.api import schemas 
from sqlalchemy.orm import Session
from Backend.api import database, models, schemas, utils, auth
import boto3

router = APIRouter(prefix="/threads")








@router.post("/create_new_thread" , status_code=status.HTTP_201_CREATED , response_model=schemas.ThreadCreate)
async def create_new_thread(thread_details: schemas.ThreadCreate, db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Create a new chat session (thread_id) for streaming.
    """
    # Generate unique UUID for the thread
    thread_uuid = thread_details.uuid
    if not thread_uuid:
        thread_uuid = str(uuid.uuid4())
    
    new_thread = models.Thread(
        uuid=thread_uuid,
        admin_id=current_user.id
    )

    db.add(new_thread)
    db.commit()
    db.refresh(new_thread)

    return {
        "uuid": new_thread.uuid,
        "admin_id": new_thread.admin_id
    }


@router.get("/get_threads" , response_model=list[schemas.ThreadOut])
async def get_threads(db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Get all chat sessions (threads) for the current admin user.
    """
    threads = db.query(models.Thread).filter(models.Thread.admin_id == current_user.id).all()
    return threads


@router.get("/get_thread/{thread_id}" , response_model=schemas.ThreadOut)
async def get_thread(thread_id: str, db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Get a specific chat session (thread) by thread_id for the current admin user.
    """
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
                                            models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    
    return thread




@router.delete("/delete_thread/{thread_id}",status_code=status.HTTP_200_OK)
async def delete_thread(
    thread_id: str,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user),
):
    thread = (
        db.query(models.Thread)
        .filter(
            models.Thread.uuid == thread_id,
            models.Thread.admin_id == current_user.id,
        )
        .first()
    )

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    db.delete(thread)
    db.commit()

    # ---- S3 cleanup ----
    s3 = boto3.client("s3")
    bucket_name = "synapse-openapi-schemas"
    prefix = f"{thread_id}/"
    deleted_any = False

    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            contents = page.get("Contents", [])
            if contents:
                deleted_any = True
                s3.delete_objects(
                    Bucket=bucket_name,
                    Delete={
                        "Objects": [{"Key": obj["Key"]} for obj in contents]
                    },
                )
    except Exception as e:

        print(f"S3 cleanup failed for thread {thread_id}: {e}")

    return {
        "detail": "Thread deleted successfully"
        + (" and S3 objects removed." if deleted_any else ".")
    }




@router.delete("/delete_all_threads",status_code=status.HTTP_200_OK)
async def delete_all_threads(
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user),
):
    threads = db.query(models.Thread).filter(models.Thread.admin_id == current_user.id).all()

    s3 = boto3.client("s3")
    bucket_name = "synapse-openapi-schemas"

    for thread in threads:
        thread_id = thread.uuid

        
        db.delete(thread)

        # ---- S3 cleanup ----
        prefix = f"{thread_id}/"
        try:
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
                contents = page.get("Contents", [])
                if contents:
                    s3.delete_objects(
                        Bucket=bucket_name,
                        Delete={
                            "Objects": [{"Key": obj["Key"]} for obj in contents]
                        },
                    )
        except Exception as e:
            print(f"S3 cleanup failed for thread {thread_id}: {e}")

    db.commit()

    return {
        "detail": "All threads are deleted successfully " + ("and S3 objects removed." if threads else ".")
    }





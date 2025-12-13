from fastapi import APIRouter , HTTPException , Depends , status   , UploadFile , File
import uuid 
from Backend.api.database import get_db
from sqlalchemy.orm import Session
from Backend.api import database, models, schemas, utils, auth
import boto3


router = APIRouter(prefix="/files")
s3 = boto3.client("s3", region_name="eu-central-1")
bucket_name = "synapse-openapi-schemas"



@router.get("/list_all_files", status_code=status.HTTP_200_OK)
async def list_all_objects(
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all objects in the S3 bucket for the current admin user, organized by thread.
    """
    # Ensure user exists
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Get all threads for this admin
    threads = db.query(models.Thread).filter(models.Thread.admin_id == current_user.id).all()

    result = {}
    paginator = s3.get_paginator("list_objects_v2")

    for thread in threads:
        prefix = f"{thread.uuid}/"
        thread_objects = []

        # List all objects under the thread prefix
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                # Remove prefix so only file names are returned
                thread_objects.append(obj["Key"].replace(prefix, ""))

        result[thread.uuid] = thread_objects

    return {"threads": result}


@router.get("/list_files/{thread_id}" , status_code=status.HTTP_200_OK)
async def list_thread_objects(
    thread_id: str,
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)

):
    
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    prefix = f"{thread_id}/"
    objects = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"] != prefix:
                objects.append(obj["Key"].replace(prefix, ""))

    return {"objects": objects}
    

@router.get("/download_file/{thread_id}/{object_key}")
async def download_file(
    thread_id: str,
    object_key: str,
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    s3_key = f"{thread_id}/{object_key}"

    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": bucket_name,
                "Key": s3_key,
                "ResponseContentDisposition": f'attachment; filename="{object_key}"',
            },
            ExpiresIn=300,  # 5 minutes
        )

        return {"url": url}

    except Exception:
        raise HTTPException(status_code=500, detail="Could not generate download link")


@router.delete("/delete_file/{thread_id}/{object_key}", status_code=status.HTTP_200_OK)
async def delete_file(
    thread_id: str,
    object_key: str,
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    s3_key = f"{thread_id}/{object_key}"

    try:
        s3.delete_object(Bucket=bucket_name, Key=s3_key)
        return {"detail": "File deleted successfully."}
    except Exception:
        raise HTTPException(status_code=500, detail="Could not delete the file.")
    

@router.delete("/delete_all_files/{thread_id}", status_code=status.HTTP_200_OK)
async def delete_all_files(
    thread_id: str,
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all files under bucket_name/thread_id/
    """
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    prefix = f"{thread_id}/"
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        contents = response.get("Contents", [])
        if contents:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={
                    "Objects": [{"Key": obj["Key"]} for obj in contents]
                },
            )
        return {"detail": "All files deleted successfully."}
    except Exception:
        raise HTTPException(status_code=500, detail="Could not delete files.")
    


@router.post("/upload_file/", status_code=status.HTTP_201_CREATED)
async def upload_file(
    thread_id: str,
    file_location: UploadFile = File(...),  
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file to S3 under bucket_name/thread_id/
    """
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    s3_key = f"{thread_id}/{file_location.filename}"

    try:
        s3.upload_fileobj(file_location.file, bucket_name, s3_key)
        return {"s3_key": s3_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {e}")
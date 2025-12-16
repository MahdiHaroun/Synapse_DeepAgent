import botocore
from fastapi import APIRouter , HTTPException , Depends , status   , UploadFile , File
from Backend.api.database import get_db
from sqlalchemy.orm import Session
from Backend.api import models, auth
import boto3
import os
from dotenv import load_dotenv

load_dotenv("/app/.env")

router = APIRouter(prefix="/files" , tags=["Files"])
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")
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
    thread = db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    s3_key = f"{thread_id}/{object_key}"
    try:
        s3.head_object(Bucket=bucket_name, Key=s3_key)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            raise HTTPException(status_code=404, detail="File not found")
        else:
            raise HTTPException(status_code=500, detail="Error checking file in S3")
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
        s3.head_object(Bucket=bucket_name, Key=s3_key)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            raise HTTPException(status_code=404, detail="File not found")
        else:
            raise HTTPException(status_code=500, detail="Error checking file in S3")

    try:
        s3.delete_object(Bucket=bucket_name, Key=s3_key)
        return {"detail": "File deleted successfully."}
    except Exception:
        raise HTTPException(status_code=500, detail="Could not delete the file.")
    



@router.delete("/delete_all_thread_files/{thread_id}", status_code=status.HTTP_200_OK)
async def delete_all_thread_files(
    thread_id: str,
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all files under bucket_name/thread_id/
    """
    thread = db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

 
    prefix = f"{thread_id}/"

    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
        contents = response.get("Contents", [])

        if not contents:

            raise HTTPException(status_code=404, detail="No files found for this thread in S3")

        s3.delete_objects(
            Bucket=bucket_name,
            Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]}
        )

        return {"detail": "All files deleted successfully."}

    except botocore.exceptions.ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 error: {e.response['Error']['Message']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not delete files: {e}")




@router.delete("/delete_all_files", status_code=status.HTTP_200_OK)
async def delete_all_files(
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete all files in the S3 bucket for the current admin user, organized by thread.
    Raises 404 if no files exist.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Get all threads for this user
    threads = db.query(models.Thread).filter(models.Thread.admin_id == current_user.id).all()
    if not threads:
        raise HTTPException(status_code=404, detail="No threads found for this user")

    files_found = False  

    try:
        for thread in threads:
            prefix = f"{thread.uuid}/"
            continuation_token = None

            while True:
                list_kwargs = {"Bucket": bucket_name, "Prefix": prefix}
                if continuation_token:
                    list_kwargs["ContinuationToken"] = continuation_token

                response = s3.list_objects_v2(**list_kwargs)
                contents = response.get("Contents", [])

                if contents:
                    files_found = True
                    # Delete objects in chunks of 1000 (S3 limit)
                    s3.delete_objects(
                        Bucket=bucket_name,
                        Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]}
                    )

                if response.get("IsTruncated"):
                    continuation_token = response.get("NextContinuationToken")
                else:
                    break

        if not files_found:
            raise HTTPException(status_code=404, detail="No files found for this user in S3")

        return {"detail": "All files deleted successfully."}

    except botocore.exceptions.ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 error: {e.response['Error']['Message']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not delete files: {e}")


@router.post("/upload_file/{thread_id}", status_code=status.HTTP_201_CREATED)
async def upload_file(
    thread_id: str,
    file_location: UploadFile = File(...),  
    current_user: models.Admin = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a file to S3 under bucket_name/thread_id/
    """
    thread = db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    s3_key = f"{thread_id}/{file_location.filename}"

    file_location.file.seek(0, 2)  
    size = file_location.file.tell()
    if size > 50 * 1024 * 1024:  #
        raise HTTPException(status_code=400, detail="File too large")
    file_location.file.seek(0)  
    try:
        s3.upload_fileobj(file_location.file, bucket_name, s3_key)
        return {"s3_key": s3_key}
    except botocore.exceptions.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {e.response['Error']['Message']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not upload file: {e}")
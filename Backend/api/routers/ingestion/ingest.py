from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException , Depends 
from uuid import uuid4
import shutil
import os
import logging
from Backend.api.database import get_db
from Backend.api import models
from sqlalchemy.orm import Session
from Backend.api import auth
import datetime
from pathlib import Path

from Backend.api.routers.ingestion.pipeline import ingest_pipeline , ingest_image

logger = logging.getLogger(__name__)

router = APIRouter()




@router.post("/ingest/pdf/{thread_id}")
async def ingest_pdf(
    thread_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """Ingest PDF file for RAG processing."""

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    thread = db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found or access denied")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    
    job_id = str(uuid4())
    file_id = "pdf_" + str(uuid4())
    path = f"/shared/{thread_id}/uploads/{file_id}.pdf"

    # Create directory
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"[{datetime.datetime.now()}] Created directory: {os.path.dirname(path)}")

    # List directory BEFORE writing
    print(f"[{datetime.datetime.now()}] Directory contents BEFORE write:")
    print(os.listdir(os.path.dirname(path)))

    try:
        # Read file content first
        file_content = await file.read()
        print(f"[{datetime.datetime.now()}] Read {len(file_content)} bytes from uploaded file")
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Write to disk with sync
        with open(path, "wb") as f:
            bytes_written = f.write(file_content)
            f.flush()
            os.fsync(f.fileno())
        
        print(f"[{datetime.datetime.now()}] Wrote {bytes_written} bytes to {path}")
        
        # Immediate verification
        if not os.path.exists(path):
            raise HTTPException(status_code=500, detail=f"File was not created at {path}")
        
        actual_size = os.path.getsize(path)
        stat_info = os.stat(path)
        print(f"[{datetime.datetime.now()}] Verified file at {path}")
        print(f"  - Size: {actual_size} bytes")
        print(f"  - Permissions: {oct(stat_info.st_mode)}")
        print(f"  - Owner: {stat_info.st_uid}:{stat_info.st_gid}")
        
        # List directory AFTER writing
        print(f"[{datetime.datetime.now()}] Directory contents AFTER write:")
        print(os.listdir(os.path.dirname(path)))
        
    except Exception as e:
        print(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        await file.close()

    file_path = Path(path)
    file_size = file_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    if size_mb > 5:  # 5 MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 5 MB limit")

    new_file = models.UploadedFiles(
        filename=file.filename,
        thread_id=thread.id,
        admin_id=current_user.id,
        file_type="pdf", 
        file_size=file_size,
        upload_date=datetime.datetime.utcnow(), 
        file_uuid=file_id
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    background_tasks.add_task(
        ingest_pipeline,
        job_id,
        path,
        file_id,
        thread_id
    )

    return {
        "job_id": job_id,
        "file_id": file_id,
        "status": "started"
    }


@router.post("/ingest/image/{thread_id}")
async def image_ingest(
    thread_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)
):
    """Ingest Image file for RAG processing."""

    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    thread = db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == current_user.id
    ).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found or access denied")
    
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not any(file.filename.lower().endswith(ext) for ext in ['.jpeg', '.jpg', '.png', '.webp']):
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WEBP image files are supported")
    
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    
    job_id = str(uuid4())
    file_id = "image_" + str(uuid4()) 
    
    path = f"/shared/{thread_id}/uploads/{file_id}.png"
    
    # Create directory
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"Created directory: {os.path.dirname(path)}")

    try:
        # Read file content first
        file_content = await file.read()
        print(f"Read {len(file_content)} bytes from uploaded image")
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        # Write to disk
        with open(path, "wb") as f:
            bytes_written = f.write(file_content)
        
        print(f"Wrote {bytes_written} bytes to {path}")
        
        # Verify file exists and has content
        if not os.path.exists(path):
            raise HTTPException(status_code=500, detail=f"File was not created at {path}")
        
        actual_size = os.path.getsize(path)
        print(f"Verified file at {path} with size {actual_size} bytes")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        await file.close()
        

    file_path = Path(path)
    file_size = file_path.stat().st_size
    size_mb = file_size / (1024 * 1024)
    if size_mb > 5:  # 5 MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 5 MB limit")

    new_file  = models.UploadedFiles(
        filename=file.filename,
        thread_id=thread.id,
        admin_id=current_user.id,
        file_type="image", 
        file_size=file_size,
        upload_date= datetime.datetime.utcnow(), 
        file_uuid=file_id
    )

    db.add(new_file)
    db.commit()
    db.refresh(new_file)

    background_tasks.add_task(
        ingest_image,
        job_id,
        path,
        file_id,
        thread_id
    )

    return {
        "job_id": job_id,
        "file_id": file_id,
        "status": "started"
    }
    
    
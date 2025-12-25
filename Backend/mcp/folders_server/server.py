from mcp.server.fastmcp import FastMCP
import datetime
import os
import boto3
import base64
from pathlib import Path
from dotenv import load_dotenv
from typing import List


env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Set AWS credentials
os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")

mcp = FastMCP("file-management" , host="0.0.0.0", port=3005)

VOLUME_PATH = "/shared"  # Docker volume mount point

@mcp.tool()
async def create_pdf_file(
    thread_id: str,
    content: str,
    images_s3_keys: List[str] = [],
    images_volume_paths: List[str] = [],
    bucket_name: str = "synapse-openapi-schemas"
) -> dict:
    """
    Create a UTF-8 PDF file from text + multiple images from S3 and/or volume,
    upload to S3, and return the file path and S3 key.

    Arguments:
        thread_id: The conversation thread ID
        content: Text content for the PDF
        images_s3_keys: List of S3 keys for images
        images_volume_paths: List of local volume paths relative to /shared/<thread_id>
        bucket_name: S3 bucket name
    """
    from fpdf import FPDF
    import io
    from uuid import uuid4
    import boto3

    # Initialize PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Add UTF-8 font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_path):
        font_path = "/app/fonts/DejaVuSans.ttf"  # fallback

    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    # Initialize S3 client
    s3 = boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
    )

    # --- Add images from S3 ---
    for key in images_s3_keys:
        try:
            img_obj = io.BytesIO()
            s3.download_fileobj(bucket_name, key, img_obj)
            img_obj.seek(0)
            pdf.image(img_obj, w=100)
            pdf.ln(5)
        except Exception as e:
            print(f"Error adding S3 image {key}: {e}")

    # --- Add images from local volume ---
    volume_base_path = f"/shared/{thread_id}"
    for rel_path in images_volume_paths:
        img_path = os.path.join(volume_base_path, rel_path)
        if os.path.exists(img_path) and os.path.isfile(img_path):
            try:
                pdf.image(img_path, w=100)
                pdf.ln(5)
            except Exception as e:
                print(f"Error adding local image {img_path}: {e}")
        else:
            print(f"Local image not found: {img_path}")

    # Add text content
    pdf.ln(10)
    for line in content.split("\n"):
        pdf.multi_cell(0, 8, line)

    # Prepare paths
    pdf_file_name = f"{uuid4().hex}.pdf"
    thread_folder = os.path.join(volume_base_path, "documents")
    os.makedirs(thread_folder, exist_ok=True)
    pdf_path = os.path.join(thread_folder, pdf_file_name)
    pdf.output(pdf_path)

    # Upload PDF to S3
    pdf_file_key = f"{thread_id}/documents/{pdf_file_name}"
    s3.upload_file(pdf_path, bucket_name, pdf_file_key)

    # Relative path for email attachments (relative to /shared/{thread_id}/)
    relative_path = f"documents/{pdf_file_name}"

    return {
        "s3_key": pdf_file_key,
        "file_path": pdf_path,
        "relative_path": relative_path,
        "filename": pdf_file_name,
        "message": f"PDF created at {pdf_path}. Use relative_path '{relative_path}' for email attachments."
    }


@mcp.tool()
async def list_files_in_thread(thread_id: str):
    """
    List all files for a specific thread from the shared volume.
    Returns file paths relative to the thread folder.
    """
    thread_dir = os.path.join(VOLUME_PATH, thread_id)

    if not os.path.exists(thread_dir):
        raise FileNotFoundError(f"Thread directory {thread_dir} does not exist.")

    files_list = []

    # Walk through all subdirectories
    for root, dirs, files in os.walk(thread_dir):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, thread_dir)  # relative to thread folder
            files_list.append(rel_path)

    return {"thread_id": thread_id, "files": files_list}

@mcp.tool()
async def search_files_by_keyword(thread_id: str, search_term: str):
    """
    Search for files by partial name inside a thread folder.
    Returns paths relative to the thread folder.
    """
    thread_dir = os.path.join(VOLUME_PATH, thread_id)

    if not os.path.exists(thread_dir):
        raise FileNotFoundError(f"Thread directory {thread_dir} does not exist.")

    matched_files = []

    # Walk through all subdirectories
    for root, dirs, files in os.walk(thread_dir):
        for f in files:
            if search_term.lower() in f.lower():  # partial, case-insensitive match
                file_path = os.path.join(root, f)
                rel_path = os.path.relpath(file_path, thread_dir)
                matched_files.append(rel_path)

    return {"thread_id": thread_id, "search_term": search_term, "matched_files": matched_files}



if __name__ == "__main__":
    mcp.run(transport="sse")
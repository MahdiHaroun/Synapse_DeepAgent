from PyPDF2 import PdfReader
import os
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing import Annotated
from src.States.state import DeepAgentState
import boto3
from dotenv import load_dotenv
load_dotenv("/app/.env")


os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")







@tool()
async def create_pdf_file(
    thread_id: str,
    content: str,
    image_s3_keys: list = None,  # now expects S3 keys like "thread_id/file.png"
    bucket_name: str = "synapse-openapi-schemas"
) -> dict:
    """
    Create a UTF-8 PDF file from text + multiple images from S3,
    upload to S3, and return a secure presigned link.
    
    Arguments:
        thread_id: The conversation thread ID
        content: Text content for the PDF
        image_s3_keys: List of S3 keys for images
    """
    from fpdf import FPDF
    import io
    from uuid import uuid4
    import boto3

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Add UTF-8 font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_path):
        raise FileNotFoundError("Font file DejaVuSans.ttf not found on server.")

    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)
    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
    os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")

    s3 = boto3.client("s3", region_name="eu-central-1")

    # Add images from S3
    if image_s3_keys:
        for s3_key in image_s3_keys:
            try:
                # Download image into memory
                img_buffer = io.BytesIO()
                s3.download_fileobj(bucket_name, s3_key, img_buffer)
                img_buffer.seek(0)

                # fpdf expects a filename, so save temporarily in-memory
                tmp_img_path = f"/tmp/{uuid4().hex}_{os.path.basename(s3_key)}"
                with open(tmp_img_path, "wb") as f:
                    f.write(img_buffer.read())

                pdf.image(tmp_img_path, x=10, w=180)
                pdf.ln(5)
                os.remove(tmp_img_path)  # clean up temporary file

            except Exception as e:
                print(f"Warning: Could not add image {s3_key}: {e}")

        pdf.ln(10)  # extra space after images

    # Add text content
    for line in content.split("\n"):
        pdf.multi_cell(0, 8, line)

    # Save PDF to S3
    pdf_file_key = f"{thread_id}/{uuid4().hex}.pdf"
    tmp_pdf_path = f"/tmp/{uuid4().hex}.pdf"
    pdf.output(tmp_pdf_path)

    s3.upload_file(tmp_pdf_path, bucket_name, pdf_file_key)
    os.remove(tmp_pdf_path)

    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": pdf_file_key},
        ExpiresIn=3600
    )

    return {
        "s3_key": pdf_file_key,
        "presigned_url": presigned_url
    }




@tool
async def list_cached_files(state: Annotated[DeepAgentState, InjectedState]) -> str:
    """List all files currently cached in memory from this conversation."""
    cached_files = state.get("files", {})
    if not cached_files:
        return "No files cached yet."
    
    file_list = []
    for key, content in cached_files.items():
        size = len(content)
        if key.startswith("image_analysis_"):
            file_list.append(f" {key} ({size} chars) - Image analysis result")
        else:
            file_list.append(f" {key} ({size} chars)")
    
    return "Cached files in this conversation:\n" + "\n".join(file_list)


@tool
async def get_cached_file(
    filename: str,
    state: Annotated[DeepAgentState, InjectedState]
) -> str:
    """Retrieve a previously cached file content."""
    cached_files = state.get("files", {})
    
    # Try exact match first
    if filename in cached_files:
        return cached_files[filename]
    
    # Try partial match for image analysis
    for key, content in cached_files.items():
        if filename in key:
            return content
    
    return f"File '{filename}' not found in cache. Use list_cached_files to see available files."


@tool
async def read_pdf_file(
    temp_file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Extract text from a PDF file and cache in state for reuse. Reject if more than 5 pages."""
    # Check if already cached
    filename = os.path.basename(temp_file_path)
    cached_files = state.get("files", {})
    
    if filename in cached_files:
        return Command(
            update={"messages": [ToolMessage(f"Using cached content from {filename}\n\n{cached_files[filename]}", tool_call_id=tool_call_id)]}
        )
    
    # Extract text
    reader = PdfReader(temp_file_path)
    num_pages = len(reader.pages)

    if num_pages > 5:
        raise ValueError(f"PDF has {num_pages} pages, but the limit is 5.")

    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    content = text.strip()
    
    # Cache in state for reuse
    return Command(
        update={
            "files": {filename: content},
            "messages": [ToolMessage(f"Extracted and cached {num_pages} pages from {filename}\n\n{content}", tool_call_id=tool_call_id)]
        }
    )




@tool
async def read_text_file(
    temp_file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Read and cache text file content for reuse."""
    filename = os.path.basename(temp_file_path)
    cached_files = state.get("files", {})
    
    if filename in cached_files:
        return Command(
            update={"messages": [ToolMessage(f"Using cached content from {filename}\n\n{cached_files[filename]}", tool_call_id=tool_call_id)]}
        )
    
    with open(temp_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    return Command(
        update={
            "files": {filename: content},
            "messages": [ToolMessage(f"Cached {filename}\n\n{content}", tool_call_id=tool_call_id)]
        }
    )


@tool
async def read_excel_file(
    temp_file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """Read an Excel file and cache its content as CSV string for reuse."""
    import pandas as pd
    
    filename = os.path.basename(temp_file_path)
    cached_files = state.get("files", {})
    
    if filename in cached_files:
        return Command(
            update={"messages": [ToolMessage(f"Using cached content from {filename}\n\n{cached_files[filename]}", tool_call_id=tool_call_id)]}
        )
    
    df = pd.read_excel(temp_file_path)
    content = df.to_csv(index=False)
    
    return Command(
        update={
            "files": {filename: content},
            "messages": [ToolMessage(f"Cached Excel data from {filename}\n\n{content}", tool_call_id=tool_call_id)]
        }
    )



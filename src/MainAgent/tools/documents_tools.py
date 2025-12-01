from PyPDF2 import PdfReader
import boto3
import os
from fpdf import FPDF
from uuid import uuid4
from langchain_core.tools import  tool





@tool
async def read_pdf_file(path: str) -> str:
    """Extract text from a PDF file. Reject if more than 5 pages."""
    reader = PdfReader(path)
    num_pages = len(reader.pages)


    if num_pages > 5:
        raise ValueError(f"PDF has {num_pages} pages, but the limit is 5.")

    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text


@tool
async def read_text_file(path: str) -> str:
    """Read and return the content of a text file."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return content


@tool
async def read_excel_file(path: str) -> str:
    """Read an Excel file and return its content as a CSV string."""
    import pandas as pd

    df = pd.read_excel(path)
    return df.to_csv(index=False)


@tool
async def create_pdf_file(content: str):
    """
    Create a PDF file from text, upload to S3, and return a secure presigned download link.
    """


    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for line in content.split("\n"):
        pdf.multi_cell(0, 10, line)

    file_key = f"{uuid4().hex}.pdf"
    pdf.output(file_key)

    # S3 bucket
    bucket = "synapse-files-container"
    if not bucket:
        raise ValueError("AWS_S3_BUCKET_NAME is not set")

    session = boto3.Session()
    s3 = session.client("s3" , region_name="us-east-1")

    # Upload file (private)
    s3.upload_file(file_key, bucket, file_key)

    # Generate presigned URL
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": file_key},
        ExpiresIn=3600  # expires in 1 hour
    )

    # Cleanup
    os.remove(file_key)

    return {
        "message": "PDF created successfully.",
        "filename": file_key,
        "download_url": presigned_url
    }

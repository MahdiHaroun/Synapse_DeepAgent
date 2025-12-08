from PyPDF2 import PdfReader
import boto3
import os
from fpdf import FPDF
from uuid import uuid4
from langchain_core.tools import  tool



@tool 
async def delete_file(file_location: str) -> str:
    """Delete a file from the specified directory."""
    if os.path.exists(file_location):
        os.remove(file_location)
        return f"File {file_location} deleted successfully."
    else:
        return f"File {file_location} does not exist."

@tool 
async def check_file_exists(file_location: str) -> bool:
    """Check if a file exists at the specified location."""
    return os.path.exists(file_location)


@tool
async def read_pdf_file(temp_file_path: str) -> str:
    """Extract text from a PDF file. Reject if more than 5 pages."""
    reader = PdfReader(temp_file_path)
    num_pages = len(reader.pages)


    if num_pages > 5:
        raise ValueError(f"PDF has {num_pages} pages, but the limit is 5.")

    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text.strip()




@tool
async def read_text_file(temp_file_path: str) -> str:
    """Read and return the content of a text file."""
    with open(temp_file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content


@tool
async def read_excel_file(temp_file_path: str) -> str:
    """Read an Excel file and return its content as a CSV string."""
    import pandas as pd

    df = pd.read_excel(temp_file_path)
    return df.to_csv(index=False)


@tool
async def create_pdf_file(content: str, image_paths: list = None) -> dict:
    """
    Create a UTF-8 PDF file from text + multiple images,
    upload to S3, and return a secure presigned link.
    """

    from fpdf import FPDF
    import boto3
    import os
    from uuid import uuid4

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Add UTF-8 font
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_path):
        raise FileNotFoundError("Font file DejaVuSans.ttf not found on server.")

    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    # Add images
    if image_paths:
        for img in image_paths:
            if img and os.path.exists(img):
                pdf.image(img, x=10, w=180)
                pdf.ln(90)

        pdf.ln(5)

    for line in content.split("\n"):
        pdf.multi_cell(0, 8, line)
    file_key = f"{uuid4().hex}.pdf"
    pdf.output(file_key)

    bucket = "synapse-files-container"

    s3 = boto3.client("s3", region_name="us-east-1")
    s3.upload_file(file_key, bucket, file_key)

    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": file_key},
        ExpiresIn=3600
    )

    # Cleanup
    os.remove(file_key)

    return {
        "message": "PDF created successfully.",
        "filename": file_key,
        "download_url": presigned_url,
    }

import os
from langchain_core.tools import tool
from langchain.tools import ToolRuntime
from langgraph.prebuilt import InjectedState
from typing import Annotated, List
from src.States.state import DeepAgentState
from src.MainAgent.tools.memory_tools import Context
from src.embedding.embedding import titan_embed_v1
from src.LLMs.GroqLLMs.llms import groq_gpt_oss_llm
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from Backend.api.database import sessionLocal
from Backend.api import models
load_dotenv("/app/.env")


os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")







@tool()
async def create_pdf_file(
    runtime: ToolRuntime[Context],
    content: str,
    image_s3_keys: list = None,  # now expects S3 keys like "thread_id/file.png"
    bucket_name: str = "synapse-openapi-schemas" ,

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
        font_path = "/app/fonts/DejaVuSans.ttf"  # fallback


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
    
    thread_id = runtime.context.thread_id
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
async def list_documents_in_thread(
    runtime: ToolRuntime[Context]
) -> List[dict]:
    """
    List all documents added to the current thread/conversation.
    Returns a list of dicts with file_id, filename, upload_date, and s3_key.
    """
    thread_id = runtime.context.thread_id

    db = sessionLocal()
    try:
        files = db.query(models.UploadedFiles).filter(
            models.UploadedFiles.thread_id == thread_id
        ).all()

        file_list = []
        for f in files:
            file_list.append({
                "file_id": f.file_id,
                "filename": f.filename,
                "file_type": f.file_type,
                "upload_date": f.upload_date.isoformat(),
            })

        return file_list

    finally:
        db.close()


@tool
async def search_retrieve_faiss(
    runtime: ToolRuntime[Context],
    question: str,
    file_id: str = None
) -> str:
    """
    Search the FAISS vector store for relevant document chunks related to the question.

    Args:
        question: The user's question
        file_id: Optional - Specific file ID to search. If None, searches all files in context.

    Returns:
        Answer based on the retrieved document chunks.
        
    Usage:
        - For general questions: Leave file_id as None (searches all added files)
        - For specific file: Provide the file_id (useful for comparisons)
        - For comparing files: Call this multiple times with different file_ids
    """
    thread_id = runtime.context.thread_id
    all_file_ids = runtime.context.files_ids

    if not all_file_ids:
        return "No documents have been added to this conversation yet. Please add documents first."

    db = FAISS.load_local(
        f"faiss/{thread_id}",
        titan_embed_v1,
        allow_dangerous_deserialization=True
    )

    # Search with higher k to ensure we get relevant chunks
    docs = db.similarity_search(question, k=15)
    
    # Filter by file_id(s)
    if file_id:
        # Search only in specific file
        filtered_docs = [
            d for d in docs 
            if d.metadata.get("file_id") == file_id
        ]
        context_msg = f"file ID: {file_id}"
    else:
        # Search across all added files
        filtered_docs = [
            d for d in docs 
            if d.metadata.get("file_id") in all_file_ids
        ]
        context_msg = f"all {len(all_file_ids)} added file(s)"
    
    if not filtered_docs:
        return f"No relevant information found in {context_msg} for this question."
        
    context = "\n\n".join(d.page_content for d in filtered_docs[:5])  # Use top 5 most relevant

    prompt = f"""
Use ONLY the context below to answer the question.
If the answer is not present in the context, say "I don't know based on the provided documents".

Context from documents:
{context}

Question:
{question}

Answer:"""

    return groq_gpt_oss_llm.invoke(prompt).content



def get_all_chunks(db: FAISS, file_id: str):
    """Retrieve all document chunks for a given file ID from the FAISS vector store."""
    # Get all documents from the vector store
    all_docs = db.docstore._dict.values()
    
    # Filter by file_id in metadata
    file_docs = [
        doc for doc in all_docs 
        if doc.metadata.get("file_id") == file_id
    ]
    
    return file_docs


@tool
async def summarize_file(
    runtime: ToolRuntime[Context],
    state: Annotated[DeepAgentState, InjectedState],
    file_id: str 
):
    """
    Use ONLY when the user asks to summarize, overview, or TL;DR a file.
    This tool reads the entire file and produces a full summary.
    
    The file_id should be one of the files added to this conversation.
    """

    thread_id = runtime.context.thread_id
    file_id = file_id



    db = FAISS.load_local(
        f"faiss/{thread_id}",
        titan_embed_v1,
        allow_dangerous_deserialization=True
    )

    docs = get_all_chunks(db, file_id)

    if not docs:
        return "No content found for this file."

    # ---- MAP ----
    partial = []
    for doc in docs:
        partial.append(
            groq_gpt_oss_llm.invoke(
                f"Summarize this text:\n{doc.page_content}"
            ).content
        )

    # ---- REDUCE ----
    final = groq_gpt_oss_llm.invoke(
        "Combine these summaries into one coherent summary:\n"
        + "\n".join(partial)
    ).content

    return final

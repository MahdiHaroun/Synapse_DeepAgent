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













@tool
async def list_faiss_files(
    runtime: ToolRuntime[Context]
) -> List[dict]:
    """
    List all documents added to the current thread/conversation.
    Returns a list of dicts with file_id, filename, upload_date, and s3_key.
    """
    thread_uuid = runtime.context.thread_id

    db = sessionLocal()
    try:
        # First, get the Thread by UUID to get the integer ID
        thread = db.query(models.Thread).filter(
            models.Thread.uuid == thread_uuid
        ).first()
        
        if not thread:
            return []
        
        # Now query files using the integer thread ID
        files = db.query(models.UploadedFiles).filter(
            models.UploadedFiles.thread_id == thread.id
        ).all()

        file_list = []
        for f in files:
            file_list.append({
                "file_id": f.file_uuid,
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
    all_file_uuids = runtime.context.files_ids

    if not all_file_uuids:
        return "No documents have been added to this conversation yet. Please add documents first."

    db = FAISS.load_local(
        f"/app/faiss/{thread_id}",
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
            if d.metadata.get("file_id") in all_file_uuids
        ]
        context_msg = f"all {len(all_file_uuids)} added file(s)"
    
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



def get_all_chunks(db: FAISS, file_uuid: str):
    """Retrieve all document chunks for a given file ID from the FAISS vector store."""
    # Get all documents from the vector store
    all_docs = db.docstore._dict.values()
    
    # Filter by file_id in metadata (metadata uses "file_id" as the key)
    file_docs = [
        doc for doc in all_docs 
        if doc.metadata.get("file_id") == file_uuid
    ]
    
    return file_docs


@tool
async def summarize_faiss_file(
    runtime: ToolRuntime[Context],
    state: Annotated[DeepAgentState, InjectedState],
    file_uuid: str 
):
    """
    Use ONLY when the user asks to summarize, overview, or TL;DR a file.
    This tool reads the entire file and produces a full summary.
    
    The file_id should be one of the files added to this conversation.
    """

    thread_id = runtime.context.thread_id
    file_uuid = file_uuid



    db = FAISS.load_local(
        f"/app/faiss/{thread_id}",
        titan_embed_v1,
        allow_dangerous_deserialization=True
    )

    docs = get_all_chunks(db, file_uuid)

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

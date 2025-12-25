import logging
import os
from Backend.api.routers.ingestion.status import set_status
from Backend.api.routers.ingestion.pdf import PdfProcessor
from Backend.api.routers.ingestion.image import ImageProcessor
from Backend.api.routers.ingestion.storing import VectorStoreManager

import logging
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(f"{LOG_DIR}/websocket.log")
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

async def ingest_pipeline(job_id: str, file_path: str, file_id: str, thread_id: str):
    """Process PDF ingestion pipeline with status tracking."""
    try:
        await set_status(job_id, "uploaded", 10, file_id, thread_id)
        logger.info(f"Starting ingestion pipeline for job {job_id}")

        processor = PdfProcessor()
        await set_status(job_id, "parsing", 30, file_id, thread_id)

        docs = processor.load_and_chunk(file_path)
        if not docs:
            raise ValueError("No documents extracted from PDF")
        
        await set_status(job_id, "chunking", 50, file_id, thread_id)
        logger.info(f"Extracted {len(docs)} chunks from PDF")

        store = VectorStoreManager()
        store.save(docs, file_id, thread_id)
        await set_status(job_id, "embedding", 80, file_id, thread_id) 

        await set_status(job_id, "completed", 100, file_id, thread_id)
        logger.info(f"Successfully completed ingestion for job {job_id}")
        
        # Keep the files - no cleanup!
        logger.info(f"File preserved at {file_path}")

    except Exception as e:
        logger.error(f"Ingestion pipeline failed for job {job_id}: {e}", exc_info=True)
        await set_status(job_id, "failed", 0, file_id, thread_id, error=str(e))


async def ingest_image(job_id: str, file_path: str, file_id: str, thread_id: str):
    """Process Image ingestion pipeline with status tracking."""
    try:
        await set_status(job_id, "uploaded", 10, file_id, thread_id)
        logger.info(f"starting image ingestion pipeline for job {job_id}")

        processor = ImageProcessor()

        await set_status(job_id, "validating", 30, file_id, thread_id)
        await processor.validate_image(file_path)

        await set_status(job_id, "normalizing", 50, file_id, thread_id)
        normalized_path = await processor.normalize_image(file_path)

        await set_status(job_id, "analyzing", 70, file_id, thread_id)
        analysis = await processor.analyze_image(normalized_path)

        from langchain_core.documents import Document
        doc = Document(
            page_content=analysis,
            metadata={
                "file_id": file_id,
                "thread_id": thread_id,
                "type": "image_analysis",
                "original_file": file_path
            }
        )

        await set_status(job_id, "embedding", 90, file_id, thread_id)
        store = VectorStoreManager()
        store.save([doc], file_id, thread_id)

        await set_status(job_id, "completed", 100, file_id, thread_id)
        logger.info(f"Successfully completed image ingestion for job {job_id}")

        # Keep original, but cleanup normalized version
        try:
            if normalized_path != file_path and os.path.exists(normalized_path):
                os.remove(normalized_path)
                logger.info(f"Cleaned up normalized image at {normalized_path}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to cleanup normalized file: {cleanup_error}")
            
        logger.info(f"Original image preserved at {file_path}")
        
    except Exception as e:
        logger.error(f"Image ingestion pipeline failed for job {job_id}: {e}", exc_info=True)
        await set_status(job_id, "failed", 0, file_id, thread_id, error=str(e))
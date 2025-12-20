import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

REDIS_URL = "redis://localhost:6379"
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def cancel_key(thread_id: str) -> str:
    """Generate Redis key for cancellation flag."""
    if not thread_id:
        raise ValueError("thread_id cannot be empty")
    return f"cancel:{thread_id}"

async def request_cancel(thread_id: str) -> None:
    """Request cancellation for a thread."""
    try:
        await redis_client.set(cancel_key(thread_id), "1", ex=60)
        logger.info(f"Cancellation requested for thread {thread_id}")
    except Exception as e:
        logger.error(f"Failed to request cancel for thread {thread_id}: {e}")

async def is_cancelled(thread_id: str) -> bool:
    """Check if thread has been cancelled."""
    try:
        return await redis_client.exists(cancel_key(thread_id)) == 1
    except Exception as e:
        logger.error(f"Failed to check cancel status for thread {thread_id}: {e}")
        return False

async def clear_cancel(thread_id: str) -> None:
    """Clear cancellation flag for a thread."""
    try:
        await redis_client.delete(cancel_key(thread_id))
        logger.info(f"Cancellation cleared for thread {thread_id}")
    except Exception as e:
        logger.error(f"Failed to clear cancel for thread {thread_id}: {e}")

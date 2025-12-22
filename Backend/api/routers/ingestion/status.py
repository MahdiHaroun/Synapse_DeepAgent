import json
import os
import redis.asyncio as aioredis

# Use environment variable or default to docker service name
redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
redis_client = aioredis.from_url(redis_url, decode_responses=True)

def ingestion_key(job_id: str):
    return f"ingestion:{job_id}"

async def set_status(
    job_id: str,
    state: str,
    progress: int = 0,
    file_id: str | None = None,
    thread_id: str | None = None,
    error: str | None = None,
):
    """Set ingestion job status in Redis."""
    payload = {
        "state": state,
        "progress": progress,
        "file_id": file_id,
        "thread_id": thread_id,
        "error": error,
    }
    await redis_client.set(ingestion_key(job_id), json.dumps(payload), ex=3600)  # 1 hour TTL


async def get_status(job_id: str) -> dict | None:
    """Get ingestion job status from Redis."""
    data = await redis_client.get(ingestion_key(job_id))
    return json.loads(data) if data else None


async def delete_status(job_id: str):
    """Delete ingestion job status from Redis."""
    await redis_client.delete(ingestion_key(job_id))




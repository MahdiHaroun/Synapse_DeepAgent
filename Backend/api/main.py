import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

# Import database and routers
from Backend.api.database import get_db, engine
from Backend.api import models
from Backend.api.routers import auth, threads, files, chat, protocols, testing
from Backend.api.routers import scheduler
from Backend.api.routers.ingestion import ingest
from Backend.api.websocket.websocket_server import start_websocket_server  # Your custom WS server

logger = logging.getLogger(__name__)

# Create all database tables
models.Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app
    Handles startup and shutdown events
    """
    logger.info("Starting up Synapse DeepAgent API...")    
    # Start WebSocket server in background
    ws_task = asyncio.create_task(start_websocket_server(host="0.0.0.0", port=8071))
    print("WebSocket server started on ws://0.0.0.0:8071")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Synapse DeepAgent API...")
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        logger.info("WebSocket server stopped")


# Initialize FastAPI with lifespan
app = FastAPI(
    title="Synapse DeepAgent API",
    description="API for Synapse DeepAgent application.",
    version="3.4.0",
    lifespan=lifespan
)

# Include routers
app.include_router(auth.router)
app.include_router(threads.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(protocols.router)
app.include_router(scheduler.router)
app.include_router(ingest.router)
app.include_router(testing.router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Synapse DeepAgent API!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070)

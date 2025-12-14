from fastapi import APIRouter , HTTPException , Depends , status   , UploadFile , File , FastAPI
from Backend.api.database import get_db , engine , Base
import Backend.api.schemas
from sqlalchemy.orm import Session
from Backend.api import database, models, schemas, utils, auth
from Backend.api.routers import auth , threads , files  , chat , protocols
from contextlib import asynccontextmanager

# Create all database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Synapse DeepAgent API",
    description="API for Synapse DeepAgent application.",
    version="3.3.2",
)
app.include_router(auth.router)
app.include_router(threads.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(protocols.router)




@app.get("/")
async def root():
    return {"message": "Welcome to the Synapse DeepAgent API!"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8070)



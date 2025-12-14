from fastapi import APIRouter , HTTPException , Depends , status  
import uuid 
import os
from Backend.api.database import get_db
from Backend.api import schemas 
from sqlalchemy.orm import Session
from Backend.api import models, auth
from dotenv import load_dotenv
from pymongo import MongoClient
from langgraph.store.mongodb import MongoDBStore
from Synapse_RAG.embedding.embedding import titan_embed_v1
from langgraph.store.mongodb.base import VectorIndexConfig
from datetime import datetime

load_dotenv("Backend/api/.env")

# Initialize MongoDB connection once
mongo_uri = os.getenv("MONGODB_URI")
mongo_client = MongoClient(mongo_uri)
mongo_db = mongo_client["Synapse_memory_db"]  # Same DB as agent uses
protocols_collection = mongo_db["synapse_agent_store"]

router = APIRouter(prefix="/protocols" , tags=["Protocols"])





@router.post("/create_protocol" , status_code=status.HTTP_201_CREATED , response_model=schemas.ProtocolCreate)
async def create_protocol(protocol_details: schemas.ProtocolCreate, db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Create a new protocol/workflow sequence.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    long_term_store = MongoDBStore(
            collection=mongo_db["synapse_agent_store"],
            index_config=VectorIndexConfig(
                dims=1536,
                embed=titan_embed_v1, 
                fields=["sequence_protocol"],
                filters=[] 
            ),
            auto_index_timeout=60 
        )
    
    # Insert the protocol into the long-term store

    sequence_data = {
            "sequence_protocol": protocol_details.sequence_description,  # This field will be indexed for semantic search
            "user_id": current_user.username,
            "created_at": datetime.utcnow().isoformat(),
            "sequence_id": str(uuid.uuid4())
        }
    
    long_term_store.put(("protocols",), sequence_data["sequence_id"], sequence_data)


    return {
        "sequence_description": protocol_details.sequence_description
    }


@router.get("/get_protocols" , status_code=status.HTTP_200_OK)
async def get_protocols(db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Retrieve all protocols for the current admin user.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Query MongoDB directly for user's protocols
    # Match namespace as array and user_id as username
    user_protocols = protocols_collection.find({
        "namespace": ["protocols"],
        "value.user_id": current_user.username
    }).sort("created_at", -1).limit(100)
    
    # Format response
    protocols_list = []
    for protocol in user_protocols:
        protocols_list.append({
            "sequence_id": protocol["value"]["sequence_id"],
            "sequence_protocol": protocol["value"]["sequence_protocol"],
            "created_at": protocol["value"]["created_at"]
        })
    
    return {"protocols": protocols_list}


@router.delete("/delete_protocol/{sequence_id}" , status_code=status.HTTP_200_OK)
async def delete_protocol(sequence_id: str, db: Session = Depends(get_db),
    current_user: models.Admin = Depends(auth.get_current_user)):
    """
    Delete a specific protocol by sequence_id for the current admin user.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Verify ownership and delete
    result = protocols_collection.delete_one({
        "namespace": ["protocols"],
        "key": sequence_id,
        "value.user_id": current_user.username
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Protocol not found or unauthorized")
    
    return {"detail": "Protocol deleted successfully"}


    

    

    
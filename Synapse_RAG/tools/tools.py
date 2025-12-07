from langchain.tools import tool 
from Synapse_RAG.embedding.embedding import titan_embed_v1
from pymongo import MongoClient
import os
import yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv

load_dotenv()

# Initialize MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)

# Load collections from YAML file
def load_collections():
    yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'collections.yaml')
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    return config.get('collections', {})

AVAILABLE_COLLECTIONS = load_collections()

def get_embeddings(text): 
        return titan_embed_v1.embed_documents([text])[0]  # Pass as list, return first

@tool 
def get_query_results(query: str, collection_name: str = "rag_db.test") -> str:
        """Gets results from a vector search query on MongoDB collections.
        
        Args:
            query: The search query string to find relevant documents.
            collection_name: The collection to search in format 'database.collection'. 
                           Available: 'rag_db.test'. Default is 'rag_db.test'.
        
        Returns:
            A formatted string with the retrieved document texts.
        """
        
        # Get collection info
        if collection_name not in AVAILABLE_COLLECTIONS:
            return f"Error: Collection '{collection_name}' not available. Available: {list(AVAILABLE_COLLECTIONS.keys())}"
        
        coll_info = AVAILABLE_COLLECTIONS[collection_name]
        collection = client[coll_info["db"]][coll_info["collection"]]
        vector_index = coll_info["index"]
        
        # Get query embedding
        query_embedding = get_embeddings(query)
        
        pipeline = [
            {
                "$vectorSearch": {
                    "index": vector_index,
                    "queryVector": query_embedding,
                    "path": "embedding",
                    "numCandidates": 1536,
                    "limit": 5
                }
            }, { 
                "$project": {
                    "_id": 1,
                    "text": 1
                }
            }
        ]

        results = collection.aggregate(pipeline)
        
        array_of_results = []
        for doc in results:
            array_of_results.append(doc["text"])
        
        # Return formatted string for LLM
        if not array_of_results:
            return "No relevant documents found."
        
        return "\n\n---\n\n".join(array_of_results)

@tool
def get_object_id_list(query: str, collection_name: str = "rag_db.test") -> str:
    """Gets list of ObjectIds from a vector search query on MongoDB collections.

    Args:
        query: The search query string to find relevant documents.
        collection_name: The collection to search in format 'database.collection'. 
                       Available: 'rag_db.test'. Default is 'rag_db.test'.
    Returns:
        A comma-separated string of ObjectIds.
    """
    # Get collection info
    if collection_name not in AVAILABLE_COLLECTIONS:
        return f"Error: Collection '{collection_name}' not available. Available: {list(AVAILABLE_COLLECTIONS.keys())}"
    
    coll_info = AVAILABLE_COLLECTIONS[collection_name]
    collection = client[coll_info["db"]][coll_info["collection"]]
    vector_index = coll_info["index"]
    
    # Get query embedding
    query_embedding = get_embeddings(query)
    
    pipeline = [
        {
            "$vectorSearch": {
                "index": vector_index,
                "queryVector": query_embedding,
                "path": "embedding",
                "numCandidates": 1536,
                "limit": 5
            }
        }, { 
            "$project": {
                "_id": 1
            }
        }
    ]

    results = collection.aggregate(pipeline)
    
    id_list = []
    for doc in results:
        id_list.append(str(doc["_id"]))
    
    if not id_list:
        return "No relevant documents found."
    
    return ", ".join(id_list)



async def add_document_to_collection(collection_name: str, document_location: str) -> str:
    """Add a new document to the specified MongoDB collection.

    Args:
        collection_name: The name of the MongoDB collection in format 'database.collection'.
        document: The document content to add.

    Returns:
        A confirmation message.
    """
    # Get collection info
    if collection_name not in AVAILABLE_COLLECTIONS:
        return f"Error: Collection '{collection_name}' not available. Available: {list(AVAILABLE_COLLECTIONS.keys())}"
    
    coll_info = AVAILABLE_COLLECTIONS[collection_name]
    collection = client[coll_info["db"]][coll_info["collection"]]


    loader = PyPDFLoader(document_location)
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=20)
    documents = text_splitter.split_documents(data)

    chunks = [doc.page_content for doc in documents]

    batch_size = 10
    all_embeddings = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        embed = titan_embed_v1.embed_documents(batch)     # <── batch call
        all_embeddings.extend(embed)


    docs_to_insert = [
    {"text": documents[i].page_content, "embedding": all_embeddings[i]}
    for i in range(len(documents))
    ]

    # Insert document into the collection
    result = collection.insert_many(docs_to_insert)

    return f"{len(result.inserted_ids)} Document(s) added to collection '{collection_name}' successfully."


async def update_document_in_collection(collection_name: str, object_id: list[str], new_content: str) -> str:
    """Update an existing document in the specified MongoDB collection.

    Args:
        collection_name: The name of the MongoDB collection in format 'database.collection'.
        document_id: The ID of the document to update.
        new_content: The new content for the document.
    Returns:
        A confirmation message.
    """
    from bson import ObjectId

    # Get collection info
    if collection_name not in AVAILABLE_COLLECTIONS:
        return f"Error: Collection '{collection_name}' not available. Available: {list(AVAILABLE_COLLECTIONS.keys())}"
    
    coll_info = AVAILABLE_COLLECTIONS[collection_name]
    collection = client[coll_info["db"]][coll_info["collection"]]

    # Generate new embedding for the updated content
    new_embedding = get_embeddings(new_content)

    # Update document in the collection
    result = collection.update_one(
        {"_id": ObjectId(object_id)},
        {"$set": {"text": new_content, "embedding": new_embedding}}
    )

    if result.matched_count == 0:
        return f"Error: No document found with ID '{object_id}' in collection '{collection_name}'."

    return f"Document with ID '{object_id}' updated successfully in collection '{collection_name}'."



async def delete_document_from_collection(collection_name: str, object_id: list[str]) -> str:
    """Delete a document from the specified MongoDB collection.

    Args:
        collection_name: The name of the MongoDB collection in format 'database.collection'.
        document_id: The ID of the document to delete.
    Returns:
        A confirmation message.
    """
    from bson import ObjectId

    # Get collection info
    if collection_name not in AVAILABLE_COLLECTIONS:
        return f"Error: Collection '{collection_name}' not available. Available: {list(AVAILABLE_COLLECTIONS.keys())}"
    
    coll_info = AVAILABLE_COLLECTIONS[collection_name]
    collection = client[coll_info["db"]][coll_info["collection"]]

    # Delete document from the collection
    result = collection.delete_one({"_id": ObjectId(object_id)})

    if result.deleted_count == 0:
        return f"Error: No document found with ID '{object_id}' in collection '{collection_name}'."

    return f"Document with ID '{object_id}' deleted successfully from collection '{collection_name}'."



async def create_mongo_collection(collection_name: str, vector_index_name: str, db_name: str = "rag_db") -> str:
    """
    Create a new MongoDB collection and register it in collections.yaml.
    
    Arguments:
        collection_name (str): The name of the new collection.
        vector_index_name (str): The name of the vector index to create.
        db_name (str): The database name. Defaults to 'rag_db'.
    Returns:
        str: Confirmation message.
    """
    from pymongo.operations import SearchIndexModel
    import time
    
    # Create the collection by inserting a dummy document first
    collection = client[db_name][collection_name]
    
    # Insert a placeholder document to create the collection
    dummy_embedding = [0.0] * 1536  # Titan embedding dimension
    placeholder_doc = {
        "text": "Collection initialized - placeholder document",
        "embedding": dummy_embedding,
        "placeholder": True
    }
    result = collection.insert_one(placeholder_doc)
    
    # Wait a moment for MongoDB to register the collection
    time.sleep(2)
    
    # Verify collection exists before creating index
    collection_names = client[db_name].list_collection_names()
    if collection_name not in collection_names:
        return f"Error: Failed to create collection '{db_name}.{collection_name}'"
    
    # Create vector search index
    search_index_model = SearchIndexModel(
        definition={
            "fields": [
                {
                    "type": "vector",
                    "numDimensions": 1536,  # Titan embeddings dimension
                    "path": "embedding",
                    "similarity": "cosine"
                }
            ]
        },
        name=vector_index_name,
        type="vectorSearch"
    )
    
    try:
        collection.create_search_index(model=search_index_model)
    except Exception as e:
        return f"Error creating search index: {str(e)}"    
    # Add to YAML file
    yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'collections.yaml')
    
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    if 'collections' not in config:
        config['collections'] = {}
    
    full_name = f"{db_name}.{collection_name}"
    config['collections'][full_name] = {
        'db': db_name,
        'collection': collection_name,
        'index': vector_index_name
    }
    
    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    
    # Reload collections
    global AVAILABLE_COLLECTIONS
    AVAILABLE_COLLECTIONS = load_collections()
    
    return f"Collection '{full_name}' created successfully with index '{vector_index_name}' and registered in collections.yaml"


async def drop_mongo_collection (collection_name: str, db_name: str = "rag_db") -> str:
    """
    Drop a MongoDB collection and remove it from collections.yaml.
    
    Arguments:
        collection_name (str): The name of the collection to drop.
        db_name (str): The database name. Defaults to 'rag_db'.
    Returns:
        str: Confirmation message.
    """
    # Drop the collection
    collection = client[db_name][collection_name]
    collection.drop()
    
    # Remove from YAML file
    yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'collections.yaml')
    
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f) or {}
    
    full_name = f"{db_name}.{collection_name}"
    if 'collections' in config and full_name in config['collections']:
        del config['collections'][full_name]
        
        with open(yaml_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        # Reload collections
        global AVAILABLE_COLLECTIONS
        AVAILABLE_COLLECTIONS = load_collections()
        
        return f"Collection '{full_name}' dropped successfully and removed from collections.yaml"
    else:
        return f"Error: Collection '{full_name}' not found in collections.yaml"
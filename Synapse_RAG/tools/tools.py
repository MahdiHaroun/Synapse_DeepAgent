from langchain.tools import tool 
from Synapse_RAG.embedding.embedding import titan_embed_v1
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)

# Available collections mapping
AVAILABLE_COLLECTIONS = {
    "rag_db.test": {"db": "rag_db", "collection": "test", "index": "vector_index"},
    # Add more collections here as needed
}

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
                    "_id": 0,
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




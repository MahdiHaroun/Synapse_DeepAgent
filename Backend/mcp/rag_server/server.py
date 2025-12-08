from mcp.server import FastMCP
from Synapse_RAG.agent.agent import rag_agent 


mcp = FastMCP("rag_server" , host="0.0.0.0", port=3010)



@mcp.tool()
async def ask_rag_agent(question: str) -> str:
    """
    Use the RAG agent to answer a question.

    Arguments:
        question (str): The question to ask the RAG agent.

    Returns:
        str: The answer provided by the RAG agent.
    """
    result = await rag_agent.ainvoke({"messages": [{"role": "user", "content": question}]})
    # Extract the final message content from the agent response
    messages = result.get("messages", [])
    if messages:
        last_message = messages[-1]
        return last_message.content if hasattr(last_message, 'content') else str(last_message)
    return "No response from agent"


@mcp.tool()
async def add_new_query(collection_name: str, query: str) -> str:
    """
    Add a new document to the specified MongoDB collection from text content.

    Arguments:
        collection_name (str): The name of the MongoDB collection (e.g., 'rag_db.test').
        query (str): The query text content to add.
    
    Returns:
        str: Confirmation message.
    """
    from Synapse_RAG.tools.tools import add_query_to_collection
    result = await add_query_to_collection(collection_name, query)
    return result


@mcp.tool()
async def add_document_from_file(collection_name: str, file_path: str) -> str:
    """
    Add a new document to MongoDB by reading from a file (PDF, TXT, etc.).

    Arguments:
        collection_name (str): The name of the MongoDB collection (e.g., 'rag_db.test').
        file_path (str): The absolute path to the document file.

    Returns:
        str: Confirmation message with number of chunks added.
    """
    from Synapse_RAG.tools.tools import add_document_to_collection
    result = await add_document_to_collection(collection_name, file_path)
    return result


@mcp.tool()
async def update_document(collection_name: str, object_id: str, new_content: str) -> str:
    """
    Update an existing document in the specified MongoDB collection.

    Arguments:
        collection_name (str): The name of the MongoDB collection.
        document_id (str): The ID of the document to update.
        new_content (str): The new content for the document.

    Returns:
        str: Confirmation message.
    """
    from Synapse_RAG.tools.tools import update_document_in_collection
    result = await update_document_in_collection(collection_name, object_id, new_content)
    return result



@mcp.tool()
async def delete_document(collection_name: str, object_id: str) -> str:
    """
    Delete a document from the specified MongoDB collection.

    Arguments:
        collection_name (str): The name of the MongoDB collection.
        document_id (str): The ID of the document to delete.

    Returns:
        str: Confirmation message.
    """
    from Synapse_RAG.tools.tools import delete_document_from_collection
    result = await delete_document_from_collection(collection_name, object_id)
    return result


@mcp.tool()
async def create_new_collection(collection_name: str, vector_index_name: str, db_name: str = "rag_db") -> str:
    """
    Create a new MongoDB collection with vector search index and register it.

    Arguments:
        collection_name (str): The name of the new collection.
        vector_index_name (str): The name of the vector index to create.
        db_name (str): The database name. Defaults to 'rag_db'.

    Returns:
        str: Confirmation message.
    """
    from Synapse_RAG.tools.tools import create_mongo_collection
    result = await create_mongo_collection(collection_name, vector_index_name, db_name)
    return result

@mcp.tool()
async def drop_collection(collection_name: str, db_name: str = "rag_db") -> str:
    """
    Drop an existing MongoDB collection and remove it from collections.yaml.

    Arguments:
        collection_name (str): The name of the collection to drop.
        db_name (str): The database name. Defaults to 'rag_db'.

    Returns:
        str: Confirmation message.
    """
    from Synapse_RAG.tools.tools import drop_mongo_collection
    result = await drop_mongo_collection(collection_name, db_name)
    return result



if __name__ == "__main__":
    mcp.run(transport="sse")
from dataclasses import dataclass 
from typing_extensions import TypedDict 
from langchain.tools import tool, ToolRuntime



@dataclass
class Context:
    user_id: str


class UserInfo(TypedDict):
    name: str
    email: str






@tool
def save_user_info(user_info: dict, runtime: ToolRuntime[Context]) -> str:
    """Save user information in the long-term store."""
    try:
        store = runtime.store
        user_id = runtime.context.user_id
        
        print(f"DEBUG: Attempting to save user_info for user_id: {user_id}")
        print(f"DEBUG: user_info: {user_info}")
        print(f"DEBUG: store type: {type(store)}")
        
        # Store data in the store (namespace, key, data)
        store.put(("users",), user_id, user_info)
        
        print("DEBUG: Successfully called store.put()")
        return "Successfully saved user info."
    except Exception as e:
        print(f"ERROR in save_user_info: {e}")
        import traceback
        traceback.print_exc()
        return f"Error saving user info: {str(e)}"


@tool
def get_user_info(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information from the long-term store."""
    try:
        store = runtime.store
        user_id = runtime.context.user_id
        
        print(f"DEBUG: Attempting to get user_info for user_id: {user_id}")
        
        # Retrieve data from store - returns StoreValue object with value and metadata
        result = store.get(("users",), user_id)
        
        print(f"DEBUG: Result from store.get(): {result}")
        return str(result.value) if result else "Unknown user"
    except Exception as e:
        print(f"ERROR in get_user_info: {e}")
        import traceback
        traceback.print_exc()
        return f"Error getting user info: {str(e)}"


@tool
def save_sequence_protocol(sequence_description: str, runtime: ToolRuntime[Context]) -> str:
    """
    Save a task sequence or protocol to long-term memory for future reference.
    Use this when the user describes a multi-step workflow or procedure that should be remembered.
    
    Examples:
    - " pdf protocol : create a PDF report then send it to email mahdiharoun44@gmail.com"
    
    Args:
        sequence_description: Natural language description of the task sequence/protocol
    """
    try:
        import uuid
        from datetime import datetime
        
        store = runtime.store
        user_id = runtime.context.user_id
        
        # Generate unique ID for this sequence
        sequence_id = str(uuid.uuid4())
        
        # Store with semantic search-optimized structure
        sequence_data = {
            "sequence_protocol": sequence_description,  # This field will be indexed for semantic search
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "sequence_id": sequence_id
        }
        
        print(f"DEBUG: Saving sequence protocol for user_id: {user_id}")
        print(f"DEBUG: Sequence: {sequence_description}")
        
        # Store in the "protocols" namespace with unique sequence_id as key
        store.put(("protocols",), sequence_id, sequence_data)
        
        print(f"DEBUG: Successfully saved sequence protocol with ID: {sequence_id}")
        return "Successfully saved task sequence protocol. You can reference this workflow in future conversations."
    except Exception as e:
        print(f"ERROR in save_sequence_protocol: {e}")
        import traceback
        traceback.print_exc()
        return f"Error saving sequence protocol: {str(e)}"


@tool
def search_sequence_protocols(query: str, runtime: ToolRuntime[Context]) -> str:
    """
    Search for previously saved task sequences/protocols using semantic search.
    Use this to find similar workflows the user has done before.
    
    Args:
        query: Natural language description of the task you're looking for
    """
    try:
        store = runtime.store
        user_id = runtime.context.user_id
        
        print("DEBUG: search_sequence_protocols called")
        print(f"DEBUG: Searching protocols for user_id: {user_id} with query: {query}")
        print(f"DEBUG: Store type: {type(store)}")
        
        # List all items first to see what we have
        try:
            all_items = store.list(("protocols",))
            print(f"DEBUG: Found {len(list(all_items)) if all_items else 0} total protocols")
        except Exception as list_error:
            print(f"DEBUG: List failed: {list_error}")
        
        # Try semantic search - if it fails, fall back to listing
        try:
            print("DEBUG: Attempting semantic search...")
            results = store.search(
                ("protocols",),
                query=query,
                limit=5
            )
            print("DEBUG: Search successful, processing results...")
        except Exception as search_error:
            print(f"ERROR: Semantic search failed: {search_error}")
            # Fallback: just list all protocols
            results = store.list(("protocols",), limit=5)
            print("DEBUG: Using list() fallback instead")
        
        if not results:
            return "No task sequences found in memory yet."
        
        # Format results
        protocols = []
        for i, result in enumerate(results, 1):
            value = result.value
            protocols.append(
                f"{i}. {value.get('sequence_protocol', 'N/A')}\n"
                f"   Created: {value.get('created_at', 'Unknown')}"
            )
        
        response = f"Found {len(protocols)} task sequence(s):\n\n" + "\n\n".join(protocols)
        print(f"DEBUG: Returning {len(protocols)} protocols")
        return response
    except Exception as e:
        error_msg = str(e)
        print(f"ERROR in search_sequence_protocols: {error_msg}")
        import traceback
        traceback.print_exc()
        return f"Error searching protocols: {error_msg}. The search feature may not be fully configured yet."

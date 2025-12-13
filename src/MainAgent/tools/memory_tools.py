from dataclasses import dataclass 
from typing_extensions import TypedDict 
from langchain.tools import tool, ToolRuntime



@dataclass
class Context:
    user_id: str


class UserInfo(TypedDict):
    name: str
    email: str




from dataclasses import asdict

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
        
        print(f"DEBUG: Successfully called store.put()")
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

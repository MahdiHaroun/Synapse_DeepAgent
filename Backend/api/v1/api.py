from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from src.MCP.mcp import get_mcp_client
from src.MainAgent.agent import main_agent
from pydantic import BaseModel
 

app = FastAPI()


class QueryRequest(BaseModel):
    query: str
    thread_id: str

@app.post("/agent/query")
async def query_agent(request: QueryRequest):
    # Create agent per request (lightweight, uses cached tools/model)
    agent = main_agent
    
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": request.query}]},
        {"configurable": {"thread_id": request.thread_id}}
    )
    with open("output.txt", "w") as f:
        f.write(str(result))
    
    return {"result": result}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)# To run the FastAPI app, use the command:
    # uvicorn Backend.api.v1.api:app --reload
from typing import Annotated, Literal, Sequence
from typing_extensions import TypedDict

import operator
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.MainAgent.agent import MainAgent
from src.States.state import DeepAgentState, Todo


class GraphState(DeepAgentState):
    """The state of our graph - extends DeepAgentState to include todos and files."""
    pass


async def create_agent_node():
    """Create the main agent."""
    main_agent_instance = MainAgent()
    agent = await main_agent_instance.create_main_agent()
    return agent


async def agent_node(state: GraphState):
    """Main agent node that processes user input."""
    # Get the agent
    agent = await create_agent_node()
    
    # Use the full state (including todos and files)
    response = await agent.ainvoke(state)
    
    # Return the full response state
    return response


# Create the graph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("agent", agent_node)

# Add edges
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

# Compile the graph with checkpointer for LangGraph Dev
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
graph = workflow.compile()#checkpointer=checkpointer)


# For testing
async def test_graph():
    config = {"configurable": {"thread_id": "test_thread"}}
    result = await graph.ainvoke({
        "messages": [HumanMessage("Hello! How many orders are in the database?")]
    }, config)
    return result


if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_graph())
    print("Final result:", result)
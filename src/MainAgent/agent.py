import asyncio
import os
from pymongo import MongoClient
from src.SubAgents.subAgents import task_tool 
from src.LLMs.GroqLLMs.llms import groq_moonshotai_llm 
from src.embedding.embedding import titan_embed_v1
from src.LLMs.OpenAI_LLMs.llms import openai_gpt4_llm
#from src.LLMs.AWS_LLMs.llms import sonnet_4_llm
from src.States.state import DeepAgentState
from src.MainAgent.tools.todo_tools import write_todos, read_todos , get_current_datetime 
from src.MainAgent.tools.documents_tools import(
    create_pdf_file,
    summarize_file,
    search_retrieve_faiss ,
    list_documents_in_thread
)
from src.Prompts.prompts import  TODO_USAGE_INSTRUCTIONS , GENERAL_INSTRUCTIONS_ABOUT_SPECIFIC_TASKS_WHEN_CALLING_SUB_AGENTS, DOCUMENTS_TOOL_DESCRIPTION  ,  TASK_DESCRIPTION_PREFIX , MEMORY_TOOL_INSTRUCTIONS , URLS_PROTOCOL , SCHADULE_JOBS_INSTRUCTIONS
from langchain.agents import create_agent
#from langgraph.checkpoint.memory import InMemorySaver 
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.store.mongodb import MongoDBStore
from langgraph.store.mongodb.base import VectorIndexConfig
from langchain.agents.middleware import SummarizationMiddleware #, HumanInTheLoopMiddleware
from dotenv import load_dotenv
from src.MainAgent.tools.memory_tools import (
    Context,
    get_user_info,
    save_sequence_protocol,
    search_sequence_protocols
)



class MainAgent: 
    def __init__(self):
        load_dotenv("../.env")  # Load environment variables from .env file
        mongo_uri = os.getenv("MONGODB_URI")
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client["Synapse_memory_db"]

        # Short-term / episodic memory
        self.mongo_memory = MongoDBSaver(
            self.db,
            collection_name="agent_checkpoints"
        )

        # Long-term / semantic store 
        self.long_term_store = MongoDBStore(
            collection=self.db["synapse_agent_store"],
            index_config=VectorIndexConfig(
                dims=1536,
                embed=titan_embed_v1,  
                fields=["sequence_protocol"],
                filters=[]  
            ),
            auto_index_timeout=60  #index timeout in seconds
        )
    
    async def main_agent_tools(self):
        delegation_tools = [task_tool] 
        built_in_tools = [
            write_todos, read_todos, 
            get_user_info,
            save_sequence_protocol, search_sequence_protocols,
            get_current_datetime,
            create_pdf_file,
            summarize_file,
            search_retrieve_faiss,
            list_documents_in_thread

        ] 
        all_tools = delegation_tools + built_in_tools

        return all_tools
    
    async def create_instructions(self):

        INSTRUCTIONS = (
        "# TODO MANAGEMENT\n"
        + TODO_USAGE_INSTRUCTIONS
        + "\n\n"
        + "# TOOLS DESCRIPTION\n"
        + TASK_DESCRIPTION_PREFIX.format(other_agents="Database_Agent, Database_Analyzer_Agent, External_Communication_Agent, AWS_S3_Agent, Analysis_Agent, Calendar_Agent, Auth_Agent, Web_Search_Agent, RAG_Agent, Scheduler_Agent")
        + "\n\n"
        + MEMORY_TOOL_INSTRUCTIONS
        + "\n\n"
        + URLS_PROTOCOL
        + "\n\n"
        + DOCUMENTS_TOOL_DESCRIPTION
        + "\n\n"
        + "CRITICAL: You MUST use write_todos tool for ANY user request to create a plan before proceeding.\n"
        + "=" * 80
        + "\n\n"
        + "# SUB-AGENT DELEGATION\n"
        + GENERAL_INSTRUCTIONS_ABOUT_SPECIFIC_TASKS_WHEN_CALLING_SUB_AGENTS  
        + "\n\n"
        + SCHADULE_JOBS_INSTRUCTIONS
        )
        with open("src/Prompts/main_agent_instructions.txt", "w", encoding="utf-8") as f:
            f.write(INSTRUCTIONS)
        return INSTRUCTIONS

    async def create_main_agent(self):
        all_tools = await self.main_agent_tools()

        INSTRUCTIONS = await self.create_instructions()

        agent = create_agent(
            openai_gpt4_llm,
            all_tools,
            system_prompt=INSTRUCTIONS,
            state_schema=DeepAgentState,
            checkpointer=self.mongo_memory,
            store=self.long_term_store,
            context_schema=Context ,
            middleware=[
                        SummarizationMiddleware(
                        model=groq_moonshotai_llm,
                        max_tokens_before_summary=2000,  # Reduced threshold
                        messages_to_keep=5 
                    ),
                    # HumanInTheLoopMiddleware(
                    #     interrupt_on={
                    #         "task": True    # interrupt with default approval
                    #     }
                    # )
                     ],
        )

        return agent


# Lazy initialization pattern for production
_main_agent = None
_agent_lock = asyncio.Lock()

async def get_main_agent():
    """Get or create the main agent instance (lazy initialization)."""
    global _main_agent
    async with _agent_lock:
        if _main_agent is None:
            _main_agent = await MainAgent().create_main_agent()
        return _main_agent


async def main():
    main_agent = await MainAgent().create_main_agent()
    result = await main_agent.ainvoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "how many orders in the database and clients number",
            }
        ],
    }
)
    print (result)
    return result

if __name__ == "__main__":
    asyncio.run(main())


    

         
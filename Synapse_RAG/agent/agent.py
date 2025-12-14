from src.LLMs.GroqLLMs.llms import groq_llama3_llm 
from Synapse_RAG.tools.tools import get_query_results , get_object_id_list
from langchain.agents import create_agent 
import asyncio




class RAGAgent: 
    def __init__(self):
        pass
    
    async def rag_agent_tools(self):
        rag_tools = [get_query_results , get_object_id_list ] 
        return rag_tools
    
    async def create_rag_agent(self):
        rag_tools = await self.rag_agent_tools()

        RAG_INSTRUCTIONS = (
        "You are a Retrieval-Augmented Generation (RAG) agent. Use the tool [get_query_results] to retrieve relevant documents from MongoDB vector database.\n"
        "When a user asks a question:\n"
        "1. Use get_query_results tool with the user's query to fetch relevant documents\n"
        "2. Synthesize an answer based on the retrieved context\n"
        "3. Be concise and accurate\n\n"
        "Available collections:\n"
        "- rag_db.test (default): General documents\n\n"
        "You can specify a different collection using the collection_name parameter if needed.\n"
        "Use the tool [get_object_id_list] to get the list of object IDs in a specified collection.\n"
        )

        agent = create_agent(
            groq_llama3_llm,
            rag_tools,
            system_prompt=RAG_INSTRUCTIONS,
        )

        return agent
    


# Initialize agent synchronously for module-level import

try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

rag_agent = loop.run_until_complete(RAGAgent().create_rag_agent())
    


if __name__ == "__main__":
    import asyncio

    async def main():
        rag_agent_instance = RAGAgent()
        rag_agent = await rag_agent_instance.create_rag_agent()
        # Example usage
        query = "What is latest ai in mongoDB?"
        response = rag_agent.invoke({"messages": [{"role": "user", "content": query}]})
        print("RAG Agent Response:", response)

    asyncio.run(main())
import asyncio
from src.SubAgents.subAgents import task_tool 
from src.LLMs.GroqLLMs.llms import groq_moonshotai_llm , groq_llama3_llm
from src.LLMs.AWS_LLMs.llms import sonnet_4_llm
from src.States.state import DeepAgentState
from src.MainAgent.tools.todo_tools import write_todos, read_todos , get_current_datetime 
from src.MainAgent.tools.documents_tools import(
    read_text_file,
    read_excel_file,
    create_pdf_file,
    read_pdf_file,
    list_cached_files,
    get_cached_file,
    list_all_files
)
from src.MainAgent.tools.image_analysis import analyze_image
from src.Prompts.prompts import  TODO_USAGE_INSTRUCTIONS , GENERAL_INSTRUCTIONS_ABOUT_SPECIFIC_TASKS_WHEN_CALLING_SUB_AGENTS, DOCUMENTS_TOOL_DESCRIPTION  , IMAGE_ANALYSIS_TOOL_DESCRIPTION , TASK_DESCRIPTION_PREFIX 
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver 
from langchain.agents.middleware import SummarizationMiddleware #, HumanInTheLoopMiddleware


class MainAgent: 
    def __init__(self):
        pass
    
    async def main_agent_tools(self):
        delegation_tools = [task_tool] 
        built_in_tools = [
            write_todos, read_todos, get_current_datetime,
            read_text_file, read_excel_file, create_pdf_file, read_pdf_file,
            list_cached_files, get_cached_file,
            analyze_image , list_all_files
        ] 
        all_tools = delegation_tools + built_in_tools

        return all_tools
    
    async def create_instructions(self):

        INSTRUCTIONS = (
        "# TODO MANAGEMENT\n"
        + TODO_USAGE_INSTRUCTIONS
        + "\n\n"
        + "# TOOLS DESCRIPTION\n"
        + TASK_DESCRIPTION_PREFIX.format(other_agents="DB_sub_agent , DB_analyzer_agent, EC_agent , AWS_S3_agent , analysis_agent , Calendar_agent, Auth_agent, Web_Search_agent, RAG_agent")
        + DOCUMENTS_TOOL_DESCRIPTION
        + "\n\n"
        + IMAGE_ANALYSIS_TOOL_DESCRIPTION
        + "\n\n"
        + "CRITICAL: You MUST use write_todos tool for ANY user request to create a plan before proceeding.\n"
        + "=" * 80
        + "\n\n"
        + "# SUB-AGENT DELEGATION\n"
        + GENERAL_INSTRUCTIONS_ABOUT_SPECIFIC_TASKS_WHEN_CALLING_SUB_AGENTS 
        )
        with open("src/Prompts/main_agent_instructions.txt", "w", encoding="utf-8") as f:
            f.write(INSTRUCTIONS)
        return INSTRUCTIONS

    async def create_main_agent(self):
        all_tools = await self.main_agent_tools()

        INSTRUCTIONS = await self.create_instructions()

        agent = create_agent(
            groq_moonshotai_llm,
            all_tools,
            system_prompt=INSTRUCTIONS,
            state_schema=DeepAgentState,
            checkpointer=InMemorySaver(),
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
    



main_agent = asyncio.run(MainAgent().create_main_agent())


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


    

         
import asyncio
from src.SubAgents.subAgents import task_tool 
from src.LLMs.GroqLLMs.llms import groq_moonshotai_llm 
from src.States.state import DeepAgentState
from src.MainAgent.tools.todo_tools import write_todos, read_todos , get_current_datetime
from src.Prompts.prompts import SUBAGENT_USAGE_INSTRUCTIONS , TODO_USAGE_INSTRUCTIONS , GENERAL_INSTRUCTIONS_ABOUT_SPECIFIC_TASKS_WHEN_CALLING_SUB_AGENTS 
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver 
from langchain.agents.middleware import SummarizationMiddleware , HumanInTheLoopMiddleware
import datetime 

class MainAgent: 
    def __init__(self):
        pass
    
    async def main_agent_tools(self):
        delegation_tools = [task_tool] 
        built_in_tools = [write_todos, read_todos , get_current_datetime] 
        all_tools = delegation_tools + built_in_tools

        return all_tools
    
    async def create_instructions(self):
        SUBAGENT_INSTRUCTIONS = SUBAGENT_USAGE_INSTRUCTIONS.format(
            max_concurrent_research_units=3,
            max_subAgent_iterations=5,
            date=datetime.datetime.now().strftime("%Y-%m-%d")
        )

        INSTRUCTIONS = (
        "# TODO MANAGEMENT\n"
        + TODO_USAGE_INSTRUCTIONS
        + "\n\n"
        + "CRITICAL: You MUST use write_todos tool for ANY user request to create a plan before proceeding.\n"
        + "=" * 80
        + "\n\n"
        + "# SUB-AGENT DELEGATION\n"
        + GENERAL_INSTRUCTIONS_ABOUT_SPECIFIC_TASKS_WHEN_CALLING_SUB_AGENTS 
        )
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
                        HumanInTheLoopMiddleware(
                        interrupt_on={
                                    "task": True    # interrupt with default approval
                                }
                    )
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


    

         
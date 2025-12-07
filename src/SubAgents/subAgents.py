import datetime
import yaml 
import asyncio

from src.Prompts.prompts import (
    DB_AGENT_INSTRUCTIONS,
    DB_ANALYZER_AGENT_INSTRUCTIONS,
    EXTERNAL_COMMUNICATION_AGENT_INSTRUCTIONS,
    AWS_S3_AGENT_INSTRUCTIONS,
    ANALYSIS_AGENT_INSTRUCTIONS,
    CALENDAR_AGENT_INSTRUCTIONS,
    AUTH_AGENT_INSTRUCTIONS,
    WEB_SEARCH_AGENT_INSTRUCTIONS,
    RAG_AGENT_INSTRUCTIONS,
)
from src.SubAgents.task_tool import _create_task_tool
from src.MCP.mcp import all_mcp_tools
from src.LLMs.GroqLLMs.llms import groq_moonshotai_llm
from src.States.state import DeepAgentState



class SubAgents: 
    def __init__(self):
        pass
    
    async def create_DB_Explorer_Agent(self): 
        
        with open("src/SubAgents/configs/db_explorer.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])

        filtered__db_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]

        DB_sub_agent = {
            "name": "Database_Agent",
            "description": "Delegate DB_Operations to the sub-agent DB. Only give this Agent one Task at the time.",
            "prompt": DB_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered__db_tools]  
        }
        return DB_sub_agent
    
    async def create_DB_Analyzer_Agent(self): 
        with open("src/SubAgents/configs/db_analyzer.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])

        filtered_db_analyzer_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]

        DB_analyzer_agent = {
            "name": "Database_Analyzer_Agent",
            "description": "Delegate DB_Analysis tasks to the sub-agent DB_Analyzer. Only give this Agent one Task at the time.",
            "prompt": DB_ANALYZER_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered_db_analyzer_tools] 
        }
        return DB_analyzer_agent
    
    async def create_External_Communication_Agent(self):
        with open("src/SubAgents/configs/EC.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])
        filtered_ec_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]
        EC_agent = {
            "name": "External_Communication_Agent",
            "description": "Delegate External_Communication tasks to the sub-agent EC. Only give this Agent one Task at the time.",
            "prompt": EXTERNAL_COMMUNICATION_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered_ec_tools] 
        }
        return EC_agent
    
    async def create_AWS_S3_Agent(self):
        with open("src/SubAgents/configs/aws_s3.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])
        filtered_s3_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]
        AWS_S3_agent = {
            "name": "AWS_S3_Agent",
            "description": "Delegate AWS_S3 tasks to the sub-agent AWS_S3. Only give this Agent one Task at the time.",
            "prompt": AWS_S3_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered_s3_tools]  
        }
        return AWS_S3_agent
    
    async def create_Analysis_Agent(self):
        with open("src/SubAgents/configs/analysis.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])
        filtered_analysis_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]
        Analysis_agent = {
            "name": "Analysis_Agent",
            "description": "Delegate Analysis tasks to the sub-agent Analysis. Only give this Agent one Task at the time.",
            "prompt": ANALYSIS_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered_analysis_tools]  
        }
        return Analysis_agent
    

    async def create_calendar_agent(self):
        with open("src/SubAgents/configs/calendar.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])
        filtered_calendar_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]
        Calendar_agent = {
            "name": "Calendar_Agent",
            "description": "Delegate Calendar tasks to the sub-agent Calendar. Only give this Agent one Task at the time.",
            "prompt": CALENDAR_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered_calendar_tools]  
        }
        return Calendar_agent
    
    async def create_Auth_Agent(self):
        with open("src/SubAgents/configs/auth.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])
        filtered_auth_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]
        Auth_agent = {
            "name": "Auth_Agent",
            "description": "Delegate Authentication tasks to the sub-agent Auth. Only give this Agent one Task at the time.",
            "prompt": AUTH_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered_auth_tools]  
        }
        return Auth_agent
    
    async def create_Web_Search_Agent(self):
        with open("src/SubAgents/configs/web_search.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])
        filtered_web_search_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]
        Web_Search_agent = {
            "name": "Web_Search_Agent",
            "description": "Delegate Web Search tasks to the sub-agent Web_Search. Only give this Agent one Task at the time.",
            "prompt": WEB_SEARCH_AGENT_INSTRUCTIONS.format(date=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")),
            "tools": [tool.name for tool in filtered_web_search_tools]  
        }
        return Web_Search_agent
    
    async def create_rag_agent(self):
        with open("src/SubAgents/configs/rag_service.yaml"  ,  "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        tool_names = []
        if isinstance(config, list) and len(config) > 0:
            tool_names = config[0].get("tools", [])
        filtered_rag_tools = [tool for tool in all_mcp_tools if tool.name in tool_names]
        RAG_agent = {
            "name": "RAG_Agent",
            "description": "Delegate RAG tasks to the sub-agent RAG. Only give this Agent one Task at the time.",
            "prompt": RAG_AGENT_INSTRUCTIONS,
            "tools": [tool.name for tool in filtered_rag_tools]  
        }
        return RAG_agent
    

    

    
    async def sub_agent_tools(self):
        # Return all MCP tools for sub-agents to use
        return all_mcp_tools
    

    async def create_task_tool(self):
        DB_sub_agent = await self.create_DB_Explorer_Agent()
        DB_analyzer_agent = await self.create_DB_Analyzer_Agent()
        EC_agent = await self.create_External_Communication_Agent()
        Calendar_agent = await self.create_calendar_agent()
        AWS_S3_agent = await self.create_AWS_S3_Agent()
        analysis_agent = await self.create_Analysis_Agent()
        Auth_agent = await self.create_Auth_Agent()
        Web_Search_agent = await self.create_Web_Search_Agent()
        RAG_agent = await self.create_rag_agent()

        sub_agent_tools = await self.sub_agent_tools()

        task_tool = _create_task_tool(
            tools=sub_agent_tools,
            subagents=[DB_sub_agent , DB_analyzer_agent, EC_agent , AWS_S3_agent , analysis_agent , Calendar_agent, Auth_agent, Web_Search_agent, RAG_agent],
            model=groq_moonshotai_llm,
            state_schema=DeepAgentState
        )
        return task_tool
    


task_tool = asyncio.run(SubAgents().create_task_tool())


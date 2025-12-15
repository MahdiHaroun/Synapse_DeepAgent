from langchain_community.tools.tavily_search import TavilySearchResults 
from mcp.server import FastMCP  
import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathlib import Path
import os


load_dotenv("/app/.env")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
mcp = FastMCP("web-server" , host="0.0.0.0", port=3020)


@mcp.tool()
async def web_search(query: str , number_of_results: int =3) -> list:
    """
    Perform a web search using Tavily and return summarized results.

    Arguments:
        query (str): The search query.
        number_of_results (int): Number of top results to return.

    Returns:
        list: A list of summarized search results.
    """
    search_tool = TavilySearchResults(k=number_of_results)
    results = await search_tool.arun(query)
    return results



@mcp.tool()
async def read_webpage(url: str) -> str:
    """
    Read and extract text content from a specified webpage URL.

    Arguments:
        url (str): The URL of the webpage to read.
    Returns:
        str: The extracted text content from the webpage.
    """


    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html_content = await response.text()

    soup = BeautifulSoup(html_content, 'html.parser')
    text_content = soup.get_text(separator='\n', strip=True)
    return text_content



if __name__ == "__main__":
    mcp.run(transport="sse")
import os
from typing import List, Dict, Any, Optional
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import Runnable
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch
from langchain_community.tools.semanticscholar.tool import SemanticScholarQueryRun
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_experimental.tools.python.tool import PythonREPLTool
from crawler import SimpleCrawl4AITool, AdvancedCrawl4AITool, SmartExtractionTool, BatchCrawl4AITool
import json
import sys
from io import StringIO
import traceback
import re

# Initialize the global list to store captured figures
_captured_figures: List[str] = []

def get_captured_figures() -> List[str]:
    """Get any captured Plotly figures as JSON strings."""
    global _captured_figures
    print(f"Getting captured figures: {len(_captured_figures)} available")
    return _captured_figures.copy()

def clear_captured_figures():
    """Clear the captured figures."""
    global _captured_figures
    count = len(_captured_figures)
    _captured_figures.clear()
    print(f"Cleared {count} captured figures")

def load_system_prompt() -> str:
    """Load the system prompt from the esi_agent_instruction.md file."""
    try:
        with open("esi_agent_instruction.md", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return """You are ESI, a helpful AI research assistant. You have access to web search and academic paper search tools.
        
Your capabilities include:
1. Searching the web for current information using Tavily
2. Finding academic papers and research using Semantic Scholar
3. Creating data visualizations using Plotly (NOT matplotlib)
4. Providing comprehensive, well-researched answers

When creating visualizations:
- ALWAYS use Plotly (plotly.express as px or plotly.graph_objects as go)
- NEVER use matplotlib.pyplot - it's not supported
- Use fig.show() to display plots - this will capture them for display
- Available libraries: pandas, numpy, plotly, scipy, sklearn

Always cite your sources and provide accurate, helpful information."""

def create_tavily_tool() -> Tool:
    """Create the Tavily search tool."""
    # Initialize Tavily search
    tavily_search = TavilySearch(
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
        include_images=False
    )
    
    return Tool(
        name="tavily_search",
        description="Search the web for current information, news, and general knowledge. Use this for real-time information, current events, or when you need up-to-date web content.",
        func=tavily_search.run
    )


def create_agent(temperature: float = 0.5, model: str = "gemini-2.5-flash", verbosity: int = 3) -> Runnable:
    """Create and configure the React agent with tools."""
    
    # Load environment variables
    google_api_key = os.getenv("GOOGLE_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
 
    
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY environment variable is required")
    
    # Initialize the LLM based on the selected model
    if model.startswith("gemini"):
        if not google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required for Gemini models")
        llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            google_api_key=google_api_key,
        )
    else: # Assume OpenRouter model
        if not openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required for OpenRouter models")
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=openrouter_api_key, # Use openai_api_key for OpenRouter
            base_url="https://openrouter.ai/api/v1",
        )
    
    # Create tools
    tools = [
        create_tavily_tool(),
        SemanticScholarQueryRun(top_k_results=10),
        WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper()),
        PythonREPLTool(), # Reverted to original PythonREPLTool
        SimpleCrawl4AITool(),
        AdvancedCrawl4AITool(),
        SmartExtractionTool(),
        BatchCrawl4AITool()
    ]


    # Load system prompt
    system_prompt = load_system_prompt()

    # Adjust system prompt based on verbosity
    if verbosity == 1:
        system_prompt += "\n\nYour responses should be extremely concise and laconic. Get straight to the point."
    elif verbosity == 2:
        system_prompt += "\n\nYour responses should be concise and to the point, avoiding unnecessary details."
    elif verbosity == 4:
        system_prompt += "\n\nYour responses should be detailed and provide ample explanation."
    elif verbosity == 5:
        system_prompt += "\n\nYour responses should be extremely verbose, comprehensive, and elaborate on all points."
    
    # Create the React agent
    agent = create_react_agent(
        llm,
        tools=tools,
        prompt = system_prompt,
    )
    
    return agent

if __name__ == "__main__":
    # Test the agent creation
    try:
        # Set dummy API keys for testing purposes if not already set
        os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "YOUR_DUMMY_GOOGLE_API_KEY")
        os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "YOUR_DUMMY_TAVILY_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "YOUR_DUMMY_OPENROUTER_API_KEY")


        print("Testing agent creation with default Gemini model...")
        agent = create_agent()
        print("Agent created successfully with Gemini model!")
        
        print("\nTesting agent creation with an OpenRouter model...")
        agent_openrouter = create_agent(model="mistralai/mistral-small-3.2-24b-instruct:free")
        print("Agent created successfully with OpenRouter model!")

        # Test query (this part might require actual API keys to run successfully)
        # test_query = "Create a simple scatter plot using plotly"
        # result = agent.invoke({"input": test_query})
        # print(f"Test result: {result}")
        
        # Check if figures were captured
        # figures = get_captured_figures()
        # print(f"Captured {len(figures)} figures during test")
        
    except Exception as e:
        print(f"Error creating agent: {e}")
        import traceback
        traceback.print_exc()

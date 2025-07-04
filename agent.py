import os
from typing import List, Dict, Any
from langgraph.prebuilt import create_react_agent
from langchain_core.runnables import Runnable
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain_community.tools.semanticscholar.tool import SemanticScholarQueryRun
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

def load_system_prompt() -> str:
    """Load the system prompt from the esi_agent_instruction.md file."""
    try:
        with open("esi_agent_instruction.md", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return """You are a helpful AI research assistant. You have access to web search and academic paper search tools.
        
Your capabilities include:
1. Searching the web for current information using Tavily
2. Finding academic papers and research using Semantic Scholar
3. Providing comprehensive, well-researched answers

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

def create_agent(temperature: float = 0.1, model: str = "gemini-2.5-flash") -> Runnable:
    """Create and configure the React agent with tools."""
    
    # Load environment variables
    google_api_key = os.getenv("GOOGLE_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is required")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY environment variable is required")
    
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=google_api_key,
    )
    
    # Create tools
    tools = [
        create_tavily_tool(),
        SemanticScholarQueryRun(top_k_results=10),
        WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())
    ]
    
    # Load system prompt
    system_prompt = load_system_prompt()
    
    # Create the React agent
    agent = create_react_agent(
        llm,
        tools=tools
    )
    
    return agent

if __name__ == "__main__":
    # Test the agent creation
    try:
        agent = create_agent()
        print("Agent created successfully!")
        
        # Test query
        test_query = "What are the latest developments in artificial intelligence?"
        result = agent.invoke({"input": test_query})
        print(f"Test result: {result}")
        
    except Exception as e:
        print(f"Error creating agent: {e}")
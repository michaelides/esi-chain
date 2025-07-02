import os
from typing import List, Dict, Any
from langchain.agents import create_react_agent, AgentExecutor
from langchain.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain_community.tools.semanticscholar.tool import SemanticScholarQueryRun

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



def create_agent(max_iterations: int = 15, max_execution_time: int = 120, temperature: float = 0.1) -> AgentExecutor:
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
        model="gemini-2.5-flash",
        temperature=temperature,
        google_api_key=google_api_key,
    )
    
    # Create tools
    tools = [
        create_tavily_tool(),
        SemanticScholarQueryRun()
    ]
    
    # Load system prompt
    system_prompt = load_system_prompt()
    
    # Create the React prompt template
    react_prompt = PromptTemplate.from_template(f"""
{system_prompt}

You have access to the following tools:

{{tools}}

To use a tool, please use the following format:

Thought: Do I need to use a tool? Yes
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action

When you have a response to say to the Human, or if you do not need to use a tool, you MUST use the format:

Thought: Do I need to use a tool? No
Final Answer: [your response here]

Begin!

Question: {{input}}
Thought:{{agent_scratchpad}}
""")
    
    # Create the React agent
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=react_prompt
    )
    
    # Create the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=lambda error: f"A formatting error occurred: {error}. Please try again, ensuring your response strictly follows the required format.",
        max_iterations=15,
        max_execution_time=max_execution_time
    )
    
    return agent_executor

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
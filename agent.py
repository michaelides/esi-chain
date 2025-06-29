
import os
from dotenv import load_dotenv
from llama_index.core.tools import FunctionTool
from llama_index.llms.gemini import Gemini
from llama_index.core.agent import ReActAgent
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.tools.tavily_research import TavilyToolSpec
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.readers.web import SimpleWebPageReader
from llama_index.readers.file import PDFReader
from llama_index.tools.code_interpreter import CodeInterpreterToolSpec
import chainlit as cl
import chromadb
import requests
from bs4 import BeautifulSoup
from semanticscholar import SemanticScholar

# Load environment variables
load_dotenv()
gemini_key=os.getenv("GEMINI_API_KEY")

# --- Tool Implementations ---

def tavily_search(query: str):
    """Performs a web search using Tavily."""
    tavily_tool = TavilyToolSpec(api_key=os.getenv("TAVILY_API_KEY"))
    return tavily_tool.search(query)

def semantic_scholar_search(query: str):
    """Searches for academic papers on Semantic Scholar."""
    ss = SemanticScholar()
    results = ss.search_paper(query)
    return [str(paper) for paper in results]

def web_scraper(url: str):
    """Scrapes content from a given URL."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    return soup.get_text()

def pdf_scraper(file_path: str):
    """Scrapes content from a local PDF file."""
    reader = PDFReader()
    documents = reader.load_data(file_path)
    return "\n".join([doc.text for doc in documents])

# --- Agent Setup ---

def create_agent(temperature=0.7):
    """Creates and configures the ReActAgent."""
    # Load system prompt
    with open("esi_agent_instruction.md", "r") as f:
        system_prompt = f.read()

    # Initialize LLM
    llm = Gemini(
        model_name="models/gemini-2.5-flash",
        api_key=gemini_key,
        temperature=temperature,
    )

    # Initialize Tools
    tavily_tool = FunctionTool.from_defaults(fn=tavily_search)
    semantic_scholar_tool = FunctionTool.from_defaults(fn=semantic_scholar_search)
    web_scraper_tool = FunctionTool.from_defaults(fn=web_scraper)
    pdf_scraper_tool = FunctionTool.from_defaults(fn=pdf_scraper)
    code_interpreter_tool = CodeInterpreterToolSpec()

    # RAG Tool
    db = chromadb.PersistentClient(path="./chroma_db")
    chroma_collection = db.get_or_create_collection("esi_collection")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    rag_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    rag_tool = rag_index.as_query_engine().as_tool()

    # Memory
    memory = ChatMemoryBuffer.from_defaults(token_limit=15000)

    # Create Agent
    agent = ReActAgent.from_tools(
        tools=[
            tavily_tool,
            semantic_scholar_tool,
            web_scraper_tool,
            pdf_scraper_tool,
            code_interpreter_tool,
            rag_tool,
        ],
        llm=llm,
        memory=memory,
        system_prompt=system_prompt,
        verbose=True,
    )

    cl.user_session.set("agent", agent)
    return agent

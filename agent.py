import os
from typing import List

import chainlit as cl
from dotenv import load_dotenv
from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.agent import AgentRunner, ReActAgent
from llama_index.core.chat_engine import ContextChatEngine
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.tools import FunctionTool
from llama_index.embeddings.google import GoogleGenerativeAIEmbeddings
from llama_index.llms.google import GoogleGenerativeAI
from llama_index.vector_stores.chroma import ChromaVectorStore

# Load environment variables from .env file
load_dotenv()

# Configure Google API key
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# Initialize the LLM
llm = GoogleGenerativeAI(model="models/gemini-1.5-flash-latest")

# Configure LlamaIndex global settings
Settings.llm = llm
Settings.embed_model = GoogleGenerativeAIEmbeddings(model_name="models/text-embedding-004")


def get_tools() -> List[FunctionTool]:
    """
    Returns a list of FunctionTool objects that the agent can use.
    """
    # Example tool: a simple calculator
    def calculator(a: int, b: int, operation: str) -> int:
        """
        Performs a basic arithmetic operation on two numbers.
        Args:
            a (int): The first number.
            b (int): The second number.
            operation (str): The operation to perform ('add', 'subtract', 'multiply', 'divide').
        Returns:
            int: The result of the operation.
        """
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Cannot divide by zero.")
            return a / b
        else:
            raise ValueError("Invalid operation. Choose from 'add', 'subtract', 'multiply', 'divide'.")

    calculator_tool = FunctionTool.from_defaults(fn=calculator)

    # Example tool: a simple search function (placeholder)
    def search_web(query: str) -> str:
        """
        Searches the web for a given query and returns a summary of the results.
        Args:
            query (str): The search query.
        Returns:
            str: A summary of the search results.
        """
        return f"Searching the web for '{query}'... (This is a placeholder. Real search functionality would go here.)"

    search_tool = FunctionTool.from_defaults(fn=search_web)

    return [calculator_tool, search_tool]


def create_agent():
    """
    Creates and returns a ReActAgent instance.
    """
    # Load documents (if any)
    # documents = SimpleDirectoryReader("data").load_data()

    # Initialize ChromaDB client and collection (assuming it's already set up or will be)
    # For a persistent client, you might need:
    # import chromadb
    # db = chromadb.PersistentClient(path="./chroma_db")
    # chroma_collection = db.get_or_create_collection("my_collection")

    # Placeholder for chroma_collection if not using persistent client or specific collection
    # For demonstration, let's assume a simple in-memory ChromaDB for now if no persistent client is configured.
    # In a real application, you'd connect to your ChromaDB instance.
    # For now, let's create a dummy collection if not provided.
    try:
        import chromadb
        db = chromadb.Client() # Or chromadb.PersistentClient(path="./chroma_db")
        chroma_collection = db.get_or_create_collection("my_default_collection")
    except Exception as e:
        print(f"Could not initialize ChromaDB client: {e}. Proceeding without a specific collection.")
        chroma_collection = None # Or handle this case as appropriate

    # Initialize the vector store with the ChromaDB collection
    # Ensure you have `llama-index-vector-stores-chroma` installed
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    # Create a RAG index from the vector store
    rag_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)

    # Create a query engine from the RAG index
    rag_query_engine = rag_index.as_query_engine()

    # Define a tool for the RAG query engine
    rag_tool = FunctionTool.from_defaults(
        fn=lambda query: rag_query_engine.query(query),
        name="rag_query_engine",
        description="Useful for answering questions about documents in the knowledge base.",
    )

    # Get other tools
    tools = get_tools()
    tools.append(rag_tool)

    # Initialize chat memory
    memory = ChatMemoryBuffer.from_defaults(token_limit=3900)

    # Create the ReAct agent
    agent = ReActAgent(
        llm=llm,
        memory=memory,
        tools=tools,
        verbose=True,
    )
    return agent


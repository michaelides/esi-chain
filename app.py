import chainlit as cl
from chainlit.input_widget import Select, Slider, Switch
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer
from chainlit.types import ThreadDict
from agent import create_agent, get_captured_figures, clear_captured_figures
import asyncio
from typing import Dict, Optional
import os
import json
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agent import load_system_prompt
import random
from dotenv import load_dotenv

load_dotenv()

OAUTH_GOOGLE_CLIENT_ID = os.getenv("OAUTH_GOOGLE_CLIENT_ID")
OAUTH_GOOGLE_CLIENT_SECRET = os.getenv("OAUTH_GOOGLE_CLIENT_SECRET")

# Global agent variable
agent = None

THINKING_PHRASES_FILE = "thinking_phrases.md"
_thinking_phrases = []
def load_thinking_phrases():
    """Loads thinking phrases from the specified markdown file."""
    global _thinking_phrases
    try:
        with open(THINKING_PHRASES_FILE, "r", encoding="utf-8") as f:
            _thinking_phrases = [line.strip() for line in f if line.strip()]
    except Exception as e:
        _thinking_phrases = ["Thinking..."]

@cl.password_auth_callback
def auth_callback(username: str, password: str):
    # Fetch the user matching username from your database
    # and compare the hashed password with the value stored in the database
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
            return None
@cl.oauth_callback
def oauth_callback(
  provider_id: str,
  token: str,
  raw_user_data: Dict[str, str],
  default_user: cl.User,
) -> Optional[cl.User]:
  return default_user

# In-memory user database (replace with a real database in production)
# users = {}

# def create_user(username, password):
#     """Creates a new user."""
#     if username in users:
#         return False  # User already exists
#     users[username] = password
#     return True

# def auth_callback(username: str, password: str):
#     """Authenticates a user."""
#     if username in users and users[username] == password:
#         return cl.User(
#             identifier=username, metadata={"provider": "credentials"}
#         )
#     else:
#         return None


@cl.data_layer
def get_data_layer():
    """Initialize SQLAlchemy data layer with async database connection"""
    # Create data directory if it doesn't exist
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    # SQLite connection string - using aiosqlite for async support
    # This is required by Chainlit's SQLAlchemy data layer
    db_path = os.path.join(data_dir, "chainlit_app.db")
    
    # Use async SQLite connection (requires aiosqlite)
    conninfo = f"sqlite+aiosqlite:///{db_path}"
    
    print(f"Initializing async database at: {db_path}")
    
    try:
        data_layer = SQLAlchemyDataLayer(conninfo=conninfo)
        print("SQLAlchemy data layer initialized successfully")
        return data_layer
    except Exception as e:
        print(f"Error initializing data layer: {e}")
        print("Make sure to install aiosqlite: pip install aiosqlite")
        # Return None to use in-memory storage as fallback
        return None

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="New topic",
            message="Can you help me to identify a new research topic or question for my dissertation?",
            icon="public/idea.svg",
        ),
        cl.Starter(
            label="Refine hypotheses",
            message="I already know my research question but I need help developing my hypotheses",
            icon="public/research.svg",
        ),
        cl.Starter(
            label="Design the study",
            message="I need help with my study design",
            icon="public/plan.svg",
        ),
        cl.Starter(
            label="Data analysis",
            message="I've collected my data but I need help with my analysis",
            icon="public/data.svg",
        ),
        # cl.Starter(
        #     label="Create a plot",
        #     message="Create a simple plot of y=x using Plotly",
        #     icon="public/chart.svg",
        # ),
        cl.Starter(
            label="What can you do?",
            message="Explain what you can do, and how you can help me with my dissertation",
            icon="public/ai.svg",
        )
    ]


@cl.on_settings_update
async def setup_agent(settings):
    """Handle settings updates."""
    global agent
    print(f"Settings updated: {settings}")
    
    try:
        # Recreate agent with new settings
        agent = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_agent(
                temperature=settings.get("temperature", 1.0),
                model=settings.get("model", "gemini-2.5-flash"),
                verbosity=settings.get("verbosity", 3)
            )
        )
        
        temperature = settings.get("temperature", 1.0)
        model = settings.get("model", "gemini-2.5-flash")
        include_sources = settings.get("include_sources", True)
        verbosity = settings.get("verbosity", 3)
        await cl.Message(
            content=f"✅ Settings updated successfully!\n- Temperature: {temperature}\n- Model: {model}\n- Include sources: {include_sources}\n- Verbosity: {verbosity}"
        ).send()
        
    except Exception as e:
        await cl.Message(content=f"❌ Error updating settings: {str(e)}" ).send()
        
async def display_plotly_figures():
    """Check for and display any captured Plotly figures using cl.Pyplot."""
    try:
        figures = get_captured_figures()
        if figures:
            await cl.Message(content=f"📊 **{len(figures)} visualization(s) generated:**").send()
            
            for i, fig_json in enumerate(figures):
                try:
                    # Parse the JSON and create a Plotly figure
                    fig_dict = json.loads(fig_json)
                    fig = go.Figure(fig_dict)
                    
                    # Use cl.plotly to display the figure
                    plotly_element = [cl.Plotly(
                        name=f"plot_{i+1}",
                        figure=fig,
                        display="inline"
                    )]
                    await cl.Message(content="This message has a chart", elements=plotly_element).send()
                    print(f"Successfully displayed plot {i+1} using cl.Pyplot")
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error for plot {i+1}: {e}")
                    await cl.Message(
                        content=f"❌ Error parsing plot {i+1}: Invalid JSON data"
                    ).send()
                except Exception as e:
                    print(f"Error processing plot {i+1}: {e}")
                    await cl.Message(
                        content=f"❌ Error processing plot {i+1}: {str(e)}"
                    ).send()
            
            # Clear the captured figures after processing
            clear_captured_figures()
            
    except Exception as e:
        print(f"Error in display_plotly_figures: {e}")
        import traceback
        traceback.print_exc()
        # Still try to clear figures even if there was an error
        clear_captured_figures()

@cl.on_chat_start
async def start():
    """Initialize the agent when a new chat session starts."""
    global agent
    # load thinking phrases
    load_thinking_phrases()

    # Define and send settings
    settings = await cl.ChatSettings([
        Slider(
            id="temperature",
            label="Temperature",
            initial=1.0,
            min=0,
            max=2,
            step=0.1,
            description="Controls creativity and randomness in responses."
        ),
        Select(
            id="model",
            label="Model",
            values=[
                "gemini-2.5-flash",
                "mistralai/mistral-small-3.2-24b-instruct:free",
            #    "qwen/qwen3-235b-a22b:free",
            #    "openrouter/cypher-alpha:free",
                "deepseek/deepseek-chat-v3-0324:free",
            #    "thudm/glm-4-32b:free",
                "moonshotai/kimi-k2"
            #    "meta-llama/llama-3.3-70b-instruct:free"
            ],
            initial_index=0,
            description="Select the AI model to use for responses."
        ),
        Switch(
            id="include_sources",
            label="Include Sources",
            initial=True,
            description="Whether to include source citations in responses."
        ),
        Slider(
            id="verbosity",
            label="Verbosity",
            initial=3,
            min=1,
            max=5,
            step=1,
            description="Controls the length and detail of responses (1: Laconic, 5: Extremely Verbose)."
        )
    ]).send()

    # # Initialize chat history
    # cl.user_session.set("chat_history", [])

    try:
        # Create the agent with initial settings
        agent = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_agent(
                temperature=settings.get("temperature", 1.0),
                model=settings.get("model", "gemini-2.5-flash"),
                verbosity=settings.get("verbosity", 3)
            )
        )
    except Exception as e:
        error_msg = f"❌ Error initializing agent: {str(e)}"
        await cl.Message(content=error_msg).send()



@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    memory = ConversationBufferMemory(return_messages=True)
    root_messages = [m for m in thread["steps"] if m["parentId"] == None]
    for message in root_messages:
        if message["type"] == "user_message":
            memory.chat_memory.add_user_message(message["output"])
        else:
            memory.chat_memory.add_ai_message(message["output"])

    cl.user_session.set("memory", memory)

    setup_runnable()




@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages and process them with the agent."""
    global agent

    response_message = cl.Message(content=random.choice(_thinking_phrases))
    await response_message.send()

    try:
        chat_history = cl.user_session.get("chat_history", [])
        
        # Add the new user message to history
        chat_history.append(HumanMessage(content=message.content))
        
        # Prepare the input for the agent
        agent_input = {"messages": chat_history}
        
        # Track the full response content for the final message
        full_response_content = ""
        
        # To store the final AIMessage for history
        final_ai_message_obj: Optional[AIMessage] = None
        
        is_first_token = True # Flag to track the first actual LLM token
        
        # Stream the agent's response using astream_events for token-level granularity
        async for event in agent.astream_events(agent_input, version="v1"):
            kind = event["event"]
#            print(f"Received event kind: {kind}") # Debug print
            
            if kind == "on_chat_model_stream":
                # This event provides token-level chunks from the LLM
                token = event["data"]["chunk"].content
                if token:
                    if is_first_token:
                        # Clear "Thinking..." and start actual streaming
                        response_message.content = ""
                        await response_message.update()
                        is_first_token = False

#                    print(f"Streaming token: '{token}'") # Debug print
                    
                    # Split by space to simulate word-by-word streaming
                    words = token.split(' ')
                    for i, word in enumerate(words):
                        await response_message.stream_token(word)
                        if i < len(words) - 1: # Add space between words
                            await response_message.stream_token(" ")
                        await asyncio.sleep(0.005) # Small delay for visual effect
                    
                    full_response_content += token # Accumulate original token for history
            
            elif kind == "on_chain_end":
                print(f"Chain end event: {event['name']}") # Debug print
                # This event signifies the end of a chain or the overall graph.
                # The final output of the agent is usually in event["data"]["output"]
                if "output" in event["data"] and event["data"]["output"] is not None and "messages" in event["data"]["output"]:
                    # Find the last AIMessage in the final output messages
                    for msg in reversed(event["data"]["output"]["messages"]):
                        if isinstance(msg, AIMessage):
                            final_ai_message_obj = msg
                            break
        
        # After streaming, add the complete AI response to chat history
        # Use the accumulated streamed content for the AIMessage content.
        if final_ai_message_obj:
            final_ai_message_obj.content = full_response_content
            chat_history.append(final_ai_message_obj)
        elif full_response_content:
            # Fallback if no specific AIMessage object was found from on_chain_end
            chat_history.append(AIMessage(content=full_response_content))
        
        # Check for plots after the stream is complete
        print("Checking for captured figures...")
        await display_plotly_figures()
        
        # Update the chat history in the session
        cl.user_session.set("chat_history", chat_history)
        
        # Ensure the response message is fully updated (though stream_token does this incrementally)
        await response_message.update()

    except Exception as e:
        error_msg = f"❌ Error processing message: {str(e)}"
        print(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
        await cl.Message(content=error_msg).send()

@cl.on_stop
async def stop():
    """Clean up when the chat session ends."""
    global agent
    agent = None
    print("Chat session ended, agent cleaned up.")

if __name__ == "__main__":
    pass
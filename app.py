import chainlit as cl
from chainlit.input_widget import Select, Slider
from agent import create_agent
import asyncio
from typing import Optional
import os

from langchain_core.messages import HumanMessage, SystemMessage
from agent import create_agent, load_system_prompt

# Global agent variable
agent = None

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="New topic",
            message="Can you help me to identify a new research topic or question for my dissertation? ",
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
            message="I 've collected my data but I need help with my analysis", 
            icon="public/data.svg",
            ),
        cl.Starter(
            label="What can you do?",
            message="Explain what you can do, and how you can help me with my dissertation",
            icon="public/ai.svg",
            )
        ]
@cl.on_chat_start
async def start():
    """Initialize the agent when a new chat session starts."""
    global agent

    # Greet the user
    user = cl.user_session.get("user")
    # if user:
    #     await cl.Message(
    #         content=f"Hello, {user.identifier}!\nI'm ESI, your AI research assistant. How can I help you today?"
    #     ).send()
    # else:
    #     await cl.Message(
    #         content="Welcome! I'm ESI, your AI research assistant. How can I help you today?"
    #     ).send()

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
            values=["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            initial_index=0,
            description="Select the AI model to use for responses."
        ),
    ]).send()

    # Initialize chat history
    cl.user_session.set("chat_history", [])

    try:
        # Create the agent with initial settings
        agent = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_agent(
                temperature=settings.get("temperature", 0.1),
                model=settings.get("model", "gemini-2.5-flash")
            )
        )
    except Exception as e:
        error_msg = f"❌ Error initializing agent: {str(e)}"
        await cl.Message(content=error_msg).send()

@cl.on_settings_update
async def setup_agent(settings):
    """Handle settings updates."""
    global agent
    print(f"Settings updated: {settings}")
    
    try:
        # Recreate agent with new settings
        agent = await asyncio.get_event_loop().run_in_executor(
            None, lambda: create_agent(
                temperature=settings.get("temperature", 0.5),
                model=settings.get("model", "gemini-2.5-flash")
            )
        )
        
        temperature = settings.get("temperature", 0.5)
        model = settings.get("model", "gemini-2.5-flash")
        
        await cl.Message(
            content=f"✅ Settings updated successfully!\n- Temperature: {temperature}\n- Model: {model}\n"
        ).send()
        
    except Exception as e:
        await cl.Message(content=f"❌ Error updating settings: {str(e)}").send()



@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages and process them with the agent."""
    global agent
    
    # Pass cl.emit_user_message as the sendMessage function
    suggestions = cl.CustomElement(
        name="FollowUpSuggestions", 
        suggestions=["Foo", "Bar"], # These are still hardcoded, will address LLM generation later
        sendMessage=cl.emit_user_message # Corrected: Pass the emit_user_message function
    )

    if not agent:
        await cl.Message(content="❌ Agent not initialized. Please refresh the page.").send()
        return

    # Create a new message for the response
    response_message = cl.Message(content="Suggestions:", elements=[suggestions])
    await response_message.send()

    # Stream the agent's response
    try:
        chat_history = cl.user_session.get("chat_history")
        if chat_history is None:
            chat_history = []
            cl.user_session.set("chat_history", chat_history)

        system_prompt_content = load_system_prompt()
        
        if not chat_history:
            chat_history.append(SystemMessage(content=system_prompt_content))

        chat_history.append(HumanMessage(content=message.content))

        async for s in agent.astream({"messages": chat_history}):
            print(s) # Print the raw stream chunk for debugging
            for key, value in s.items():
                if isinstance(value, dict) and "messages" in value:
                    for message_obj in value["messages"]:
                        if hasattr(message_obj, "content"):
                            await response_message.stream_token(message_obj.content)
                            if key == "agent":
                                chat_history.append(message_obj)
                            elif key == "tools":
                                chat_history.append(message_obj)
        
        cl.user_session.set("chat_history", chat_history)
        await response_message.update()

    except Exception as e:
        error_msg = f"❌ Error processing message: {str(e)}"
        await cl.Message(content=error_msg).send()

@cl.on_stop
async def stop():
    """Clean up when the chat session ends."""
    global agent
    agent = None
    print("Chat session ended, agent cleaned up.")

# @cl.oauth_callback
# def oauth_callback(
#   provider_id: str,
#   token: str,
#   raw_user_data: dict[str, str],
#   default_user: cl.User,
# ) -> Optional[cl.User]:
#   return default_user

if __name__ == "__main__":
    pass

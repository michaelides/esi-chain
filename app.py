import chainlit as cl
from chainlit.input_widget import Select, Slider
from agent import create_agent
import asyncio
from typing import Optional
import os

from langchain_core.messages import HumanMessage, SystemMessage
from agent import create_agent, load_system_prompt

# New imports for LLM-generated suggestions
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
import json

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

# Define a wrapper function to emit user messages
async def send_message_to_frontend(message_content: str):
    await cl.emit_user_message(message_content)

async def generate_follow_up_suggestions(chat_history: list) -> list[str]:
    """Generates follow-up suggestions based on the chat history."""
    
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        print("Error: GOOGLE_API_KEY environment variable not set. Cannot generate follow-up suggestions.")
        return []

    suggestion_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an AI assistant specialized in generating concise follow-up questions or suggestions for a user's research dissertation.
        Based on the provided chat history, generate 3-5 short, relevant, and distinct follow-up suggestions that the user might want to ask next.
        Focus on moving the conversation forward in a helpful way for dissertation research.
        Output the suggestions STRICTLY as a JSON array of strings, like this example:
        ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
        Do NOT include any other text, explanations, or formatting outside the JSON array.
        """),
        ("human", "Chat history:\n{chat_history}\n\nGenerate follow-up suggestions:")
    ])

    # Use a simple LLM for this task, potentially the same model as the agent
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1, google_api_key=google_api_key)

    chain = suggestion_prompt | llm

    # Pass the relevant part of the chat history (last 5 messages to manage token limits)
    history_str = "\n".join([f"{msg.type}: {msg.content}" for msg in chat_history[-5:]])
    
    try:
        response = await chain.ainvoke({"chat_history": history_str})
        suggestions_raw = response.content.strip()
        
        print(f"Raw LLM suggestions response: {suggestions_raw}") # Debugging line
        
        # Clean up potential markdown code blocks
        if suggestions_raw.startswith("```json") and suggestions_raw.endswith("```"):
            suggestions_raw = suggestions_raw[7:-3].strip()
        
        suggestions_list = json.loads(suggestions_raw)
        print(f"Parsed suggestions: {suggestions_list}") # Debugging line

        if isinstance(suggestions_list, list) and all(isinstance(s, str) for s in suggestions_list):
            return suggestions_list
        else:
            print(f"Warning: LLM returned non-list or non-string suggestions: {suggestions_list}")
            return []
    except json.JSONDecodeError as e:
        print(f"Error parsing LLM suggestions JSON: {e}")
        print(f"Raw LLM response that caused error: {suggestions_raw}") # More specific error logging
        return []
    except Exception as e:
        print(f"Error generating follow-up suggestions: {e}")
        return []

@cl.on_message
async def main(message: cl.Message):
    """Handle incoming messages and process them with the agent."""
    global agent
    
    if not agent:
        await cl.Message(content="❌ Agent not initialized. Please refresh the page.").send()
        return

    # Initialize chat history
    chat_history = cl.user_session.get("chat_history")
    if chat_history is None:
        chat_history = []
        cl.user_session.set("chat_history", chat_history)

    system_prompt_content = load_system_prompt()
    
    if not chat_history:
        chat_history.append(SystemMessage(content=system_prompt_content))

    chat_history.append(HumanMessage(content=message.content))

    # Create a placeholder message for the agent's response
    agent_response_message = cl.Message(content="")
    await agent_response_message.send()

    # Stream the agent's response
    try:
        async for s in agent.astream({"messages": chat_history}):
            print(s) # Print the raw stream chunk for debugging
            for key, value in s.items():
                if isinstance(value, dict) and "messages" in value:
                    for message_obj in value["messages"]:
                        if hasattr(message_obj, "content"):
                            await agent_response_message.stream_token(message_obj.content)
                            if key == "agent":
                                chat_history.append(message_obj)
                            elif key == "tools":
                                chat_history.append(message_obj)
        
        cl.user_session.set("chat_history", chat_history)
        await agent_response_message.update()

        # After the agent's response, generate and send follow-up suggestions
        generated_suggestions = await generate_follow_up_suggestions(chat_history)
        
        print(f"Final generated_suggestions for frontend: {generated_suggestions}") # Debugging line

        if generated_suggestions:
            suggestions_element = cl.CustomElement(
                name="FollowUpSuggestions", 
                suggestions=generated_suggestions,
                sendMessage=send_message_to_frontend
            )
            # Send the suggestions as a new message containing only the custom element
            await cl.Message(content="", elements=[suggestions_element]).send()

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

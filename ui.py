
import chainlit as cl
from agent import create_agent

@cl.on_chat_start
async def on_chat_start():
    """Initializes the agent and settings when a new chat starts."""
    # Set initial temperature for the agent
    initial_temperature = 0.7
    cl.user_session.set("agent", create_agent(temperature=initial_temperature))
    await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="LLM",
                label="LLM",
                values=["gemini-2.5-flash"], # Note: This is a UI label, actual model is set in agent.py
                initial_value="gemini-2.5-flash",
            ),
            cl.input_widget.Slider(
                id="Temperature",
                label="Temperature",
                min=0.0,
                max=1.0,
                step=0.1,
                initial=initial_temperature, # Use the initial temperature here
                description="Controls the randomness of the model's output.",
            ),
        ]
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handles incoming user messages."""
    agent = cl.user_session.get("agent")
    response = await agent.astream_chat(message.content)
    msg = cl.Message(content="")
    await msg.send()

    for token in response.response_gen:
        await msg.stream_token(token)
    await msg.update()

@cl.on_settings_update
async def on_settings_update(settings):
    """Updates the agent when settings are changed."""
    # Recreate the agent with the new temperature setting
    cl.user_session.set("agent", create_agent(temperature=settings["Temperature"]))
    await cl.Message("Agent settings updated.").send()

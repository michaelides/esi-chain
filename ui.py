
import chainlit as cl
from agent import create_agent

@cl.on_chat_start
async def on_chat_start():
    """Initializes the agent and settings when a new chat starts."""
    cl.user_session.set("agent", create_agent())
    await cl.ChatSettings(
        [
            cl.input_widget.Select(
                id="LLM",
                label="LLM",
                values=["gemini-2.5-flash"],
                initial_value="gemini-2.5-flash",
            ),
            cl.input_widget.Slider(
                id="Temperature",
                label="Temperature",
                min=0.0,
                max=1.0,
                step=0.1,
                initial=0.7,
                description="Controls the randomness of the model's output.",
            ),
        ]
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handles incoming user messages."""
    agent = cl.user_session.get("agent")
    response = await agent.astream_chat(message.content)

    # Stream the response
    msg = cl.Message(content="")
    async for token in response.async_stream_tokens():
        await msg.stream_token(token)
    await msg.send()

@cl.on_settings_update
async def on_settings_update(settings):
    """Updates the agent when settings are changed."""
    create_agent(temperature=settings["Temperature"])
    await cl.Message("Agent settings updated.").send()

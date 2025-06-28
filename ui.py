import chainlit as cl
import os
import re
import json
from typing import List, Dict, Any, Optional, Callable
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import io

# Assuming tools.py and its UI_ACCESSIBLE_WORKSPACE are still relevant
from tools import UI_ACCESSIBLE_WORKSPACE

# Placeholder for app.py callbacks - these will need to be properly integrated
# For now, we'll define dummy versions or assume they are set globally by app.py
# This is a critical part that needs careful handling when integrating with app.py

# --- Callbacks that app.py will need to provide ---
# reset_callback: Optional[Callable] = None
# new_chat_callback: Optional[Callable] = None
# delete_chat_callback: Optional[Callable] = None
# rename_chat_callback: Optional[Callable] = None
# switch_chat_callback: Optional[Callable] = None
# get_discussion_markdown_callback: Optional[Callable] = None
# get_discussion_docx_callback: Optional[Callable] = None
# handle_user_input_callback: Optional[Callable] = None
# forget_me_callback: Optional[Callable] = None
# set_long_term_memory_callback: Optional[Callable] = None
# get_chat_metadata_callback: Optional[Callable] = None # To get list of chats
# get_current_chat_id_callback: Optional[Callable] = None # To know the active chat
# get_llm_settings_callback: Optional[Callable] = None # To get current LLM settings
# set_llm_setting_callback: Optional[Callable] = None # To update LLM settings
# get_suggestions_callback: Optional[Callable] = None # To get suggested prompts
# process_uploaded_file_callback: Optional[Callable] = None # app.py might handle file processing logic
# remove_uploaded_file_callback: Optional[Callable] = None # app.py might handle file removal logic
# get_uploaded_files_callback: Optional[Callable] = None # To list uploaded files

# --- Helper Functions (adapted from stui.py or new for Chainlit) ---

def ensure_workspace():
    os.makedirs(UI_ACCESSIBLE_WORKSPACE, exist_ok=True)

async def display_chat_messages_from_session():
    """Displays chat messages stored in cl.user_session.get('messages')"""
    messages_to_display = cl.user_session.get("messages", [])
    CODE_DOWNLOAD_MARKER = "---DOWNLOAD_FILE---"
    RAG_SOURCE_MARKER = "---RAG_SOURCE---"

    for msg_data in messages_to_display:
        role = msg_data["role"]
        content = msg_data["content"]
        author = "User" if role == "user" else "ESI"

        elements = []
        text_to_display = content
        rag_sources_data = []
        code_download_filename = None
        code_download_filepath_relative = None
        code_is_image = False

        if role == "assistant":
            # 1. Extract RAG sources
            rag_source_pattern = re.compile(rf"{re.escape(RAG_SOURCE_MARKER)}({{\"type\":.*?}})", re.DOTALL)
            all_rag_matches = list(rag_source_pattern.finditer(text_to_display))
            processed_text_after_rag = text_to_display
            for match in reversed(all_rag_matches):
                json_str = match.group(1)
                try:
                    rag_data = json.loads(json_str)
                    rag_sources_data.append(rag_data)
                except json.JSONDecodeError as e:
                    cl.Warning(f"Could not decode RAG source JSON: {json_str}. Error: {e}").send()
                processed_text_after_rag = processed_text_after_rag[:match.start()] + processed_text_after_rag[match.end():]
            text_to_display = processed_text_after_rag.strip()

            # 2. Extract Code Interpreter download marker
            code_marker_match = re.search(rf"^{re.escape(CODE_DOWNLOAD_MARKER)}(.*)$", text_to_display, re.MULTILINE | re.IGNORECASE)
            if code_marker_match:
                extracted_filename = code_marker_match.group(1).strip()
                text_to_display = text_to_display[:code_marker_match.start()].strip() + text_to_display[code_marker_match.end():].strip()
                code_download_filename = extracted_filename
                code_download_filepath_relative = os.path.join(UI_ACCESSIBLE_WORKSPACE, extracted_filename) # Path relative to project root

                if extracted_filename and os.path.exists(code_download_filepath_relative):
                    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
                    if os.path.splitext(code_download_filename)[1].lower() in image_extensions:
                        code_is_image = True
                else:
                    text_to_display += f"\n\n*(Warning: The file '{extracted_filename}' mentioned for download could not be found at {code_download_filepath_relative}.)*"

            # Create elements for RAG sources and code downloads
            displayed_rag_identifiers = set()
            rag_sources_data.sort(key=lambda x: x.get('citation_number', float('inf')) if x.get('type') == 'pdf' else x.get('url', x.get('title', '')))

            for rag_idx, rag_data in enumerate(rag_sources_data):
                source_type = rag_data.get("type")
                identifier = None

                if source_type == "pdf":
                    pdf_name = rag_data.get("name", "source.pdf")
                    pdf_source_path = rag_data.get("path")
                    citation_num = rag_data.get('citation_number')
                    citation_prefix = f"[{citation_num}] " if citation_num else ""
                    identifier = pdf_source_path

                    if identifier and identifier not in displayed_rag_identifiers:
                        if pdf_source_path and pdf_source_path.startswith("http"):
                            elements.append(cl.Text(content=f"Source: {citation_prefix}[{pdf_name}]({pdf_source_path})", name=pdf_name, display="inline"))
                        elif pdf_source_path and pdf_source_path.startswith("file://"):
                            local_file_path = pdf_source_path[len("file://"):]
                            if os.path.exists(local_file_path):
                                elements.append(cl.File(path=local_file_path, name=f"{citation_prefix}{pdf_name}", display="inline"))
                            else:
                                text_to_display += f"\n*(Warning: Referenced PDF '{pdf_name}' not found locally at '{local_file_path}'.)*"
                        displayed_rag_identifiers.add(identifier)

                elif source_type == "web":
                    url = rag_data.get("url")
                    title = rag_data.get("title", url)
                    identifier = url
                    if identifier and identifier not in displayed_rag_identifiers:
                        if url:
                            elements.append(cl.Text(content=f"Source: [{title}]({url})", name=title, display="inline"))
                        displayed_rag_identifiers.add(identifier)

            # Create element for code interpreter output
            if code_download_filename and os.path.exists(code_download_filepath_relative):
                if code_is_image:
                    elements.append(cl.Image(path=code_download_filepath_relative, name=code_download_filename, display="inline"))
                else:
                    elements.append(cl.File(path=code_download_filepath_relative, name=code_download_filename, display="inline"))

        # Send the message with content and elements
        await cl.Message(content=text_to_display, author=author, elements=elements if elements else None).send()


async def setup_chat_settings_sidebar():
    """Sets up the sidebar with LLM settings, chat history, etc."""
    # This function will be called in on_chat_start
    # It will use cl.ChatSettings and cl.Action to replicate sidebar functionality

    app_state = cl.user_session.get("app_state") # Get app_state from app.py
    if not app_state:
        print("Warning: app_state not found in user_session. UI setup might be incomplete.")
        return

    # LLM Settings
    # These will likely become cl.Slider or cl.NumberInput in a cl.ChatSettings context
    # For now, let's assume app.py initializes these in user_session or provides them
    # llm_settings = app_state.get_llm_settings() # Hypothetical call
    llm_temperature = cl.user_session.get("llm_temperature", 0.7)
    llm_verbosity = cl.user_session.get("llm_verbosity", 3)
    search_results_count = cl.user_session.get("search_results_count", 5)
    long_term_memory_enabled = cl.user_session.get("long_term_memory_enabled", False)

    settings_inputs = [
        cl.Slider(id="llm_temperature", label="Creativity (Temperature)", initial=llm_temperature, min=0.0, max=2.0, step=0.1),
        cl.Slider(id="llm_verbosity", label="Verbosity", initial=llm_verbosity, min=1, max=5, step=1),
        cl.Slider(id="search_results_count", label="Number of Search Results", initial=search_results_count, min=3, max=15, step=1),
        cl.Switch(id="long_term_memory_enabled", label="Enable Long-term Memory", initial=long_term_memory_enabled)
    ]
    cl.user_session.set("settings_inputs", settings_inputs) # Store to retrieve values later

    # Chat History - This is more complex in Chainlit.
    # Chainlit has its own conversation history. We need to bridge app.py's chat management.
    # We might use cl.Action buttons for "New Chat", "Delete Chat", etc.

    actions = [
        cl.Action(name="new_chat", value="new_chat", label="➕ New Chat"),
        # More actions for rename, delete, download will be added.
    ]
    if long_term_memory_enabled:
        actions.append(cl.Action(name="forget_me", value="forget_me", label="🗑️ Forget Me (Delete All Data)"))

    cl.user_session.set("sidebar_actions", actions)

    # File Uploads
    # Chainlit handles file uploads via the UI automatically. We need to process them in on_message or a specific action.
    # We can inform the user about uploaded files.
    # uploaded_files_info = [] # Populate this from app_state.get_uploaded_files_list()
    # cl.user_session.set("uploaded_files_info", uploaded_files_info)


@cl.on_chat_start
async def on_chat_start():
    """
    Called when a new chat session starts.
    Initializes session state, displays welcome message, and sets up UI elements.
    """
    ensure_workspace()
    cl.user_session.set("messages", []) # Initialize messages for this session

    # --- This is where app.py's initialization logic would integrate ---
    # For example, app.py might have a function to call here:
    # app_instance = cl.user_session.get("app_instance") # Assuming app.py sets this
    # if app_instance:
    #     await app_instance.initialize_session_for_chainlit() # This would set up messages, settings, etc.
    # else:
    #     await cl.Message(content="Error: Application backend not initialized correctly.").send()
    #     return

    # For now, simulate some initial state based on stui.py
    # In a real scenario, app.py would populate these via a shared AppState or similar
    cl.user_session.set("llm_temperature", 0.7)
    cl.user_session.set("llm_verbosity", 3)
    cl.user_session.set("search_results_count", 5)
    cl.user_session.set("long_term_memory_enabled", False) # Default, app.py would provide actual
    cl.user_session.set("uploaded_documents", {})
    cl.user_session.set("uploaded_dataframes", {})
    cl.user_session.set("current_chat_id", "default_chat_id") # app.py would provide this


    await cl.Message(
        content="🎓 **ESI: ESI Scholarly Instructor**\nYour AI partner for brainstorming and structuring your dissertation research.",
        author="System"
    ).send()

    # Setup sidebar-like elements using cl.ChatSettings and Actions
    # This part is tricky as Chainlit's UI flow is different from Streamlit's sidebar.
    # We might present these as initial actions or use a settings modal.

    # For now, let's put settings directly in the user session.
    # User will need to be informed how to change them (e.g., via a command or future UI element)

    # Display existing messages if any (e.g., if app.py loads a previous session)
    await display_chat_messages_from_session()

    # Suggested Prompts (if any)
    # suggested_prompts = app_instance.get_suggested_prompts() # Hypothetical
    suggested_prompts = ["Help me define my research question.", "Suggest some relevant theories.", "How do I structure my literature review?"]
    if suggested_prompts:
        actions = [cl.नास(name=prompt, value=prompt, label=prompt) for prompt in suggested_prompts]
        await cl.Message(content="Here are some things you can ask:", actions=actions).send()

    # File uploader - Chainlit handles this automatically if `ask_for_file` is used or files are attached.
    # We need to inform the user how to upload.
    await cl.Message(content="You can upload files by attaching them to your message or using the upload button.").send()

    # Set up actions that would normally be in the sidebar
    await setup_actions_and_settings()


async def setup_actions_and_settings():
    """Sets up persistent actions and settings UI elements."""
    app_state = cl.user_session.get("app_state") # Assuming app.py provides this

    actions = [
        cl.Action(name="new_chat", value="new_chat", label="➕ New Chat", description="Start a new conversation"),
        # Potentially add "Manage Chats" that opens a modal or lists chats
    ]

    # LLM Settings - using cl.ChatSettings for a modal-like experience
    # These settings are more naturally handled via a settings modal in Chainlit.
    # For now, we'll rely on app.py to manage these and potentially make them settable via commands.

    if app_state and app_state.get_long_term_memory_enabled(): # Hypothetical
        actions.append(cl.Action(name="forget_me", value="forget_me", label="🗑️ Forget Me", description="Delete all your saved data"))

    # Display chat history if LTM enabled (this is complex with Chainlit's model)
    # chat_metadata = app_state.get_chat_metadata() # Hypothetical
    # if chat_metadata:
    #     for chat_id, chat_name in chat_metadata.items():
    #         actions.append(cl.Action(name=f"switch_chat_{chat_id}", value=chat_id, label=f"Switch to: {chat_name}"))

    cl.user_session.set("main_actions", actions) # Store for display or use in UI elements


@cl.on_settings_update
async def on_settings_update(settings):
    """Called when chat settings are updated by the user."""
    # This is where we'd handle changes from cl.ChatSettings if we implement them fully.
    # For now, this is a placeholder.
    # app_instance = cl.user_session.get("app_instance")
    # if app_instance:
    #     if "llm_temperature" in settings:
    #         app_instance.set_llm_setting("temperature", settings["llm_temperature"])
    #     if "llm_verbosity" in settings:
    #         app_instance.set_llm_setting("verbosity", settings["llm_verbosity"])
    #     # etc.
    #     await cl.Message(content="Settings updated!").send()
    print(f"Settings updated by user: {settings}")
    # Update user_session based on incoming settings
    for key, value in settings.items():
        cl.user_session.set(key, value)
        # Potentially call a callback to app.py to persist this setting
        # set_llm_setting_callback(key, value) # Example
    await cl.Message(content="Settings have been updated.").send()


@cl.on_message
async def on_message(message: cl.Message):
    """
    Called when the user sends a message or uploads a file.
    """
    app_instance = cl.user_session.get("app_instance") # Critical: app.py must set this

    # Store user message
    cl.user_session.get("messages").append({"role": "user", "content": message.content})

    # --- File Upload Handling ---
    # Chainlit automatically makes uploaded files available in message.elements
    # of type cl.LocalFile or similar. We need to process these.
    # This replaces the Streamlit file uploader logic.

    processed_files_info = []
    if message.elements:
        for element in message.elements:
            if isinstance(element, cl.File): # Check if it's a cl.File (Chainlit >= 1.0)
                file_path = element.path # Path to the temporary local copy of the uploaded file
                file_name = element.name
                file_content = element.content # Bytes content

                # Save to UI_ACCESSIBLE_WORKSPACE
                ensure_workspace()
                workspace_file_path = os.path.join(UI_ACCESSIBLE_WORKSPACE, file_name)
                with open(workspace_file_path, "wb") as f:
                    f.write(file_content)

                # Now, process the file content for agent access (similar to stui.py)
                # This logic should ideally be in app.py or a shared module
                # For now, replicating parts of process_uploaded_file from stui.py
                file_extension = os.path.splitext(file_name)[1].lower()

                # --- ADDED: Warning for research data files (from stui.py) ---
                data_file_extensions = [".csv", ".xlsx", ".sav", ".rdata", ".rds"]
                if file_extension in data_file_extensions:
                    await cl.Message(
                        content="**Important:** If this file contains research data, please ensure you have "
                        "obtained all necessary ethical approvals for its use and upload. "
                        "Do not upload sensitive or confidential data without proper authorization.",
                        author="System"
                    ).send()
                # --- END ADDED SECTION ---

                if file_extension in [".pdf", ".docx", ".md", ".txt"]:
                    text_content = ""
                    try:
                        if file_extension == ".pdf":
                            reader = PdfReader(io.BytesIO(file_content))
                            for page in reader.pages:
                                text_content += page.extract_text() or ""
                        elif file_extension == ".docx":
                            document = Document(io.BytesIO(file_content))
                            for para in document.paragraphs:
                                text_content += para.text + "\n"
                        elif file_extension in [".md", ".txt"]:
                            text_content = file_content.decode("utf-8")

                        cl.user_session.get("uploaded_documents")[file_name] = text_content
                        processed_files_info.append(f"Document '{file_name}' processed for agent access. You can now ask me to `read_uploaded_document('{file_name}')`.")
                    except Exception as e:
                        await cl.Message(content=f"Error processing document '{file_name}': {e}", author="System").send()

                elif file_extension in [".csv", ".xlsx", ".sav"]:
                    df = None
                    try:
                        if file_extension == ".csv":
                            df = pd.read_csv(io.BytesIO(file_content))
                        elif file_extension == ".xlsx":
                            df = pd.read_excel(io.BytesIO(file_content))
                        elif file_extension == ".sav":
                            # For .sav, pandas needs a file path. We saved it to workspace.
                            df = pd.read_spss(workspace_file_path) # Requires pyreadstat

                        if df is not None:
                            cl.user_session.get("uploaded_dataframes")[file_name] = df # Storing actual DataFrame might be memory intensive. Consider storing path.
                            processed_files_info.append(f"Dataset '{file_name}' processed. You can now ask me to `analyze_uploaded_dataframe('{file_name}')` or use `code_interpreter`.")
                        else:
                            await cl.Message(content=f"Could not load dataframe from '{file_name}'.", author="System").send()
                    except ImportError:
                         await cl.Message(content="`pyreadstat` library not found. Please install it (`pip install pyreadstat`) to read .sav files.", author="System").send()
                    except Exception as e:
                        await cl.Message(content=f"Error processing dataset '{file_name}': {e}", author="System").send()

                elif file_extension in [".rdata", ".rds"]:
                    await cl.Message(content=f"File type '{file_extension}' for '{file_name}' is not directly supported for Python processing. Please convert it to CSV or XLSX.", author="System").send()
                else:
                    await cl.Message(content=f"Unsupported file type: {file_extension} for '{file_name}'. File saved to workspace at {workspace_file_path} but not processed for agent tools.", author="System").send()

    if processed_files_info:
        for info_msg in processed_files_info:
            await cl.Message(content=info_msg, author="Assistant").send()
            cl.user_session.get("messages").append({"role": "assistant", "content": info_msg})


    # --- Call the main input handler from app.py ---
    # This is where the core logic of the app (agent interaction) happens.
    # The `handle_user_input_callback` from app.py should be invoked here.
    # It will return the assistant's response.

    # response_content = await app_instance.handle_user_input(message.content) # Hypothetical

    # For now, simulate a response:
    # Simulating response generation
    # In reality, this comes from handle_user_input_callback(message.content)
    if not app_instance or not hasattr(app_instance, 'handle_user_input'):
        simulated_response = "App instance or handle_user_input not configured. Cannot process message."
        await cl.Message(content=simulated_response, author="System").send()
        return

    # Construct the full context for the handler, similar to how Streamlit app would
    # This includes current settings, uploaded files info etc.
    # The handler in app.py will need to be adapted to get this from user_session

    # Before calling handler, make sure app_instance knows about current settings from user_session
    # app_instance.update_settings_from_chainlit_session(cl.user_session) # Hypothetical

    assistant_response_content = await app_instance.handle_user_input(message.content)

    # Store assistant response
    cl.user_session.get("messages").append({"role": "assistant", "content": assistant_response_content})

    # Display assistant response (potentially with elements for files/RAG)
    # This will be more complex if the response contains markers for files, RAG, etc.
    # We need to parse `assistant_response_content` like in `display_chat` from stui.py

    # For now, a simple display. We'll enhance this to match stui.py's display_chat logic.
    # await cl.Message(content=assistant_response_content, author="Assistant").send()

    # Instead of simple send, use the display logic to handle RAG, files etc.
    # For this, we need to ensure the last message (the one we just got) is included
    # in what display_chat_messages_from_session processes.
    # However, display_chat_messages_from_session iterates all. We need to send just the new one.

    # Let's adapt parts of display_chat_messages_from_session for a single message
    msg_data = {"role": "assistant", "content": assistant_response_content}

    elements = []
    text_to_display = msg_data["content"]
    rag_sources_data = []
    code_download_filename = None
    code_download_filepath_relative = None # Relative to project root
    code_is_image = False
    CODE_DOWNLOAD_MARKER = "---DOWNLOAD_FILE---" # Ensure this is defined
    RAG_SOURCE_MARKER = "---RAG_SOURCE---" # Ensure this is defined

    # 1. Extract RAG sources
    rag_source_pattern = re.compile(rf"{re.escape(RAG_SOURCE_MARKER)}({{\"type\":.*?}})", re.DOTALL)
    all_rag_matches = list(rag_source_pattern.finditer(text_to_display))
    processed_text_after_rag = text_to_display
    for match in reversed(all_rag_matches):
        json_str = match.group(1)
        try:
            rag_data = json.loads(json_str)
            rag_sources_data.append(rag_data)
        except json.JSONDecodeError as e:
            print(f"Warning: Could not decode RAG source JSON: '{json_str}'. Error: {e}")
        processed_text_after_rag = processed_text_after_rag[:match.start()] + processed_text_after_rag[match.end():]
    text_to_display = processed_text_after_rag.strip()

    # 2. Extract Code Interpreter download marker
    code_marker_match = re.search(rf"^{re.escape(CODE_DOWNLOAD_MARKER)}(.*)$", text_to_display, re.MULTILINE | re.IGNORECASE)
    if code_marker_match:
        extracted_filename = code_marker_match.group(1).strip()
        text_to_display = text_to_display[:code_marker_match.start()].strip() + text_to_display[code_marker_match.end():].strip()
        code_download_filename = extracted_filename
        # Ensure UI_ACCESSIBLE_WORKSPACE is defined and accessible
        code_download_filepath_relative = os.path.join(UI_ACCESSIBLE_WORKSPACE, extracted_filename)

        if extracted_filename and os.path.exists(code_download_filepath_relative):
            image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
            if os.path.splitext(code_download_filename)[1].lower() in image_extensions:
                code_is_image = True
        else:
            text_to_display += f"\n\n*(Warning: The file '{extracted_filename}' mentioned for download could not be found at '{code_download_filepath_relative}'.)*"

    # Create elements for RAG sources and code downloads
    displayed_rag_identifiers = set()
    rag_sources_data.sort(key=lambda x: x.get('citation_number', float('inf')) if x.get('type') == 'pdf' else x.get('url', x.get('title', '')))

    for rag_idx, rag_data in enumerate(rag_sources_data):
        source_type = rag_data.get("type")
        identifier = None

        if source_type == "pdf":
            pdf_name = rag_data.get("name", "source.pdf")
            pdf_source_path = rag_data.get("path") # http:// or file://
            citation_num = rag_data.get('citation_number')
            citation_prefix = f"[{citation_num}] " if citation_num else ""
            identifier = pdf_source_path

            if identifier and identifier not in displayed_rag_identifiers:
                if pdf_source_path and pdf_source_path.startswith("http"):
                    elements.append(cl.Text(content=f"Source: {citation_prefix}[{pdf_name}]({pdf_source_path})", name=pdf_name, display="inline"))
                elif pdf_source_path and pdf_source_path.startswith("file://"):
                    local_file_path = pdf_source_path[len("file://"):]
                    if os.path.exists(local_file_path):
                        elements.append(cl.File(path=local_file_path, name=f"{citation_prefix}{pdf_name}", display="inline"))
                    else:
                         text_to_display += f"\n*(Warning: Referenced PDF '{pdf_name}' not found locally at '{local_file_path}'.)*"
                displayed_rag_identifiers.add(identifier)

        elif source_type == "web":
            url = rag_data.get("url")
            title = rag_data.get("title", url)
            identifier = url
            if identifier and identifier not in displayed_rag_identifiers:
                if url:
                    elements.append(cl.Text(content=f"Source: [{title}]({url})", name=title, display="inline"))
                displayed_rag_identifiers.add(identifier)

    if code_download_filename and os.path.exists(code_download_filepath_relative):
        if code_is_image:
            elements.append(cl.Image(path=code_download_filepath_relative, name=code_download_filename, display="inline"))
        else:
            elements.append(cl.File(path=code_download_filepath_relative, name=code_download_filename, display="inline"))

    await cl.Message(content=text_to_display if text_to_display else " ", author="Assistant", elements=elements if elements else None).send()


@cl.action_callback("new_chat")
async def on_new_chat(action: cl.Action):
    # app_instance = cl.user_session.get("app_instance")
    # if app_instance and hasattr(app_instance, 'new_chat_session'):
    #     await app_instance.new_chat_session() # This should reset state in app.py and user_session
    #     await cl.Message(content="Started a new chat session.").send()
    #     # Need to re-trigger on_chat_start or a similar re-initialization for the UI
    #     # This is a bit tricky in Chainlit, might need to refresh or guide user
    # else:
    #     await cl.ErrorMessage(content="Could not start new chat: App not configured.").send()
    # For now, just clear messages and re-run on_chat_start logic
    cl.user_session.set("messages", [])
    # Call app.py's new_chat_callback here if it exists and is set
    # new_chat_callback()
    await on_chat_start() # This will effectively reset the chat display
    await cl.Message(content="New chat started. Previous messages cleared from this view.").send()
    return "New chat started." # Optional return for action


@cl.action_callback("forget_me")
async def on_forget_me(action: cl.Action):
    # app_instance = cl.user_session.get("app_instance")
    # if app_instance and hasattr(app_instance, 'forget_me'):
    #     await app_instance.forget_me() # This should clear server-side data and cookies
    #     await cl.Message(content="All your data has been deleted. You may need to refresh the page.").send()
    # else:
    #     await cl.ErrorMessage(content="Could not forget user: App not configured.").send()
    # Call app.py's forget_me_callback here
    # forget_me_callback()
    # This action in Chainlit typically means clearing user_session and potentially browser storage.
    # Chainlit itself doesn't manage cross-session user identity beyond user_session without custom auth.
    # The "forget_me" needs to be implemented in app.py to clear any cookies or server-side storage.
    await cl.Message(content="Forget me functionality needs to be fully implemented in `app.py` (clearing cookies, server-side data). For now, this is a placeholder.").send()
    return "Forget me clicked."

# --- TODO ---
# - Implement remaining actions: rename_chat, delete_chat, download_chat (md, docx)
#   These will require callbacks to app.py and careful state management.
#   Downloads can be done using cl.FileElement.
# - Implement display of chat history list and switching chats. This is complex
#   as Chainlit's model is one chat per session. May need a "dashboard" or modal.
# - Full integration with app.py:
#   - app.py needs to initialize an AppState/AppInstance and put it in cl.user_session.
#   - All callbacks (handle_user_input, settings changes, chat management) need to be
#     called on this AppState/AppInstance.
#   - app.py needs to adapt its logic to work with cl.user_session for state.
# - Error handling and robustness.
# - UI styling and layout to better match the original Streamlit app's feel if desired.
# - Clipboard and Regenerate functionality for messages.
#   - Clipboard: Chainlit has built-in copy for messages.
#   - Regenerate: Would require storing the last user message and re-sending to handler.
#     Add an action to the assistant's message for regeneration.

# This is a foundational ui.py. Full feature parity requires more detailed implementation
# of actions, settings UI, and deep integration with app.py's state management.
print("ui.py loaded. Chainlit UI definitions are ready.")

# It's important that app.py imports this module so Chainlit can discover the decorators.
# And app.py needs to set the `app_instance` in `cl.user_session` at the beginning of `on_chat_start`
# or via a middleware.

# Example of how app.py might set the instance (conceptual)
# @cl.oauth_callback # or some other early hook
# async def auth_callback(user: cl.User): # if using auth
#   app_instance = await initialize_my_app_logic_for_user(user)
#   cl.user_session.set("app_instance", app_instance)
#   return True

# Or, more simply, if no user-specific logic at that stage:
# In app.py, before starting Chainlit server, create a global AppState factory or instance.
# Then in on_chat_start:
#   if not cl.user_session.get("app_instance"):
#       app_logic = AppLogicHandler(user_session=cl.user_session) # Pass session for state
#       cl.user_session.set("app_instance", app_logic)
#       await app_logic.on_session_init() # Let the app logic initialize itself

# The key challenge is bridging Chainlit's stateless-per-request (within a session) model
# with an application that might have more complex state managed in Python objects.
# cl.user_session is the primary vehicle for this.

""" Entrypoint for chatbot UI. """
import os
import sys
import uuid
from typing import Dict, List
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

import streamlit as st
from babel import Locale
from botocore.exceptions import ClientError
from chatbot.catalog import (
    MemoryCatalog,
    MemoryCatalogItem,
    PromptCatalog,
    PromptCatalogItem,
)
from chatbot.config import (
    AmazonBedrock,
    AmazonBedrockParameters,
    AppConfigProvider,
    AWSConfig,
    AWSRegion,
)
from chatbot.helpers import (
    ChatbotEnvironment,
    ChatbotEnvironmentVariables,
    get_current_account_id,
    is_url,
)
from chatbot.helpers.logger.app_logging import (
    get_llm_log_handler,
    get_llm_logger,
    get_technical_logger,
)
from chatbot.helpers.logger.log_to_ui_handler import LogToUiHandler
from chatbot.i18n import install_language
from langchain.memory import StreamlitChatMessageHistory
from langchain.schema import BaseChatMessageHistory

from .about_page import about_page
from .auth import check_password
from .chat_messages import (
    ChatHistory,
    ChatMessage,
    ChatParticipant,
    DebugMessage,
    InfoMessage,
)
from .sidebar import write_sidebar
from .topbar import write_top_bar, write_prompt_hints
from .stream_handler import StreamHandler

import yaml

def create_session_id() -> str:
    """Create a session id.

    Returns:
        a new session id.
    """
    return str(uuid.uuid4())


def write_chatbot(base_dir: str, environment: ChatbotEnvironment):
    """Composes and displays the UI for the chatbot.

    Args:
        base_dir: the base directory of the chatbot
            from which it resolves relative imports such as images.
        environment: the environment variables for the chatbot.
    """

    if "session_id" not in st.session_state:
        st.session_state["session_id"] = create_session_id()
    session_id = st.session_state["session_id"]

    language = Locale.parse("en_US")
    gettext = install_language(str(language))
    _ = gettext

    if "app_config" not in st.session_state:
        aws_app_config_app_name = environment.get_env_variable(
            ChatbotEnvironmentVariables.AWSAppConfigApplication
        )
        aws_app_config_env_name = environment.get_env_variable(
            ChatbotEnvironmentVariables.AWSAppConfigEnvironment
        )
        aws_app_config_profile_name = environment.get_env_variable(
            ChatbotEnvironmentVariables.AWSAppConfigProfile
        )
        st.session_state["app_config"] = AppConfigProvider(
            aws_app_config_app_name,
            aws_app_config_env_name,
            aws_app_config_profile_name,
        )
    app_config: AppConfigProvider = st.session_state["app_config"]

    if "textract_s3_bucket" not in st.session_state:
        textract_s3_bucket = environment.get_env_variable(
            ChatbotEnvironmentVariables.AmazonTextractS3Bucket
        )
        print(f"textract_s3_bucket: {textract_s3_bucket}")
        st.session_state["textract_s3_bucket"] = textract_s3_bucket

    chatbot_name = app_config.config.appearance.parameters.name
    favicon_url = app_config.config.appearance.parameters.favicon_url

    if not is_url(favicon_url):
        favicon_url = os.path.join(base_dir, favicon_url)

    about_page(chatbot_name, favicon_url, gettext)

    if not check_password(chatbot_name):
        # need to login first
        st.stop()

    chat_history = ChatHistory(chatbot_name, gettext)

    if "show_llm_debug_messages" in st.session_state:
        show_llm_debug_messages = st.session_state["show_llm_debug_messages"]
    else:
        show_llm_debug_messages = False
        st.session_state["show_llm_debug_messages"] = show_llm_debug_messages

    def on_llm_log(log_message: str):
        if st.session_state["show_llm_debug_messages"]:
            chat_history.add_chat_message(
                DebugMessage(ChatParticipant.DEBUGGER, log_message)
            )

    def on_technical_log(log_message: str):
        chat_history.add_log_message(InfoMessage(ChatParticipant.DEBUGGER, log_message))

    # Logging
    if "TECHNICAL_LOGGER" in st.session_state:
        logger = st.session_state["TECHNICAL_LOGGER"]
    else:
        logger = get_technical_logger(
            ui_handler=LogToUiHandler(on_technical_log), session_id=session_id
        )
        st.session_state["TECHNICAL_LOGGER"] = logger

    if "LLM_LOGGER" in st.session_state:
        llm_logger = st.session_state["LLM_LOGGER"]
    else:
        llm_logger = get_llm_logger(
            ui_handler=LogToUiHandler(on_llm_log), session_id=session_id
        )
        st.session_state["LLM_LOGGER"] = llm_logger

    if "LLM_LOG_HANDLER" in st.session_state:
        llm_log_handler = st.session_state["LLM_LOG_HANDLER"]
    else:
        llm_log_handler = get_llm_log_handler(llm_logger)
        st.session_state["LLM_LOG_HANDLER"] = llm_log_handler

    if "aws_config" not in st.session_state:
        try:
            account_id = get_current_account_id()
            region = environment.get_env_variable(ChatbotEnvironmentVariables.AWSRegion)
            logger.info("AWS account number: %s", account_id)
            logger.info(f"AWS region: {region}")
            st.session_state["aws_config"] = AWSConfig(
                account_id=account_id, region=region
            )
            bedrock_region = environment.get_env_variable(
                ChatbotEnvironmentVariables.AmazonBedrockRegion
            )
            if bedrock_region:
                app_config.config.add_amazon_bedrock(bedrock_region)

        except Exception:
            logger.error(
                "Unable to get AWS account number. Ensure that you have AWS credentials configured."
            )
            sys.exit(0)

    logger.info("Session ID: %s", session_id)

    aws_config: AWSConfig = st.session_state["aws_config"]

    regions = [aws_config.region]

    # Refresh button callback
    def refresh(memory: BaseChatMessageHistory):
        session_id = create_session_id()
        st.session_state.session_id = session_id
        chat_history.clear()

        # Clear Streamlit local memory cache
        if memory and type(memory) is StreamlitChatMessageHistory:
            memory.clear()    

    if "memory_catalog" not in st.session_state:
        memory_catalog = MemoryCatalog(
            account_id=aws_config.account_id, regions=regions, logger=logger
        )
        st.session_state["memory_catalog"] = memory_catalog
        memory_catalog.bootstrap()

    memory_catalog: List[MemoryCatalogItem] = st.session_state["memory_catalog"]
    
    memory_item = next(iter(memory_catalog or []), None)
    memory = (
        StreamlitChatMessageHistory()
        if memory_item is None
        else memory_item.get_instance(session_id)
    )
    write_top_bar(session_id=session_id, on_refresh=lambda:refresh(memory), gettext=gettext)

    # Layout of input/response containers
    response_container = st.empty()

    def on_llm_response(text: str):
        #response_container.empty()
        stream_msg = ChatMessage(ChatParticipant.BOT, text)
        #chat_history.append_to_previous_message(stream_msg)
        with response_container.container():
            chat_history.write()
            with st.chat_message(stream_msg.sender.value, avatar=stream_msg.avatar):
                stream_msg.write()
            

    llm_callbacks = [
        StreamHandler(callback=on_llm_response)
    ]
    _sidebar = write_sidebar(
        chatbot_name,
        favicon_url,
        regions,
        gettext=gettext,
        aws_config=aws_config,
        logger=logger,
        llm_callbacks=llm_callbacks,
        show_llm_debug_messages=show_llm_debug_messages,
        app_config=app_config.config,
    )

    if "prompt_catalog" not in st.session_state:
        st.session_state["prompt_catalog"] = PromptCatalog()
    prompt_catalog: Dict[PromptCatalogItem] = st.session_state["prompt_catalog"]

    if _sidebar.flow_or_retriever_or_model_or_agent_changed:
        chat_history.add_chat_message(
            chat_history.create_system_message(_sidebar.model, _sidebar.retriever, _sidebar.flow)
        )
    
    empty_input_text = _("Ask a question or prompt the LLM")
    prompt = st.chat_input(empty_input_text)

    # Showing hints buttons
    button_prompt = write_prompt_hints(_sidebar)
    if button_prompt:
        refresh(memory)
        prompt = button_prompt

    with response_container.container():
        chat_history.write()

    
    ## Conditional display of AI generated responses as a function of user provided prompts
    if prompt:
        app = _sidebar.flow.llm_app_factory(
            _sidebar.model,
            _sidebar.retriever,
            _sidebar.agents_chains,
            prompt_catalog,
            _sidebar.sql_connection_uri,
            _sidebar.sql_model
        )
        # Required for retriver validations, it will stop and show retriever error
        if not app:
            return


        # add the content of an uploaded file content, if available
        prompt = _sidebar.uploaded_file_content + "\n" + prompt

        prompt_msg = ChatMessage(ChatParticipant.USER, prompt)
        chat_history.add_chat_message(prompt_msg)
        
        response = app.generate_response(
            prompt, memory, callbacks=[llm_log_handler, 
                                    #    StreamingStdOutCallbackHandler(),
                                    #    StreamHandler(response_container)
                                        ]
        )
        chat_history.add_chat_message(ChatMessage(ChatParticipant.BOT, response))

        # Adding graph data and fixing no document search option
        if hasattr(app, 'retriever') and hasattr(app.retriever, 'graphs'):
            for _, graph_data in app.retriever.graphs.items():
                chat_history.add_plot(graph_data)
    
    with response_container.container():
        chat_history.write()

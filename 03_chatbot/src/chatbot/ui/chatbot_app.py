""" Entrypoint for chatbot UI. """
import os
import sys
import uuid
from typing import Dict, List

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
from .topbar import write_top_bar


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

    retriever, model, retriever_or_model_changed = write_sidebar(
        chatbot_name,
        favicon_url,
        regions,
        gettext=gettext,
        aws_config=aws_config,
        logger=logger,
        show_llm_debug_messages=show_llm_debug_messages,
        app_config=app_config.config,
    )

    if "prompt_catalog" not in st.session_state:
        st.session_state["prompt_catalog"] = PromptCatalog()
    prompt_catalog: Dict[PromptCatalogItem] = st.session_state["prompt_catalog"]

    if "memory_catalog" not in st.session_state:
        memory_catalog = MemoryCatalog(
            account_id=aws_config.account_id, regions=regions, logger=logger
        )
        st.session_state["memory_catalog"] = memory_catalog
        memory_catalog.bootstrap()
    memory_catalog: List[MemoryCatalogItem] = st.session_state["memory_catalog"]

    # Refresh button callback
    def refresh():
        session_id = create_session_id()
        st.session_state.session_id = session_id
        chat_history.clear()

    write_top_bar(session_id=session_id, on_refresh=refresh, gettext=gettext)

    if retriever_or_model_changed:
        chat_history.add_chat_message(
            chat_history.create_system_message(model, retriever)
        )

    # Layout of input/response containers
    response_container = st.container()
    empty_input_text = _("Ask a question or prompt the LLM")
    prompt = st.chat_input(empty_input_text)

    ## Conditional display of AI generated responses as a function of user provided prompts
    with response_container:
        if prompt:
            memory_item = next(iter(memory_catalog or []), None)
            memory = (
                StreamlitChatMessageHistory()
                if memory_item is None
                else memory_item.get_instance(session_id)
            )

            app = retriever.llm_app_factory(model, prompt_catalog)

            chat_history.add_chat_message(ChatMessage(ChatParticipant.USER, prompt))
            response = app.generate_response(
                prompt, memory, callbacks=[llm_log_handler]
            )
            chat_history.add_chat_message(ChatMessage(ChatParticipant.BOT, response))

        chat_history.write()

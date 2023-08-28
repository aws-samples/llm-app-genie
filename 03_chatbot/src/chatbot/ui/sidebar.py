""" Chatbot UI side panel. """
from io import BytesIO
from typing import Callable, Generic, List, Tuple, TypeVar, Union

import streamlit as st
from chatbot.catalog import (
    ModelCatalog,
    ModelCatalogItem,
    RetrieverCatalog,
    RetrieverCatalogItem,
)
from chatbot.config import AppConfig
from numpy import ndarray
from streamlit.type_util import OptionSequence, T


def write_sidebar(
    chatbot_name: str,
    app_icon: Union[ndarray, List[ndarray], BytesIO, str, List[str]],
    regions: List[str],
    app_config: AppConfig,
    show_llm_debug_messages: bool = False,
    gettext: Callable[[str], str] = lambda x: x,
) -> Tuple[RetrieverCatalogItem, ModelCatalogItem, bool]:
    """
    Functional UI component that renders the sidebar.

    Args:
        chatbot_name: Name of the chatbot.
        app_icon: Icon to be displayed in the sidebar.
        regions: List of AWS regions that the chatbot should rely on.
        show_llm_debug_messages: Whether to show debug messages for LLM.
        gettext: Translation function.

    Side effects:
        Sets the session state for the retriever and model catalogs.


    Returns:
        Tuple containing currently selected retriever,
        currently selected model,
        and whether the retriever or model changes since the last render.
    """
    _ = gettext

    def __render_dropdown(
        label: str, selected_state_name: str, options: OptionSequence[T]
    ) -> Tuple[T, bool]:
        selected = st.selectbox(label=label, options=options, index=0)

        changed = False
        if selected_state_name not in st.session_state:
            st.session_state[selected_state_name] = selected
        else:
            previous_selected = st.session_state[selected_state_name]
            if selected != previous_selected:
                st.session_state[selected_state_name] = selected
                changed = True
        return selected, changed

    with st.sidebar:
        col1, col2 = st.columns([1, 5])
        with col1:
            st.image(app_icon, use_column_width="always")
        with col2:
            st.title(chatbot_name)

        retriever_state_name = "retriever_catalog"
        if retriever_state_name not in st.session_state:
            st.session_state[retriever_state_name] = RetrieverCatalog(regions)
        retriever_options = st.session_state[retriever_state_name]
        knowledgebase_label = _("Knowledge Base")
        retriever, retriever_changed = __render_dropdown(
            knowledgebase_label, "retriever", retriever_options
        )

        filter_options = retriever.available_filter_options
        current_filter_options = retriever.current_filter

        options = st.multiselect(
            _("Optional: Filter {knowledge_base_name}").format(
                knowledge_base_name=retriever.friendly_name
            ),
            filter_options if filter_options is not None else [],
            disabled=filter_options is None,
            default=current_filter_options,
            placeholder=_("Full search. Choose a filter."),
            format_func=lambda x: x[0],
        )

        retriever.current_filter = options

        model_state_name = "model_catalog"
        if model_state_name not in st.session_state:
            st.session_state[model_state_name] = ModelCatalog(
                regions, bedrock_config=app_config.amazon_bedrock or []
            )
        model_options = st.session_state[model_state_name]
        language_model_label = _("Language Model")
        model, model_changed = __render_dropdown(
            language_model_label, "model", model_options
        )

        st.checkbox(
            label=_("Language Model X-Ray ") + "🩻",
            value=show_llm_debug_messages,
            key="show_llm_debug_messages",
        )

        return retriever, model, retriever_changed | model_changed

""" Chatbot UI side panel. """
from io import BytesIO
from logging import Logger
from typing import Callable, Generic, List, Tuple, TypeVar, Union

from io import StringIO
import streamlit as st
from chatbot.catalog import (
    ModelCatalog,
    ModelCatalogItem,
    RetrieverCatalog,
    RetrieverCatalogItem,
    FlowCatalog,
    FlowCatalogItem,
)
from chatbot.config import AppConfig, AWSConfig
from numpy import ndarray
from streamlit.type_util import OptionSequence, T


class SidebarObj():
    def init(self):
        self.flow = None
        self.retriever = None
        self.model = None
        self.flow_or_retriever_or_model_changed = False
        self.uploaded_file_content = ""


def write_sidebar(
        chatbot_name: str,
        app_icon: Union[ndarray, List[ndarray], BytesIO, str, List[str]],
        regions: List[str],
        app_config: AppConfig,
        aws_config: AWSConfig,
        logger: Logger,
        show_llm_debug_messages: bool = False,
        gettext: Callable[[str], str] = lambda x: x,
    ) -> Tuple[FlowCatalogItem, RetrieverCatalogItem, ModelCatalogItem, bool]:
    """
    Functional UI component that renders the sidebar.

    Args:
        chatbot_name: Name of the chatbot.
        app_icon: Icon to be displayed in the sidebar.
        regions: List of AWS regions that the chatbot should rely on.
        logger: logging
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
        label: str, selected_state_name: str, options: OptionSequence[T], params
    ) -> Tuple[T, bool]:
        # print("__render_dropdown",label,selected_state_name,options,params)
        default_index = 0
        if selected_state_name in params and len(params[selected_state_name]) > 0:
            option_names = [str(option) for option in options]
            filtered_names = list(set(option_names) & set(params[selected_state_name]))
            options = [option for option in options if str(option) in filtered_names]

        selected = st.selectbox(label=label, options=options, index=default_index)

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

        params = st.experimental_get_query_params()

        _sidebar = SidebarObj()

        ########### FLOW STUFF ###############
        flow_state_name = "flow_catalog"
        if flow_state_name not in st.session_state:
            flow_catalog = FlowCatalog(
                aws_config.account_id, 
                regions, 
                logger
                )
            st.session_state[flow_state_name] = flow_catalog
            flow_catalog.bootstrap()

        flow_options = st.session_state[flow_state_name]
        flow_label = _("Flow")
        flow, flow_changed = __render_dropdown(
            flow_label, "flow", flow_options, params
            )
        
        enable_file_upload = flow.enable_file_upload()
        # print("\nflow:",flow,"\n","enable_file_upload:",enable_file_upload)

        # upload file button
        uploaded_file_content = ""
        if enable_file_upload:
            uploaded_file = st.sidebar.file_uploader(
                                "Upload a file", 
                                type=["txt", "json"], 
                                key=flow_options,
                                # disabled=not enable_file_upload
                                )
            if uploaded_file is not None:
                stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
                uploaded_file_content = "=== BEGIN FILE ===\n"
                uploaded_file_content += stringio.read()
                uploaded_file_content += "\n=== END FILE ===\n"
        
        ########### RETRIEVER STUFF ###############
        retriever = None
        retriever_changed = False
        if flow.enable_retriever:
            retriever_state_name = "retriever_catalog"
            if retriever_state_name not in st.session_state:
                retriever_catalog = RetrieverCatalog(
                    aws_config.account_id, 
                    regions, 
                    logger
                    )
                st.session_state[retriever_state_name] = retriever_catalog
                retriever_catalog.bootstrap()

            retriever_options = st.session_state[retriever_state_name]
            knowledgebase_label = _("Knowledge Base")
            retriever, retriever_changed = __render_dropdown(
                knowledgebase_label, "retriever", retriever_options, params
                )

            # print("\nretriever:",retriever,"\n")
            filter_options = retriever.available_filter_options
            current_filter_options = retriever.current_filter

            filter_disabled = filter_options is None

            filter_options = [] if filter_options is None else filter_options

            filter_query_param_name = "filter"
            if (
                filter_query_param_name in params
                and len(params[filter_query_param_name]) > 0
                ):
                option_names = [option[0] for option in filter_options]
                filtered_names = list(
                    set(option_names) & set(params[filter_query_param_name])
                    )
                filter_options = [
                    option for option in filter_options if option[0] in filtered_names
                    ]

            options = st.multiselect(
                _("Optional: Filter {knowledge_base_name}").format(
                    knowledge_base_name=retriever.friendly_name
                ),
                filter_options,
                disabled=filter_disabled,
                default=current_filter_options,
                placeholder=_("Full search. Choose a filter."),
                format_func=lambda x: x[0],
                )

            retriever.current_filter = options

        ########### MODEL STUFF ###############
        model_state_name = "model_catalog"
        if model_state_name not in st.session_state:
            model_catalog = ModelCatalog(
                regions,
                bedrock_config=app_config.amazon_bedrock or [],
                logger=logger,
                llm_config=app_config.llm_config.parameters,
            )
            st.session_state[model_state_name] = model_catalog
            model_catalog.bootstrap()
        model_options = st.session_state[model_state_name]
        language_model_label = _("Language Model")
        model, model_changed = __render_dropdown(
            language_model_label, "model", model_options, params
            )
        # print("model.model_kwargs before", model.model_kwargs)

        st.checkbox(
            label=_("Language Model X-Ray ") + "🩻",
            value=show_llm_debug_messages,
            key="show_llm_debug_messages",
            )

        with st.expander('Change model parameters'):
            temperature = st.slider("Temperature",
                                    min_value=0.0,
                                    max_value=1.0,
                                    value=float(model.model_kwargs["temperature"]),
                                    step=0.1
                                    )
            model.model_kwargs["temperature"] = temperature
        
        # dump variables into sidebar object
        _sidebar.flow = flow
        _sidebar.retriever = retriever
        _sidebar.model = model
        # print("_sidebar.model after", _sidebar.model.model_kwargs)
        _sidebar.flow_or_retriever_or_model_changed = retriever_changed | model_changed | flow_changed
        _sidebar.uploaded_file_content = uploaded_file_content


        return _sidebar
    # flow, retriever, model, retriever_changed | model_changed | flow_changed, uploaded_file_content

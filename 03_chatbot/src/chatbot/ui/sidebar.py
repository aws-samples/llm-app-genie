""" Chatbot UI side panel. """
from io import BytesIO, StringIO
from logging import Logger
from typing import Callable, Generic, List, Tuple, TypeVar, Union
import tempfile
import os

import streamlit as st
from chatbot.catalog import (
    ModelCatalog,
    ModelCatalogItem,
    RetrieverCatalog,
    RetrieverCatalogItem,
    AgentChainCatalog,
    AgentChainCatalogItem,
    FlowCatalog,
    FlowCatalogItem,
)
from chatbot.config import AppConfig, AWSConfig
from numpy import ndarray
from streamlit.type_util import OptionSequence, T

from chatbot.catalog.agent_chain_catalog_item_sql_generator import AGENT_CHAIN_SQL_GENERATOR_NAME
from langchain.document_loaders import AmazonTextractPDFLoader

import boto3
from botocore.exceptions import ClientError
import logging

from textractor.data.text_linearization_config import TextLinearizationConfig

s3 = boto3.client('s3')
# set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
def upload_file_to_s3(file_name, bucket, object_name=None):
    if object_name is None:
        object_name = file_name
    try:
        s3.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logger.error(e)
        return False

def delete_file_from_s3(bucket, object_name):
    try:
        s3.delete_object(Bucket=bucket, Key=object_name)
    except ClientError as e:
        logger.error(e)
        return False

class SidebarObj():
    def init(self):
        self.flow = None
        self.retriever = None
        self.model = None
        self.agents_chains = None
        self.sql_model = None
        self.flow_or_retriever_or_model_or_agent_changed = False
        self.uploaded_file_content = ""
        self.sql_connection_uri = ""
        self.retriever_top_k = 3
        self.streaming = False


def write_sidebar(
        chatbot_name: str,
        app_icon: Union[ndarray, List[ndarray], BytesIO, str, List[str]],
        regions: List[str],
        app_config: AppConfig,
        aws_config: AWSConfig,
        logger: Logger,
        llm_callbacks,
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
        default_index = 0
        if selected_state_name in params and len(params.get_all(selected_state_name)) > 0:
            option_names = [str(option) for option in options]
            filtered_names = list(set(option_names) & set(params.get_all(selected_state_name)))
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
        params = st.query_params
        # Logo layout with 2 columns good for small square logo

        if "small_logo" in params:
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(app_icon, use_column_width="always")
            with col2:
                st.title(chatbot_name)
        else:
            st.image(app_icon, use_column_width="always")
            st.title(chatbot_name)


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

        # upload file button
        uploaded_file_content = ""
        if enable_file_upload:
            uploaded_file = \
                st.sidebar.file_uploader(
                    "Upload a file",
                    type=["txt", "json", "pdf"],
                    key=flow_options,
                )
            if uploaded_file is not None:
                if uploaded_file.type == "application/pdf":
                    docs = []
                    temp_dir = tempfile.TemporaryDirectory()
                    temp_filepath = os.path.join(temp_dir.name, uploaded_file.name)
                    with open(temp_filepath, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    bucket = st.session_state['textract_s3_bucket']
                    key = temp_filepath.split('/')[-1]
                    alternate_key = key.replace('.pdf', '.txt')
                    alternate_temp_filepath = temp_filepath.replace('.pdf', '.txt')
                    # Check if the file exists
                    try:
                        print(f"The file '{key}' exists in the '{bucket}' bucket.")
                        response = s3.get_object(Bucket=bucket, Key=alternate_key)
                        uploaded_file_content = response['Body'].read().decode('utf-8')
                        #print(f"File content:\n{uploaded_file_content}")
                    except s3.exceptions.NoSuchKey:
                        print(f"The file '{key}' does not exist in the '{bucket}' bucket.")
                        upload_file_to_s3(temp_filepath, bucket, key)
                        s3_path = f"s3://{bucket}/{key}"
                        loader = AmazonTextractPDFLoader(s3_path, textract_features=["TABLES", "LAYOUT", "FORMS"], linearization_config=TextLinearizationConfig(hide_header_layout=True,hide_footer_layout=True, hide_figure_layout=True))
                        docs.extend(loader.load())
                        uploaded_file_content = "=== BEGIN FILE ===\n"
                        for doc in docs:
                            uploaded_file_content += doc.page_content
                        uploaded_file_content += "\n=== END FILE ===\n"
                        with open(alternate_temp_filepath, 'w') as f:
                            f.write(uploaded_file_content)
                        upload_file_to_s3(alternate_temp_filepath, bucket, alternate_key)
                    #delete_file_from_s3(bucket, key)
                else:
                    uploaded_file_content = "=== BEGIN FILE ===\n"
                    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
                    uploaded_file_content += stringio.read()
                    uploaded_file_content += "\n=== END FILE ===\n"

        ########### AGENTS STUFF ###############
        agents_chains = None
        agents_chains_changed = False
        sql_connection_uri = ""
        sql_model = None
        sql_model_changed = False
        if flow.enable_agents_chains:
            agents_chains_state_name = "agents_chains_catalog"
            if agents_chains_state_name not in st.session_state:
                agents_chains_catalog = AgentChainCatalog(
                    regions, 
                    logger
                    )
                st.session_state[agents_chains_state_name] = agents_chains_catalog
                agents_chains_catalog.bootstrap()

            agents_chains_options = st.session_state[agents_chains_state_name]
            agents_chains_label = _("Agent Chains")
            agents_chains, agents_chains_changed = __render_dropdown(
                agents_chains_label, "agents_chains", agents_chains_options, params
                )

            filter_options = agents_chains.available_filter_options
            current_filter_options = agents_chains.current_filter

            filter_disabled = filter_options is None
            filter_options = [] if filter_options is None else filter_options

            filter_query_param_name = "filter"
            if (
                filter_query_param_name in params
                and len(params.get_all(filter_query_param_name)) > 0
                ):
                option_names = [option[0] for option in filter_options]
                filtered_names = list(
                    set(option_names) & set(params.get_all(filter_query_param_name))
                    )
                filter_options = [
                    option for option in filter_options if option[0] in filtered_names
                    ]

            if str(agents_chains) == AGENT_CHAIN_SQL_GENERATOR_NAME:
                sql_connection_uri = st.text_input(label="SQL DB connection URI", 
                                                key="sql_connection_uri"
                                                )

                ########### SQL TOOL MODEL STUFF ###############
                sql_model_state_name = "sql_model_catalog"
                if sql_model_state_name not in st.session_state:
                    sql_model_catalog = ModelCatalog(
                        regions,
                        bedrock_config=app_config.amazon_bedrock or [],
                        logger=logger,
                        llm_config=app_config.llm_config.parameters,
                        callbacks=llm_callbacks
                    )
                    st.session_state[sql_model_state_name] = sql_model_catalog
                    sql_model_catalog.bootstrap()
                    print("sql_model_catalog",sql_model_catalog)
                sql_model_options = st.session_state[sql_model_state_name]
                sql_language_model_label = _("SQL Tool Language Model")
                sql_model, sql_model_changed = __render_dropdown(
                    sql_language_model_label, "sql_model", sql_model_options, params
                    )

        ########### RETRIEVER STUFF ###############
        retriever = None
        retriever_changed = False
        if flow.enable_retriever:
            retriever_state_name = "retriever_catalog"
            if retriever_state_name not in st.session_state:
                retriever_catalog = RetrieverCatalog(
                    aws_config.account_id, 
                    regions, 
                    app_config,
                    logger
                    )
                st.session_state[retriever_state_name] = retriever_catalog
                retriever_catalog.bootstrap()

            retriever_options = st.session_state[retriever_state_name]
            knowledgebase_label = _("Knowledge Base")
            retriever, retriever_changed = __render_dropdown(
                knowledgebase_label, "retriever", retriever_options, params
                )

            if retriever:
                filter_options = retriever.available_filter_options
                current_filter_options = retriever.current_filter

                filter_disabled = filter_options is None

                filter_options = [] if filter_options is None else filter_options

                filter_query_param_name = "filter"
                if (
                    filter_query_param_name in params
                    and len(params.get_all(filter_query_param_name)) > 0
                    ):
                    option_names = [option[0] for option in filter_options]
                    filtered_names = list(
                        set(option_names) & set(params.get_all(filter_query_param_name))
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

                # Finance Analyzer specific options
                rag = app_config.flow_config.parameters.flows["Retrieval Augmented Generation"]
                if ("Stock Analysis" in rag and 
                    retriever.friendly_name == rag["Stock Analysis"]["friendlyName"]):
                    if len(options) > 0:
                        filtered_df = retriever.announcement_df[retriever.announcement_df["symbol"].isin(opt[0] for opt in options)]
                        retriever.announcement_filter = st.multiselect(
                            "Company Announcements", 
                            filtered_df.sort_values(by='id', ascending=False).id.tolist(),
                            placeholder=_("Select announcements for analysis")
                        )
                    else:
                        st.info("Select companies for analysis")
                
                else:
                    retriever.current_filter = options
                    
                    if (retriever.friendly_name in rag and len(retriever._selected_data_sources) > 0 and 
                        retriever._selected_data_sources[0][0] in rag[retriever.friendly_name] and
                        "rag" in rag[retriever.friendly_name][retriever._selected_data_sources[0][0]]
                    ):    
                        slider_config = rag[retriever.friendly_name][retriever._selected_data_sources[0][0]]["rag"]["retrievedDocumentsSlider"]
                    else:
                        slider_config = app_config.flow_config.parameters.flows["Retrieval Augmented Generation"]["retrievedDocumentsSlider"]

                    retriever.top_k = st.slider(
                        "Retrieved documents",
                        min_value=slider_config["minValue"],
                        max_value=slider_config["maxValue"],
                        value=slider_config["value"],
                        step=slider_config["step"]
                    )
            
        ########### MAIN MODEL STUFF ###############
        model_state_name = "model_catalog"
        if model_state_name not in st.session_state:
            model_catalog = ModelCatalog(
                regions,
                bedrock_config=app_config.amazon_bedrock or [],
                logger=logger,
                llm_config=app_config.llm_config.parameters,
                callbacks=llm_callbacks
            )
            st.session_state[model_state_name] = model_catalog
            model_catalog.bootstrap()
            print("model_catalog",model_catalog)
        model_options = st.session_state[model_state_name]
        language_model_label = _("Language Model")
        model, model_changed = __render_dropdown(
            language_model_label, "model", model_options, params
            )
        
        st.toggle(
            label=_("Language Model X-Ray ") + "🩻",
            value=show_llm_debug_messages,
            key="show_llm_debug_messages",
            help="Look behing the scenes at the full prompts."
        )

        if model is not None:
            supports_streaming = model.supports_streaming
            streaming_help_msg = _("Turn streaming on or off.") if supports_streaming else _("Model does not support streaming.")
            streaming = st.toggle(
                label=_("Streaming"),
                disabled=not supports_streaming,
                value=model.streaming_on,
                help=streaming_help_msg
            )
            model.streaming_on = streaming

        with st.expander('Change model parameters'):
            temperature = st.slider("Temperature",
                                    min_value=0.0,
                                    max_value=1.0,
                                    value=float(model.model_kwargs.get("temperature", 0.1)),
                                    step=0.1
                                    )
            model.model_kwargs["temperature"] = temperature
        
        # dump variables into sidebar object
        _sidebar.flow = flow
        _sidebar.retriever = retriever
        _sidebar.model = model
        _sidebar.agents_chains = agents_chains
        _sidebar.sql_model = sql_model
        _sidebar.flow_or_retriever_or_model_or_agent_changed = retriever_changed | model_changed | sql_model_changed | flow_changed | agents_chains_changed
        _sidebar.uploaded_file_content = uploaded_file_content
        _sidebar.sql_connection_uri = sql_connection_uri
        _sidebar.streaming = streaming

        return _sidebar

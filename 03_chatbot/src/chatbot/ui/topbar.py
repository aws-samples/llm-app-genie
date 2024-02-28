""" UI component that shows session information and session reset button."""
from typing import Callable

import streamlit as st
from streamlit_extras.colored_header import colored_header

from chatbot.catalog import (
    ModelCatalog,
    ModelCatalogItem,
    RetrieverCatalog,
    RetrieverCatalogItem,
)
import boto3
import yaml


def write_top_bar(session_id: str, on_refresh: Callable[[], None], gettext):
    """Write streamlit elements to show in the top bar.
    This is stateless.

    Args:
        session_id: Session ID.
        on_refresh: Callback to run when the session is reset.
        gettext: Translator function.
    """
    _ = gettext
    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown(f"#### Session ID:  {session_id}")

    with col2:
        reset_session_text = _("Reset Session")
        if st.button(reset_session_text):
            on_refresh()
    colored_header(label="", description="", color_name="blue-30")

def write_prompt_hints(sidebar):
    """Write prompt to show in the top bar.
    Args:
        sidebar: Streamlit sidebar object.
    """
        
    with open('src/chatbot/prompts/hints.yaml', 'r', encoding="utf8") as yaml_file:
        hints = yaml.safe_load(yaml_file)

    # TODO: this part should be moved to CDK
    # TODO: existing table should be cleaned
    # table_name = "genie-prompt-hints"

    # # TODO: Moved to the data part to convert to Dynamo DB in the next phase
    # dynamodb = boto3.resource('dynamodb')
    # table = dynamodb.Table(table_name)

    # # Insert data into DynamoDB table
    # for flow, flow_hints in hints.items():
    #     for knowledge_base, data_sources in flow_hints.items():
    #         for data_source, prompt_hints in data_sources.items():
    #             table.put_item(Item={'hints': prompt_hints, 'knowledge_base': flow + "|" + knowledge_base, 'data_source': data_source})

    # Define your query parameters
    flow = sidebar.flow.friendly_name
    knowledge_base = sidebar.retriever.friendly_name if sidebar.retriever is not None else flow
    data_sources = ["all"]

    if hasattr(sidebar.retriever, "_selected_data_sources"):
        data_sources += [opt[0] for opt in sidebar.retriever._selected_data_sources]

    results = []
    # Checking for the available hints based on user selection
    if flow in hints:
        if knowledge_base in hints[flow]:
            for data_source in data_sources:
                if data_source in hints[flow][knowledge_base]:
                    results += hints[flow][knowledge_base][data_source]

    # TODO: this part should be moved to CDK
    # # Define the query condition expression and expression attribute values
    # expression = "knowledge_base = :kb and data_source = :ds"

    # for data_source in data_sources:
    #     expression_attr_values = {":kb": flow + "|" + knowledge_base, ":ds": data_source}

    #     # Query the DynamoDB table
    #     response = table.query(
    #         TableName=table_name,
    #         KeyConditionExpression=expression,
    #         ExpressionAttributeValues=expression_attr_values
    #     )
        
    #     if response["Items"]:
    #         results += response["Items"][0]["hints"]

    if not results:
        return None
    
    pairs = zip(results, st.columns(len(results)))
    prompt = None
    for i, (text, col) in enumerate(pairs):
        if col.button(text["name"], f'''{text["name"]}-{i}'''):
            prompt = text['prompt']
    
    if prompt:
        return prompt

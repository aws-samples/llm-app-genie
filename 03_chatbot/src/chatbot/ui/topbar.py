""" UI component that shows session information and session reset button."""
from typing import Callable

import streamlit as st
from streamlit_extras.colored_header import colored_header


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

def write_prompt_hints(sidebar, config):
    """Write prompt to show in the top bar.
    Args:
        sidebar: Streamlit sidebar object.
    """

    flows = config.flow_config.parameters.flows
    # with open(config.appearance.parameters.prompt_config_path, 'r') as yaml_file:
    #     hints = yaml.safe_load(yaml_file)

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
    knowledge_base = sidebar.retriever.friendly_name if sidebar.retriever else None
    
    data_sources = []
    if hasattr(sidebar.retriever, "_selected_data_sources"):
        data_sources += [opt[0] for opt in sidebar.retriever._selected_data_sources]

    # Checking for the available hints based on user selection
    results = []
    if flow in flows:
        if "hints" in flows[flow]: # MM:: why flows is double, same down
            results += flows[flow]["hints"]
        elif knowledge_base and knowledge_base in flows[flow]:  # MM:: why flows is double
            if "hints" in flows[flow][knowledge_base]:
                results += flows[flow][knowledge_base]["hints"]
            for data_source in data_sources:
                if data_source in flows[flow][knowledge_base]:
                    results += flows[flow][knowledge_base][data_source]["hints"]

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
    
    # converting hints into buttongs
    pairs = zip(results, st.columns(len(results)))
    prompt = None
    for i, (text, col) in enumerate(pairs):
        if col.button(text["name"], f'''{text["name"]}-{i}'''):
            prompt = text['prompt']
    
    if prompt:
        return prompt

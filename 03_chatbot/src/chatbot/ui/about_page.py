""" Displat information about the app in the Streamlit settings page."""
from typing import Callable

import streamlit as st


def about_page(
    chatbot_name: str, favicon_url: str, gettext: Callable[[str], str] = lambda x: x
):
    """Configures the Streamlit app.
    NOTE: The page config is visible without signing in. DO NOT PUT confidential information in here.
    """

    _ = gettext
    page_name = _("{chatbot_name} - An LLM-powered app for your custom data").format(
        chatbot_name=chatbot_name
    )
    made_by_text = _(
        "Made with ❤️ by your AWS WWSO AIML EMEA and Swiss Alps Team (and Amazon CodeWhisperer 🤫)"
    )
    powered_by_text = _("LLM-powered app built using:")
    st.set_page_config(
        page_name,
        page_icon=favicon_url,
        menu_items={
            #    'Get Help': 'https://www.example.com/',
            #    'Report a bug': "mailto:malterei@amazon.com",
            "About": f"""
                {powered_by_text}
                - [Streamlit](https://streamlit.io/)
                - [LangChain](https://github.com/hwchase17/langchain)
                - [Amazon SageMaker](https://aws.amazon.com/sagemaker/) 
                - [Amazon Kendra](https://aws.amazon.com/kendra/)
                - [Amazon OpenSearch](https://aws.amazon.com/opensearch-service/)
                - [Amazon Bedrock](https://aws.amazon.com/bedrock/)

                {made_by_text}
                """
        },
    )

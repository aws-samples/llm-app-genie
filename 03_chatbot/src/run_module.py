""" Runs the chatbot module.
This is necessary to run a Streamlit app that is packaged a Python module."""
import runpy

# Make streamlit run our chatbot module.
# See also https://github.com/streamlit/streamlit/issues/662#issuecomment-553356419

runpy.run_module("chatbot", run_name="__main__", alter_sys=True)

""" UI component that shows session information and session reset button."""
from typing import Callable

import streamlit as st
from streamlit_extras.colored_header import colored_header


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

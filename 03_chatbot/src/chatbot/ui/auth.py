import streamlit as st


def check_password(app_name: str):
    """Returns `True` if the user had a correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"]
            == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    login_screen = st.empty()
    if "password_correct" not in st.session_state:
        # First run, show inputs for username + password.
        with login_screen.container():
            st.title(app_name)
            st.text_input("Username", on_change=password_entered, key="username")
            st.text_input(
                "Password", type="password", on_change=password_entered, key="password"
            )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        with login_screen.container():
            st.title(app_name)
            st.text_input("Username", on_change=password_entered, key="username")
            st.text_input(
                "Password", type="password", on_change=password_entered, key="password"
            )
            username = st.session_state["username"]
            password = st.session_state["password"]
            if username and password:
                # Only show if customer already entered username + password
                st.error("😕 User not known or password incorrect")
        return False
    else:
        # Password correct.
        login_screen.empty()
        return True

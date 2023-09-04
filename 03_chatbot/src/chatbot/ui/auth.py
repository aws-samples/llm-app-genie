import streamlit as st


def check_password(app_name: str):
    """Returns `True` if the user had a correct password."""

    login_screen = st.empty()

    if "username" not in st.session_state:
        st.session_state["username"] = ""

    if "passwords" not in st.session_state:
        st.session_state["passwords"] = ""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        password_check_not_active = (
            "username" not in st.session_state or "password" not in st.session_state
        )
        if password_check_not_active:
            return

        username_and_password_correct = (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"]
            == st.secrets["passwords"][st.session_state["username"]]
        )
        if username_and_password_correct:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store username + password
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    need_to_check_password = (
        "password_correct" not in st.session_state
        or not st.session_state["password_correct"]
    )
    if need_to_check_password:
        with login_screen.container():
            st.title(app_name)
            st.text_input("Username", key="username", on_change=password_entered)
            st.text_input(
                "Password", type="password", key="password", on_change=password_entered
            )
            username = st.session_state["username"]
            password = st.session_state["password"]

            entered_username_password_not_correct = (
                "password_correct" in st.session_state
                and not st.session_state["password_correct"]
                and username
                and password
            )
            if entered_username_password_not_correct:
                # Only show if customer already entered username + password
                st.error("😕 User not known or password incorrect")
            return False
    else:
        # Password correct.
        login_screen.empty()

        return True

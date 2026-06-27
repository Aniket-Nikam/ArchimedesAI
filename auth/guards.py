"""
Streamlit authentication guards.
Renders a clean, minimal login/register wall.
"""
import streamlit as st
from auth.auth_service import register_user, login_user, AuthError


def require_auth():
    """
    Checks if the user is authenticated.
    If not, renders the login/register page and stops execution.
    """
    if "user_id" not in st.session_state or st.session_state["user_id"] is None:
        _render_auth_page()
        st.stop()


def logout():
    """Clears all session state to log the user out."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def _render_auth_page():
    """Renders the full-page login/register UI — clean and minimal."""

    st.markdown("""
    <div class="auth-hero">
        <div class="logo">🧬</div>
        <h1>Archimedes</h1>
        <p>Your autonomous research assistant. Search across academic databases, 
        trace citation trails, and get AI-powered synthesis — all in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    # Centered form
    _, col_form, _ = st.columns([1, 2, 1])

    with col_form:
        tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                login_username = st.text_input(
                    "Username", placeholder="Your username",
                    label_visibility="collapsed"
                )
                login_password = st.text_input(
                    "Password", type="password", placeholder="Password",
                    label_visibility="collapsed"
                )
                st.markdown("<div style='height: 0.25rem'></div>", unsafe_allow_html=True)
                login_submitted = st.form_submit_button("Sign In", use_container_width=True)

                if login_submitted:
                    try:
                        user = login_user(login_username, login_password)
                        st.session_state["user_id"] = user["id"]
                        st.session_state["username"] = user["username"]
                        st.session_state["email"] = user["email"]
                        st.rerun()
                    except AuthError as e:
                        st.error(str(e))

        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                reg_username = st.text_input(
                    "Username", placeholder="Choose a username",
                    label_visibility="collapsed"
                )
                reg_email = st.text_input(
                    "Email", placeholder="you@example.com",
                    label_visibility="collapsed"
                )
                reg_password = st.text_input(
                    "Password", type="password", placeholder="Password (min 8 chars)",
                    label_visibility="collapsed"
                )
                reg_confirm = st.text_input(
                    "Confirm", type="password", placeholder="Confirm password",
                    label_visibility="collapsed"
                )
                st.markdown("<div style='height: 0.25rem'></div>", unsafe_allow_html=True)
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

                if reg_submitted:
                    if reg_password != reg_confirm:
                        st.error("Passwords do not match.")
                    else:
                        try:
                            user = register_user(reg_username, reg_email, reg_password)
                            st.session_state["user_id"] = user["id"]
                            st.session_state["username"] = user["username"]
                            st.session_state["email"] = user["email"]
                            st.rerun()
                        except AuthError as e:
                            st.error(str(e))

        st.caption("Your data is stored locally and never shared.")

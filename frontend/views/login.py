import streamlit as st
from supabase import create_client

def _save_session(result, cookies):
    session = result.session
    st.session_state.access_token = session.access_token
    st.session_state.user_email = getattr(result.user, "email", None) or getattr(session.user, "email", None)
    if cookies is not None and session.refresh_token:
        cookies["refresh_token"] = session.refresh_token
        cookies.save()


def render(url, anon_key, frontend_url=None, cookies=None):
    frontend_url = frontend_url or st.session_state.get("frontend_url", "http://localhost:8501")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("# Read less.\n# Understand more.")
        st.markdown("Your medical literature workspace. Ask questions across papers, trace every answer to evidence, and turn dense research into clear next steps.")
        st.info("Evidence-led discovery · Private research library · Cited responses")
    with right:
        st.markdown("### Sign in to ResearchIQ")
        if not url or not anon_key or "placeholder" in url.lower() or "placeholder" in anon_key.lower():
            st.error("Set SUPABASE_URL and SUPABASE_ANON_KEY in the project-root .env, then restart the backend.")
            return
        email = st.text_input("Email address", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.session_state.pop("verification_returned", False):
            st.success("Email confirmation link opened successfully. Now sign in with your email and password.")
        if st.session_state.get("verification_waiting", False):
            st.info("Check your inbox and spam folder for the confirmation email. Once verified, return here and sign in.")
        signin, signup = st.columns(2)
        try:
            client = st.session_state.get("supabase_client")
            if client is None:
                client = create_client(url, anon_key)
                st.session_state.supabase_client = client

            code = st.query_params.get("code")
            if code and st.session_state.get("oauth_pending"):
                result = client.auth.exchange_code_for_session(code)
                _save_session(result, cookies)
                st.session_state.oauth_pending = False
                st.session_state.verification_waiting = False
                st.query_params.clear()
                st.rerun()
            elif code:
                # Supabase verifies the email before redirecting here. The user signs in
                # explicitly so email confirmation does not depend on a lost PKCE session.
                st.query_params.clear()
                st.session_state.verification_waiting = False
                st.session_state.verification_returned = True
                st.rerun()

            with signin:
                if st.button("Sign in", type="primary", use_container_width=True):
                    result = client.auth.sign_in_with_password({"email": email, "password": password})
                    _save_session(result, cookies)
                    st.session_state.verification_waiting = False
                    st.rerun()
            with signup:
                if st.button("Create account", use_container_width=True):
                    result = client.auth.sign_up({
                        "email": email,
                        "password": password,
                        "options": {"email_redirect_to": frontend_url},
                    })
                    if result.session:
                        _save_session(result, cookies)
                        st.rerun()
                    st.session_state.verification_waiting = True
                    st.rerun()

            st.caption("Already created an account but still waiting for verification?")
            if st.button("Resend confirmation email", use_container_width=True):
                if not email.strip():
                    st.error("Enter the email address you used to create the account.")
                else:
                    client.auth.resend({
                        "type": "signup",
                        "email": email.strip(),
                        "options": {"email_redirect_to": frontend_url},
                    })
                    st.success("A new confirmation email was requested. Check your inbox and spam folder.")

            if st.button("Continue with Google", use_container_width=True):
                result = client.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {"redirect_to": frontend_url},
                })
                st.session_state.oauth_pending = True
                st.link_button("Continue to Google", result.url, use_container_width=True)
        except Exception as exc:
            message = str(exc)
            if "getaddrinfo" in message.lower() or "11001" in message:
                st.error("Could not reach Supabase Auth because DNS lookup failed. Check internet/VPN/proxy/DNS and try again.")
            else:
                st.error(message)

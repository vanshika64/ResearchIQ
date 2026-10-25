import re
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import streamlit as st
from supabase import ClientOptions, create_client

_OAUTH_COOKIE = "researchiq_oauth_code_verifier"
_OAUTH_STARTED_COOKIE = "researchiq_oauth_started_at"
_OAUTH_PENDING_COOKIE = "researchiq_oauth_pending"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class _CookieAuthStorage:
    """Keep Supabase's PKCE verifier across the full-page Google redirect."""

    def __init__(self, cookies):
        self.cookies = cookies
        self.memory = {}

    def get_item(self, key):
        if key.endswith("-code-verifier"):
            return self.cookies.get(_OAUTH_COOKIE)
        return self.memory.get(key)

    def set_item(self, key, value):
        if key.endswith("-code-verifier"):
            self.cookies[_OAUTH_COOKIE] = value
        else:
            self.memory[key] = value

    def remove_item(self, key):
        if key.endswith("-code-verifier"):
            if self.cookies.get(_OAUTH_COOKIE):
                del self.cookies[_OAUTH_COOKIE]
        else:
            self.memory.pop(key, None)

    def has_oauth_verifier(self):
        try:
            started = float(self.cookies.get(_OAUTH_STARTED_COOKIE) or "0")
        except (TypeError, ValueError):
            started = 0
        return (
            self.cookies.get(_OAUTH_PENDING_COOKIE) == "1"
            and bool(self.cookies.get(_OAUTH_COOKIE))
            and 0 <= time.time() - started < 900
        )


def _clear_oauth_cookies(cookies):
    changed = False
    for key in (_OAUTH_COOKIE, _OAUTH_STARTED_COOKIE, _OAUTH_PENDING_COOKIE):
        if cookies.get(key):
            del cookies[key]
            changed = True
    return changed


def _auth_redirect_url(frontend_url, flow):
    parts = urlsplit(frontend_url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["auth_flow"] = flow
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), parts.fragment))


def _save_session(result, cookies):
    session = result.session
    if not session:
        raise RuntimeError("Supabase did not return a sign-in session. Confirm your email, then sign in.")
    st.session_state.access_token = session.access_token
    st.session_state.user_email = getattr(result.user, "email", None) or getattr(session.user, "email", None)
    if cookies is not None and session.refresh_token:
        cookies["refresh_token"] = session.refresh_token
        cookies.save()


def _auth_error(exc):
    message = str(getattr(exc, "message", None) or exc)
    lowered = message.lower()
    if "getaddrinfo" in lowered or "11001" in lowered or "name or service not known" in lowered:
        return "Could not reach Supabase Auth. Check the Supabase URL and the app's internet/DNS connection."
    if "email address not authorized" in lowered:
        return "Supabase's default email sender only delivers to authorized team addresses. Configure custom SMTP in Supabase Auth to send confirmation emails to other users."
    if "rate limit" in lowered or "too many requests" in lowered:
        return "Supabase has temporarily rate-limited authentication emails. Wait before trying again, or configure custom SMTP and review Auth rate limits."
    if "email not confirmed" in lowered:
        return "This email is not confirmed yet. Use the confirmation link from your inbox. If no message arrived, configure SMTP and check Supabase Auth logs."
    if "provider is not enabled" in lowered or "unsupported provider" in lowered or "google" in lowered and "disabled" in lowered:
        return "Google sign-in is not enabled in Supabase. Enable Google under Authentication → Sign In / Providers and add its Client ID and Secret."
    if "weak password" in lowered or "password should be" in lowered:
        return "Choose a stronger password that meets the password requirements configured in Supabase."
    return message


def _is_invalid_credentials(exc):
    message = str(getattr(exc, "message", None) or exc).lower()
    return any(term in message for term in (
        "invalid login credentials",
        "invalid credentials",
        "invalid email or password",
        "email or password is incorrect",
        "user already registered",
        "email already registered",
        "weak password",
        "password should be",
    ))


def render(url, anon_key, frontend_url=None, cookies=None):
    frontend_url = (frontend_url or st.session_state.get("frontend_url", "http://localhost:8501")).strip().rstrip("/")
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown("# Read less.\n# Understand more.")
        st.markdown("Your medical literature workspace. Ask questions across papers, trace every answer to evidence, and turn dense research into clear next steps.")
        st.info("Evidence-led discovery · Private research library · Cited responses")
    with right:
        st.markdown("### Sign in to ResearchIQ")
        if not url or not anon_key or "placeholder" in url.lower() or "placeholder" in anon_key.lower():
            st.error("Set SUPABASE_URL and SUPABASE_ANON_KEY in the backend environment, then restart the backend.")
            return

        email = st.text_input("Email address", key="login_email").strip()
        password = st.text_input("Password", type="password", key="login_password")
        if st.session_state.pop("verification_returned", False):
            st.success("Email confirmed. Sign in with your email and password.")
        if st.session_state.get("verification_waiting", False):
            verification_email = st.session_state.get("verification_email", email)
            st.info(
                f"Check {verification_email} for the confirmation link and check your spam folder too. "
                "If it does not arrive, the Supabase project may need a configured SMTP sender."
            )
        signup_notice = st.session_state.get("signup_notice")
        if signup_notice:
            st.success(signup_notice)
        callback_error = st.session_state.pop("auth_callback_error", None)
        if callback_error:
            st.error(callback_error)

        try:
            client = st.session_state.get("supabase_client")
            storage = st.session_state.get("supabase_auth_storage")
            if client is None or storage is None:
                storage = _CookieAuthStorage(cookies)
                client = create_client(
                    url,
                    anon_key,
                    ClientOptions(storage=storage, flow_type="pkce"),
                )
                st.session_state.supabase_client = client
                st.session_state.supabase_auth_storage = storage

            code = st.query_params.get("code")
            auth_flow = st.query_params.get("auth_flow")
            callback_error_query = st.query_params.get("error_description") or st.query_params.get("error")
            if callback_error_query:
                _clear_oauth_cookies(cookies)
                cookies.save()
                st.query_params.clear()
                prefix = "Google sign-in was not completed" if auth_flow == "google" else "Email confirmation could not be completed"
                st.session_state.auth_callback_error = f"{prefix}: {callback_error_query}"
                st.rerun()
            if code and auth_flow == "email":
                # Supabase verifies the email link before redirecting here. Exchange
                # the PKCE code when the original browser still has its verifier;
                # cross-device confirmation can still finish and sign in manually.
                try:
                    if storage.get_item("researchiq-code-verifier"):
                        result = client.auth.exchange_code_for_session({"auth_code": code})
                        _clear_oauth_cookies(cookies)
                        _save_session(result, cookies)
                        st.session_state.verification_waiting = False
                        st.query_params.clear()
                        st.rerun()
                except Exception:
                    # Confirmation itself has already been accepted by Supabase.
                    pass
                _clear_oauth_cookies(cookies)
                cookies.save()
                st.query_params.clear()
                st.session_state.verification_waiting = False
                st.session_state.pop("signup_notice", None)
                st.session_state.verification_returned = True
                st.rerun()
            elif code and (
                auth_flow == "google"
                or (
                    not auth_flow
                    and not st.session_state.get("verification_waiting", False)
                    and storage.has_oauth_verifier()
                )
            ):
                if storage.has_oauth_verifier():
                    try:
                        # supabase-py expects an object containing auth_code, not a bare string.
                        result = client.auth.exchange_code_for_session({"auth_code": code})
                        _clear_oauth_cookies(cookies)
                        _save_session(result, cookies)
                        st.session_state.verification_waiting = False
                        st.query_params.clear()
                        st.rerun()
                    except Exception as exc:
                        _clear_oauth_cookies(cookies)
                        cookies.save()
                        st.query_params.clear()
                        st.session_state.auth_callback_error = f"Could not complete Google sign-in: {_auth_error(exc)}"
                        st.rerun()
                else:
                    _clear_oauth_cookies(cookies)
                    cookies.save()
                    st.query_params.clear()
                    st.session_state.auth_callback_error = "Google sign-in expired before it finished. Click Continue with Google and complete the sign-in within 15 minutes."
                    st.rerun()
            elif code:
                # Never report an unknown callback as a successful email confirmation.
                # Google callbacks must preserve auth_flow through Supabase's redirect allowlist.
                _clear_oauth_cookies(cookies)
                cookies.save()
                st.query_params.clear()
                st.session_state.auth_callback_error = (
                    "The sign-in callback did not include its flow type, so the app could not safely finish authentication. "
                    "Add these exact URLs under Supabase Auth → URL Configuration → Redirect URLs: "
                    "https://research-iq1.streamlit.app?auth_flow=google and "
                    "https://research-iq1.streamlit.app?auth_flow=email, then retry."
                )
                st.rerun()

            signin, signup = st.columns(2)
            with signin:
                if st.button("Sign in", type="primary", use_container_width=True):
                    if not _EMAIL_RE.fullmatch(email) or not password:
                        st.warning("Enter valid credentials.")
                    else:
                        try:
                            result = client.auth.sign_in_with_password({"email": email, "password": password})
                            _save_session(result, cookies)
                            st.session_state.verification_waiting = False
                            st.session_state.pop("signup_notice", None)
                            st.rerun()
                        except Exception as exc:
                            if _is_invalid_credentials(exc):
                                st.warning(
                                    "We couldn't find an account matching those credentials. Check your email and password, "
                                    "or create an account if you haven't registered yet."
                                )
                            else:
                                st.error(_auth_error(exc))

            with signup:
                if st.button("Create account", use_container_width=True):
                    if not _EMAIL_RE.fullmatch(email):
                        st.warning("Enter valid credentials.")
                    elif not password:
                        st.warning("Enter valid credentials.")
                    elif len(password) < 8:
                        st.warning("Enter valid credentials.")
                    else:
                        try:
                            result = client.auth.sign_up({
                                "email": email,
                                "password": password,
                                "options": {"email_redirect_to": _auth_redirect_url(frontend_url, "email")},
                            })
                            if result.session:
                                _save_session(result, cookies)
                                st.session_state.verification_waiting = False
                                st.session_state.pop("signup_notice", None)
                                st.rerun()
                            identities = getattr(result.user, "identities", None)
                            if identities == []:
                                # Supabase intentionally obfuscates already-registered users.
                                st.session_state.verification_waiting = False
                                st.session_state.signup_notice = (
                                    "No new account was created for this request, so no confirmation email may be sent. "
                                    "Try signing in, or choose Continue with Google if you registered with Google."
                                )
                            else:
                                st.session_state.verification_waiting = True
                                st.session_state.verification_email = email
                                st.session_state.signup_notice = (
                                    f"Signup submitted. Supabase accepted the request and a confirmation email was requested for {email}. "
                                    "Check your inbox and spam folder."
                                )
                                # Preserve the signup PKCE verifier for the email-link callback.
                                cookies.save()
                            st.rerun()
                        except Exception as exc:
                            if _is_invalid_credentials(exc):
                                st.warning("Enter valid credentials.")
                            else:
                                st.error(_auth_error(exc))

            if not st.session_state.get("verification_waiting", False):
                try:
                    _clear_oauth_cookies(cookies)
                    result = client.auth.sign_in_with_oauth({
                        "provider": "google",
                        "options": {"redirect_to": _auth_redirect_url(frontend_url, "google")},
                    })
                    cookies[_OAUTH_STARTED_COOKIE] = str(time.time())
                    cookies[_OAUTH_PENDING_COOKIE] = "1"
                    cookies.save()
                    st.link_button("Continue with Google", result.url, use_container_width=True)
                except Exception as exc:
                    _clear_oauth_cookies(cookies)
                    cookies.save()
                    st.error(_auth_error(exc))
        except Exception as exc:
            st.error(_auth_error(exc))

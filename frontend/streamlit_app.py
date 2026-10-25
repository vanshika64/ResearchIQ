import os
from pathlib import Path
import time
import streamlit as st
import requests
from dotenv import load_dotenv

# streamlit-cookies-manager 0.2.x still decorates its key derivation helper
# with the removed st.cache API. Keep it compatible with newer Streamlit.
if not hasattr(st, "cache"):
    st.cache = st.cache_data

from streamlit_cookies_manager import EncryptedCookieManager
from supabase import create_client
from components.layout import styles, sidebar
from services.api import request
from views.login import render as render_login

st.set_page_config(page_title="ResearchIQ", page_icon="✳", layout="wide")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

def get_setting(name, default=""):
    """Read local environment variables or hosted Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


cookie_password = get_setting("SESSION_COOKIE_PASSWORD").strip()
if not cookie_password:
    st.error("Add SESSION_COOKIE_PASSWORD to Streamlit Cloud → App settings → Secrets, or set it in the project-root .env for local development.")
    st.stop()
cookies = EncryptedCookieManager(prefix="researchiq/", password=cookie_password)
if not cookies.ready():
    st.stop()
styles()
backend = get_setting(
    "RESEARCHIQ_API_URL",
    "https://researchiq-2oak.onrender.com",
)

config = None
backend_error = None
with st.spinner("Connecting to the backend. A free Render service may take up to a minute to wake…"):
    for attempt, timeout in enumerate(((8, 55), (8, 35)), start=1):
        try:
            response = requests.get(backend.rstrip("/") + "/api/config", timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("The backend returned an invalid configuration response.")
            config = payload
            break
        except (requests.RequestException, ValueError) as exc:
            backend_error = exc
            if attempt < 2:
                time.sleep(2)

if config is None:
    st.error(f"Cannot reach the configured ResearchIQ backend at {backend}. Details: {backend_error}")
    st.info("If this is a free Render service, wait for it to wake and refresh. If it keeps failing, check that RESEARCHIQ_API_URL in Streamlit Cloud Secrets is the exact Render service URL and that the Render deployment is live.")
    st.stop()
if not config.get("supabaseUrl") or not config.get("supabaseAnonKey"):
    st.error("The backend is reachable, but it did not provide Supabase configuration. Set SUPABASE_URL and SUPABASE_ANON_KEY in the Render backend environment, then redeploy.")
    st.stop()

if "access_token" not in st.session_state:
    auth_callback_in_progress = bool(st.query_params.get("code"))
    refresh_token = cookies.get("refresh_token")
    if refresh_token and config.get("supabaseUrl") and config.get("supabaseAnonKey"):
        try:
            auth_client = create_client(config["supabaseUrl"], config["supabaseAnonKey"])
            refreshed = auth_client.auth.refresh_session(refresh_token)
            if refreshed.session:
                st.session_state.access_token = refreshed.session.access_token
                st.session_state.user_email = getattr(refreshed.user, "email", None) or getattr(refreshed.session.user, "email", None)
                st.session_state.supabase_client = auth_client
                cookies["refresh_token"] = refreshed.session.refresh_token
                cookies.save()
            else:
                del cookies["refresh_token"]
                cookies.save()
        except Exception as exc:
            message = str(exc).lower()
            if "refresh token" in message and any(
                marker in message for marker in ("invalid", "expired", "not found", "already used")
            ):
                try:
                    del cookies["refresh_token"]
                    cookies.save()
                except KeyError:
                    pass
                if not auth_callback_in_progress:
                    st.info("Your saved sign-in session expired. Sign in again to continue.")
            else:
                # Keep the cookie on transient network failures so the user can retry.
                st.warning("Could not restore your saved session because Supabase could not be reached. Check your connection, then sign in again.")
    if "access_token" in st.session_state:
        st.rerun()
    st.markdown('<div class="eyebrow">YOUR RESEARCH WORKSPACE</div>', unsafe_allow_html=True)
    st.session_state.frontend_url = config.get("frontendUrl", "http://localhost:8501")
    render_login(config.get("supabaseUrl"), config.get("supabaseAnonKey"), cookies=cookies)
    st.stop()

token = st.session_state.access_token
sidebar(st.session_state.get("user_email"), cookies=cookies)
st.markdown('<div class="eyebrow">MEDICAL LITERATURE WORKSPACE</div>', unsafe_allow_html=True)
st.title("Research desk")
st.markdown('<div class="hero"><h2>Your papers, in conversation.</h2><p>Upload research, ask precise questions, and follow every insight back to its source.</p></div>', unsafe_allow_html=True)

try:
    papers = request(backend, "/papers", token)
    history = request(backend, "/history", token)
except Exception as exc:
    st.error(f"Could not load your research workspace: {exc}")
    st.stop()

research_tab, history_tab = st.tabs(["⌕  Research assistant", "◷  Research history"])
with research_tab:
    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.subheader("Ask your library")
        modes = {"Search": "search", "Ask": "question", "Summarize": "summary", "Compare": "comparison", "Find gaps": "gaps", "Research report": "report"}
        mode_label = st.radio("Choose a research task", list(modes), horizontal=True, label_visibility="collapsed")
        selected = st.multiselect("Select papers", options=papers, format_func=lambda p: p["title"],
                                  default=papers if len(papers) < 3 else [], key="selected_papers")
        prompts = {
            "Search": "Find the most relevant passages about…",
            "Ask": "What would you like to know about these studies?",
            "Summarize": "Summarize the objective, methods, findings, and limitations.",
            "Compare": "Compare these studies across methods, findings, and limitations.",
            "Find gaps": "What possible research gaps are suggested by these papers?",
            "Research report": "Generate a structured report about these papers.",
        }
        query = st.text_area("Question or focus", placeholder=prompts[mode_label], height=115)
        if st.button("Find evidence  ↗", type="primary", use_container_width=True, disabled=not selected):
            question = query.strip() or prompts[mode_label]
            with st.spinner("Searching your papers and preparing cited findings…"):
                try:
                    endpoint = "/search" if mode_label == "Search" else "/research"
                    result = request(backend, endpoint, token, method="POST", json={
                        "query": question, "paper_ids": [p["id"] for p in selected], "kind": modes[mode_label]
                    })
                    st.session_state.last_result = result
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        result = st.session_state.get("last_result")
        if result:
            st.divider()
            st.markdown(f'<div class="eyebrow">{result["kind"]} · GROUNDED RESPONSE</div>', unsafe_allow_html=True)
            st.markdown(result["answer"])
            st.markdown(f"**Evidence and sources ({len(result['sources'])})**")
            for index, source in enumerate(result["sources"], 1):
                with st.container(border=True):
                    st.caption(f"[{index}] {source['filename']} · page {source['page']}")
                    st.markdown(f"**{source['title']}**")
                    st.write(source["excerpt"])
            report = f"# ResearchIQ {result['kind'].title()}\n\n## Query\n{result['query']}\n\n## Findings\n{result['answer']}\n\n## Sources\n"
            report += "\n\n".join(f"[{i}] {s['title']} ({s['filename']})\n{s['excerpt']}" for i, s in enumerate(result["sources"], 1))
            st.download_button("⇩ Export structured report", report, file_name="researchiq-report.md", mime="text/markdown")
    with right:
        st.subheader("Your paper library")
        st.caption("Medical, disease, biomedical, and healthcare research PDFs only · Private to your account")
        uploaded = st.file_uploader("Upload research PDFs", type=["pdf"], accept_multiple_files=True)
        if uploaded:
            for pdf in uploaded:
                if st.button(f"Add {pdf.name}", key=f"upload-{pdf.name}"):
                    with st.spinner("Extracting paper text…"):
                        try:
                            request(backend, "/papers", token, method="POST", files={"file": (pdf.name, pdf.getvalue(), "application/pdf")})
                            st.success(f"Added {pdf.name}")
                            st.rerun()
                        except Exception as exc:
                            st.error(str(exc))
        st.caption(f"{len(papers):02d} PAPERS")
        if not papers:
            st.info("Your library is empty. Upload a text based PDF to begin.")
        for paper in papers:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"📄 **{paper['title']}**  \n`{paper['filename']}`")
            if c2.button("×", key=f"delete-{paper['id']}", help="Remove paper"):
                try:
                    request(backend, f"/papers/{paper['id']}", token, method="DELETE")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        st.divider()
        st.subheader("Recent activity")
        for item in history[:5]:
            with st.container(border=True):
                st.caption(item["kind"].upper())
                st.write(item["query"])
                if st.button("Open", key=f"recent-{item['id']}"):
                    st.session_state.last_result = item
                    st.rerun()

with history_tab:
    heading, action = st.columns([4, 1])
    heading.subheader("Your research trail")
    if action.button("Clear history"):
        try:
            request(backend, "/history", token, method="DELETE")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if not history:
        st.info("Questions, answers, and their sources will appear here.")
    for item in history:
        with st.expander(f"{item['kind'].title()} · {item['query']}"):
            st.markdown(item["answer"])
            for index, source in enumerate(item.get("sources", []), 1):
                st.markdown(f"**[{index}] {source['title']}** — {source['filename']}, page {source['page']}")
                st.caption(source["excerpt"])

import streamlit as st
from pathlib import Path

def styles():
    asset_css = (Path(__file__).resolve().parents[1] / "assets" / "theme.css").read_text(encoding="utf-8")
    # Keep the complete stylesheet inside one Markdown HTML block. Separate
    # adjacent style blocks can be parsed as visible Markdown text by Streamlit.
    st.markdown(
        f"<style>\n{asset_css}\n</style>",
        unsafe_allow_html=True,
    )

def sidebar(email, cookies=None):
    with st.sidebar:
        st.markdown("## ◈ MedNext")
        st.caption("MEDICAL EVIDENCE WORKSPACE")
        st.divider()
        st.markdown(f"**{email or 'Researcher'}**")
        if st.button("Sign out", use_container_width=True):
            client = st.session_state.get("supabase_client")
            if client:
                try:
                    with st.spinner("Signing you out securely…"):
                        client.auth.sign_out()
                except Exception:
                    pass
            if cookies is not None:
                try:
                    del cookies["refresh_token"]
                    cookies.save()
                except KeyError:
                    pass
            for key in ("access_token", "user_email", "supabase_client"):
                st.session_state.pop(key, None)
            st.rerun()
        st.divider()
        st.caption("Answers use evidence retrieved from your uploaded papers.")

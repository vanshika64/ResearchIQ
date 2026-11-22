import streamlit as st
from pathlib import Path

def styles():
    asset_css = (Path(__file__).resolve().parents[1] / "assets" / "theme.css").read_text(encoding="utf-8")
    st.markdown("""
    <style>
    .block-container{max-width:1440px;padding-top:2rem;padding-bottom:4rem}
    [data-testid="stSidebar"]{background:#f0f5f1;border-right:1px solid #e2e9e4}
    h1,h2,h3{letter-spacing:-.035em}
    .hero{background:linear-gradient(120deg,#183d32,#23684f);color:white;padding:26px 30px;border-radius:18px;margin:10px 0 22px}
    .hero h2{color:white;margin:0 0 8px}.hero p{color:#c5ddd1;margin:0}
    .eyebrow{font-size:11px;text-transform:uppercase;letter-spacing:.13em;color:#17785f;font-weight:700}
    .source{background:#f5f9f5;border:1px solid #e3ebe4;padding:12px 14px;border-radius:10px;margin:8px 0}
    .muted{color:#718079;font-size:13px}
    </style>""" + f"<style>{asset_css}</style>", unsafe_allow_html=True)

def sidebar(email, cookies=None):
    with st.sidebar:
        st.markdown("## ✳ ResearchIQ")
        st.caption("MEDICAL LITERATURE WORKSPACE")
        st.divider()
        st.markdown(f"**{email or 'Researcher'}**")
        if st.button("Sign out", use_container_width=True):
            client = st.session_state.get("supabase_client")
            if client:
                try:
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

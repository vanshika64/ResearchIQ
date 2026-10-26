import streamlit as st
from pathlib import Path

THEMES = {
    "Light": {
        "app_bg": "#F8FAFC", "sidebar": "#FFFFFF", "card": "#FFFFFF",
        "text": "#172033", "muted": "#64748B", "accent": "#6D5AE6",
        "accent_hover": "#5945D0", "soft": "#F0EDFF", "border": "#E2E8F0",
        "input": "#FFFFFF", "shadow": "0 8px 24px rgba(23,32,51,.055)", "scheme": "light",
    },
    "Dark": {
        "app_bg": "#0B0D12", "sidebar": "#11141C", "card": "#171B26",
        "text": "#F1F5F9", "muted": "#9CA3B4", "accent": "#A78BFA",
        "accent_hover": "#C4B5FD", "soft": "#29213F", "border": "#292E3B",
        "input": "#11141C", "shadow": "0 10px 30px rgba(0,0,0,.20)", "scheme": "dark",
    },
}


def initialize_theme():
    """Initialize only the dedicated UI theme state; leave app state untouched."""
    if "medlitiq_theme" not in st.session_state:
        st.session_state["medlitiq_theme"] = "Light"
    if st.session_state["medlitiq_theme"] not in THEMES:
        st.session_state["medlitiq_theme"] = "Light"


def styles():
    initialize_theme()
    theme = THEMES[st.session_state["medlitiq_theme"]]
    variables = ";".join(f"--{name.replace('_', '-')}: {value}" for name, value in theme.items())
    asset_css = (Path(__file__).resolve().parents[1] / "assets" / "theme.css").read_text(encoding="utf-8")
    st.markdown(
        "<style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');"
        f":root{{{variables}}}{asset_css}</style>",
        unsafe_allow_html=True,
    )

def _theme_control():
    st.markdown("**Appearance**")
    st.segmented_control(
        "Appearance",
        options=["Light", "Dark"],
        format_func=lambda value: "☀️ Light mode" if value == "Light" else "🌙 Dark mode",
        key="medlitiq_theme",
        label_visibility="collapsed",
        width="stretch",
    )


def sidebar(email, cookies=None, research_modes=None):
    mode_label = None
    with st.sidebar:
        st.markdown(
            '<div class="brand-lockup"><span class="brand-mark">M</span>'
            '<span class="brand-name">MedLitIQ</span></div>',
            unsafe_allow_html=True,
        )
        st.caption("Medical literature. Clearer insights.")
        st.divider()
        if email and research_modes:
            mode_label = st.radio(
                "Research tools",
                options=list(research_modes),
                key="medlitiq_research_mode",
            )
        else:
            _theme_control()
        st.divider()
        if email:
            st.markdown('<div class="sidebar-section-label">SIGNED IN AS</div>', unsafe_allow_html=True)
            st.markdown(f"**{email}**")
            if st.button("Sign out", use_container_width=True, key="medlitiq_sign_out"):
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
        else:
            st.markdown('<div class="sidebar-note">Your private workspace for medical research papers, evidence, and citations.</div>', unsafe_allow_html=True)
        if email and research_modes:
            st.divider()
            _theme_control()
        st.divider()
        st.caption("Answers use evidence retrieved from your uploaded papers.")
    return mode_label

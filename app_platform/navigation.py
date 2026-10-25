from __future__ import annotations

import streamlit as st


WORKSPACE_PAGES = {
    "Customer Portal": st.Page(
        "app.py",
        title="Customer Portal",
        icon=":material/person:",
        default=True,
    ),
    "Analyst Console": st.Page(
        "admin_dashboard.py",
        title="Analyst Console",
        icon=":material/shield:",
    ),
}


def render_workspace_switcher(current_page: str) -> None:
    if not st.session_state.get("_unified_streamlit_app"):
        return

    st.selectbox(
        "Switch workspace",
        list(WORKSPACE_PAGES),
        index=list(WORKSPACE_PAGES).index(current_page),
        key="unified_page_selector",
        label_visibility="collapsed",
        on_change=switch_workspace,
    )


def switch_workspace() -> None:
    selected_page = st.session_state["unified_page_selector"]
    st.switch_page(WORKSPACE_PAGES[selected_page])

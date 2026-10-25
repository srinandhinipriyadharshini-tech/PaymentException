import streamlit as st

from app_platform.navigation import WORKSPACE_PAGES

st.session_state["_unified_streamlit_app"] = True

current_page = st.navigation(list(WORKSPACE_PAGES.values()), position="hidden")
current_page.run()

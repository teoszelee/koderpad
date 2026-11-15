import streamlit as st

from auth import require_sign_in

st.set_page_config(
    page_title="Koderpad",
    page_icon=":material/code:",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.title("Koderpad")

require_sign_in()

page = st.navigation(
    [
        st.Page(
            "app_pages/python.py",
            title="Python",
            icon=":material/code:",
            default=True,
            help="Edit and run Python exercises. Inspect printed output and errors.",
        ),
        st.Page(
            "app_pages/sql.py",
            title="SQL",
            icon=":material/database:",
            help="Run PostgreSQL exercises and browse tables. Each Run resets public.",
        ),
        st.Page(
            "app_pages/dockerfile.py",
            title="Dockerfile",
            icon=":material/deployed_code:",
            help="Load and edit Dockerfile examples without building containers.",
        ),
    ],
    position="top",
)
page.run()

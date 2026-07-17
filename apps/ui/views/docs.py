"""
This module contains the documentation page for the billing extraction demo.
This should explain the purpose of the app, what GroundX does,
what a successful run looks like, and how to navigate the app.
"""

import streamlit as st

from apps.ui.components.docs_content import (
    WHAT_THIS_APP_IS,
    WHAT_GROUNDX_DOES,
    WHAT_TO_EXPECT,
    HOW_TO_NAVIGATE,
)


def docs_page():
    """User-facing documentation for the billing extraction demo."""
    st.header("Documentation")
    st.caption("What this app is, what GroundX does, and what a successful run looks like.")

    st.markdown("## What this app is")
    st.markdown(WHAT_THIS_APP_IS)

    st.markdown("## What GroundX is doing")
    st.markdown(WHAT_GROUNDX_DOES)

    st.markdown("## What you should expect")
    st.markdown(WHAT_TO_EXPECT)

    st.markdown("## Tabs in this UI")
    st.markdown(HOW_TO_NAVIGATE)

    st.info(
        "Start with **Infrastructure Check**, then **Upload & Process** a sample bill."
    )

"""Main entry point for the Billing Extraction Streamlit application."""

import streamlit as st

from apps.ui.views.upload import upload_page
from apps.ui.views.view_data import view_data_page
from apps.ui.views.submissions import submissions_page
from apps.ui.views.docs import docs_page
from apps.ui.views.infra import infra_page

# --- Session state ---
# Initialize all session keys to None to avoid KeyError on first access
for key in (
    "uploaded_file",
    "extracted_data",
    "bucket_id",
    "workflow_id",
    "process_id",
    "document_id",
    "submission_id",
    "sample_doc_filename",
):
    if key not in st.session_state:
        st.session_state[key] = None

if "selected_yaml_file" not in st.session_state:
    st.session_state.selected_yaml_file = "simple.yaml"

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

# --- Page config ---
st.set_page_config(page_title="Billing Extraction", layout="wide")

# Custom CSS classes for syntax-highlighted JSON display
st.markdown(
    """<style>
    .json-key { color: #2E8B57; }
    .json-string { color: #191970; }
    .json-number { color: #8B4513; }
    .json-boolean { color: #9932CC; }
    .json-null { color: #CD5C5C; }
    </style>""",
    unsafe_allow_html=True,
)

# Map page labels to their render functions
PAGES = {
    "Documentation": docs_page,
    "Infrastructure Check": infra_page,
    "Upload & Process": upload_page,
    "View Extracted Data": view_data_page,
    "Job History": submissions_page,
}


def main():
    """Render the sidebar navigation and route to the selected page."""
    st.title("Billing Extraction Application")
    st.sidebar.header("Navigation")
    page_label = st.sidebar.radio("Go to", list(PAGES.keys()))
    PAGES[page_label]()


if __name__ == "__main__":
    main()

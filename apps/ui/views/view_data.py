import json

import streamlit as st

from apps.ui.components.document_processor import DocumentProcessor
from apps.ui.components.formatting import format_json


def _flatten(data, prefix=""):
    """Flatten a (possibly nested) extraction dict into Field/Value/Type rows."""
    rows = []
    if isinstance(data, dict):
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (dict, list)):
                rows.extend(_flatten(v, key))
            else:
                rows.append({"Field": key, "Value": str(v), "Type": type(v).__name__})
    elif isinstance(data, list):
        for i, item in enumerate(data):
            rows.extend(_flatten(item, f"{prefix}[{i}]"))
    else:
        rows.append({"Field": prefix, "Value": str(data), "Type": type(data).__name__})
    return rows


def view_data_page():
    """Display extracted billing data in raw JSON and tabular views, with download support."""
    st.header("View Extracted Data")
    if not st.session_state.extracted_data:
        st.warning("No extracted data available. Please process a document first.")
        return

    data = st.session_state.extracted_data

    # Show the identifiers for the job that produced this data.
    ids = {
        k: st.session_state.get(k)
        for k in ("submission_id", "document_id", "process_id", "workflow_id", "bucket_id")
        if st.session_state.get(k) is not None
    }
    if ids:
        st.caption("Produced by job:")
        st.json(ids)

    if not DocumentProcessor.extract_has_values(data):
        st.error(
            "This extract is an empty schema (all null/blank fields). "
            "Ingest completed, but the layout/extract LLM did not populate values. "
            "Check that `GROUNDX_AGENT_API_KEY` is a real OpenAI-compatible key "
            "(not `sk-CHANGE_ME`), then re-process the document."
        )

    st.subheader("Extracted Billing Information")
    st.markdown("### Raw Data:")
    formatted = format_json(data)
    st.markdown(
        f'<pre style="background-color:#f0f0f0;padding:10px;border-radius:5px;">{formatted}</pre>',
        unsafe_allow_html=True,
    )
    st.markdown("### Tabular View:")
    st.table(_flatten(data))

    st.download_button(
        label="Download Extracted Data",
        data=json.dumps(data, indent=2, default=str),
        file_name="extracted_billing_data.json",
        mime="application/json",
    )

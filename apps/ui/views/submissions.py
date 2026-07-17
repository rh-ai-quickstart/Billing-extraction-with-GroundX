import json

import streamlit as st

from apps.ui.components.document_processor import DocumentProcessor
from apps.ui.components.submission_store import SubmissionStore


def submissions_page():
    """Job History — list stored submissions and the data extracted by each job."""
    st.header("Job History")
    st.caption("Every processed document is stored here with the data it extracted.")

    store = SubmissionStore()
    submissions = store.list()
    if not submissions:
        st.info("No submissions yet. Process a document to create one.")
        return

    # Summary table of every job.
    st.table(
        [
            {
                "Submission": s.get("id", ""),
                "Created": s.get("created_at", ""),
                "File": s.get("filename", ""),
                "Status": s.get("status", ""),
                "Document ID": s.get("document_id", "") or "—",
            }
            for s in submissions
        ]
    )

    # Detail view for a selected job.
    ids = [s.get("id", "") for s in submissions]
    selected = st.selectbox("Inspect a submission", ids)
    record = store.get(selected)
    if not record:
        return

    st.subheader(f"Submission {selected}")
    st.json(
        {
            k: record.get(k)
            for k in (
                "created_at",
                "filename",
                "file_size",
                "yaml_file",
                "status",
                "bucket_id",
                "workflow_id",
                "process_id",
                "document_id",
            )
            if record.get(k) is not None
        }
    )

    if record.get("error"):
        st.error(record["error"])

    extracted = record.get("extracted_data")
    if extracted:
        st.markdown("### Extracted Data")
        if not DocumentProcessor.extract_has_values(extracted):
            st.warning(
                "All extracted fields are null/blank. This usually means the "
                "extract LLM failed (check `GROUNDX_AGENT_API_KEY`) rather than "
                "a UI display bug."
            )
        st.json(extracted)
        st.download_button(
            label="Download JSON",
            data=json.dumps(extracted, indent=2, default=str),
            file_name=f"extraction_{selected}.json",
            mime="application/json",
        )

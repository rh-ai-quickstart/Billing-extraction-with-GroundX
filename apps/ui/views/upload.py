import os

import streamlit as st

from apps.ui.components.client import BillingClient
from apps.ui.components.document_processor import DocumentProcessor, DocumentProcessorError
from apps.ui.components.sample_documents import available_samples, load_sample
from apps.ui.components.submission_store import SubmissionStore
from apps.ui.components.yaml_manager import YAMLManager


def _render_schema_preview(selected_yaml: str) -> None:
    """Show the active extraction schema in a collapsed expander."""
    with st.expander(f"Extraction schema: `{selected_yaml}`", expanded=False):
        raw = YAMLManager().load_raw(selected_yaml)
        if raw is None:
            st.warning(f"Could not load `{selected_yaml}` from `prompts/`.")
            return
        st.code(raw, language="yaml")


def _render_sample_selector() -> None:
    """Let the user pick one of the sample bills in ``test-docs/``."""
    samples = available_samples()
    if not samples:
        st.caption("No sample documents found in `test-docs/`.")
        return

    st.subheader("Sample documents")
    st.caption("Select a sample bill from `test-docs/` to extract data from.")

    cols = st.columns(len(samples))
    for col, sample in zip(cols, samples):
        with col:
            selected = st.session_state.get("sample_doc_filename") == sample.filename
            label = f"✓ {sample.label}" if selected else sample.label
            if st.button(label, key=f"sample_{sample.filename}", use_container_width=True):
                st.session_state.sample_doc_filename = sample.filename
                st.session_state.uploaded_file = None
                # Bump the uploader key so a prior upload does not stick.
                st.session_state.uploader_key = (
                    st.session_state.get("uploader_key", 0) + 1
                )
                st.rerun()


def _resolve_document():
    """Return the active document: user upload wins over a sample selection."""
    uploader_key = st.session_state.get("uploader_key", 0)
    uploaded_file = st.file_uploader(
        "Or upload your own billing document",
        type=["pdf", "jpg", "jpeg", "png"],
        key=f"billing_upload_{uploader_key}",
    )
    if uploaded_file is not None:
        # A fresh upload clears any prior sample choice.
        if st.session_state.get("sample_doc_filename"):
            st.session_state.sample_doc_filename = None
        return uploaded_file

    sample_name = st.session_state.get("sample_doc_filename")
    if sample_name:
        sample = load_sample(sample_name)
        if sample is None:
            st.error(f"Sample `{sample_name}` is missing from `test-docs/`.")
            st.session_state.sample_doc_filename = None
            return None
        st.info(f"Using sample document: **{sample.name}**")
        return sample

    return None


def _render_document_preview(uploaded_file) -> None:
    """Optional collapsed preview of the selected PDF or image."""
    ext = uploaded_file.name.rsplit(".", 1)[-1].lower()
    with st.expander(f"Preview: `{uploaded_file.name}`", expanded=False):
        if ext == "pdf":
            try:
                st.pdf(uploaded_file.getvalue(), height=600)
            except Exception as exc:
                st.warning(
                    "PDF preview is unavailable. Install the Streamlit PDF "
                    f"extra (`pip install 'streamlit[pdf]'`). Details: {exc}"
                )
        elif ext in ("jpg", "jpeg", "png"):
            st.image(uploaded_file.getvalue(), use_container_width=True)
        else:
            st.caption("Preview is not available for this file type.")


def upload_page():
    """Upload page — validates the file and runs the GroundX extraction pipeline.

    This drives the same steps as ``get_started.ipynb``: create a bucket, create
    the extraction workflow from the selected YAML schema, ingest the document,
    poll for completion, and download the extractions. Each run is stored as a
    submission so the extracted data can be tracked by job.
    """
    st.header("Upload & Process Billing Documents")

    st.write(
        """
        This page lets you upload your own billing document (PDF, JPG or PNG), or select one of the built-in sample documents to try out.
        Once a document is provided, it will be processed using the selected schema. The system will extract relevant financial and billing data from your unstructured document using GroundX's extraction pipeline.
        
        *Supported file types:* PDF, JPG, PNG  
        *Steps performed:*
        1. Document upload or sample selection
        2. Document validation
        3. Schema selection for data extraction
        4. Extraction and preview of results

        **Important Note:** This will work with the existing documents, but may not 
        work with new documents because the schema is used may not match 
        the new document.
        """
    )

    selected_yaml = st.session_state.get("selected_yaml_file", "simple.yaml")
    file_name = os.path.splitext(selected_yaml)[0]
    st.caption(f"Using extraction schema: **{selected_yaml}**")

    _render_schema_preview(selected_yaml)
    _render_sample_selector()

    uploaded_file = _resolve_document()
    if uploaded_file is None:
        st.info("Please upload a billing document (PDF, JPG, PNG) or select a sample.")
        return

    client = BillingClient()
    is_valid, message = client.validate_uploaded_file(uploaded_file)
    if not is_valid:
        st.error(message)
        return

    st.session_state.uploaded_file = uploaded_file

    _render_document_preview(uploaded_file)

    processor = DocumentProcessor(file_name=file_name)
    st.json(processor.get_file_details(uploaded_file))

    if not processor.is_ready:
        st.error(
            "GroundX is not configured, so documents cannot be processed. "
            f"Details: {processor.init_error}"
        )
        return

    if not st.button("Process Document"):
        return

    # Run the pipeline, surfacing each step as live status.
    with st.status("Processing document…", expanded=True) as status:
        def on_status(msg: str) -> None:
            status.write(msg)

        try:
            job = processor.process(uploaded_file, on_status=on_status)
        except DocumentProcessorError as exc:
            status.update(label="Processing failed", state="error")
            st.error(str(exc))
            # Record the failed attempt so it still shows up in job history.
            SubmissionStore().record(
                {
                    "filename": uploaded_file.name,
                    "file_size": uploaded_file.size,
                    "yaml_file": selected_yaml,
                    "status": "error",
                    "error": str(exc),
                }
            )
            return

        record = SubmissionStore().record(job)
        status.update(label="Extraction complete", state="complete")

    # Populate session state (mirrors the notebook's tracked identifiers).
    st.session_state.bucket_id = job["bucket_id"]
    st.session_state.workflow_id = job["workflow_id"]
    st.session_state.process_id = job["process_id"]
    st.session_state.document_id = job["document_id"]
    st.session_state.extracted_data = job["extracted_data"]
    st.session_state.submission_id = record["id"]

    st.success(
        f"Document processed and stored as submission `{record['id']}`. "
        "See **View Extracted Data** or **Job History**."
    )
    st.json(
        {
            "submission_id": record["id"],
            "bucket_id": job["bucket_id"],
            "workflow_id": job["workflow_id"],
            "process_id": job["process_id"],
            "document_id": job["document_id"],
        }
    )

"""
Document processing for the Billing Extraction UI.

This mirrors the flow in ``get_started.ipynb`` exactly:

    1. Initialize the GroundX client and the ExtractPromptManager
    2. Create (or reuse) a bucket
    3. Create a workflow from the prompt manager and set it as the account default
    4. Ingest the uploaded document
    5. Poll the processing status by ``process_id`` until complete
    6. Download the structured extractions by ``document_id``

The heavy lifting (prompt construction from the YAML schema) is delegated to
``manager.ExtractPromptManager`` — the same class the notebook uses — so the UI
and the notebook produce identical workflows.
"""

import os
import sys
import tempfile
import time
from typing import Any, Callable, Dict, Optional

# The notebook's prompt machinery (manager.py + prompts/) lives at the repo
# root. Pin the repo root to the front of sys.path so ``manager`` and
# ``prompts`` resolve there regardless of how Streamlit orders sys.path (it puts
# the script dir, apps/ui/, first). This file is
# apps/ui/components/document_processor.py, so the repo root is four levels up.
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Imported lazily-safe so the module still imports for local dev / tests where
# the extract extra isn't installed. Each stage is tracked separately so the UI
# can report *which* dependency is missing rather than a blanket message.
_SDK_ERROR: Optional[Exception] = None
_MANAGER_ERROR: Optional[Exception] = None

try:
    from groundx import Document, GroundX
    from groundx.extract import Logger, Source
except Exception as exc:  # pragma: no cover - depends on optional extras
    Document = GroundX = Logger = Source = None  # type: ignore
    _SDK_ERROR = exc

try:
    from manager import ExtractPromptManager
except Exception as exc:  # pragma: no cover - depends on repo layout
    ExtractPromptManager = None  # type: ignore
    _MANAGER_ERROR = exc

GROUNDX_AVAILABLE = _SDK_ERROR is None and _MANAGER_ERROR is None


# Terminal states reported by the ingest status endpoint.
_COMPLETE_STATES = {"complete", "completed"}
_ERROR_STATES = {"error", "errors", "failed", "cancelled", "canceled"}

StatusCallback = Callable[[str], None]


class DocumentProcessorError(RuntimeError):
    """Raised when the extraction pipeline cannot be run or fails."""


class DocumentProcessor:
    """Runs the GroundX extraction pipeline described in ``get_started.ipynb``."""

    def __init__(
        self,
        prompts_dir: str = "prompts",
        file_name: str = "simple",
        bucket_name: str = "workflow-test",
    ):
        """Initialize the GroundX client and prompt manager.

        Args:
            prompts_dir: Directory holding the extraction schema YAML files
                (the same ``cache_path`` the notebook uses).
            file_name: Schema/workflow name to load, without the ``.yaml``
                suffix (the notebook default is ``"simple"``).
            bucket_name: Bucket to ingest documents into (created if missing).
        """
        self.prompts_dir = prompts_dir
        self.file_name = file_name
        self.bucket_name = bucket_name

        self.gx_client = None
        self.prompt_manager = None
        self._init_error: Optional[str] = None

        if _SDK_ERROR is not None:
            self._init_error = (
                "The 'groundx[extract]' package is not available "
                f"(install groundx[extract]): {_SDK_ERROR}"
            )
            return
        if _MANAGER_ERROR is not None:
            self._init_error = (
                "Could not import the extraction prompt machinery "
                "(manager.py / prompts package). Ensure they are on the "
                f"Python path: {_MANAGER_ERROR}"
            )
            return

        api_key = os.getenv("GROUNDX_API_KEY")
        base_url = os.getenv("GROUNDX_BASE_URL")
        if not api_key:
            self._init_error = "GROUNDX_API_KEY environment variable is not set."
            return

        try:
            # base_url is optional (SaaS default); the OpenShift deployment sets it.
            client_kwargs: Dict[str, Any] = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            self.gx_client = GroundX(**client_kwargs)

            logger = Logger(name="billing-ui", level="info")
            self.prompt_manager = ExtractPromptManager(
                cache_source=Source(logger=logger, cache_path=self.prompts_dir),
                config_source=Source(logger=logger, cache_path=self.prompts_dir),
                logger=logger,
                default_file_name=self.file_name,
                default_workflow_id=self.file_name,
                gx_client=self.gx_client,
            )
        except Exception as exc:  # pragma: no cover - network/credential dependent
            self._init_error = f"Could not initialize GroundX client: {exc}"
            self.gx_client = None
            self.prompt_manager = None

    # -- readiness ---------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """True when the client and prompt manager are usable."""
        return self.gx_client is not None and self.prompt_manager is not None

    @property
    def init_error(self) -> Optional[str]:
        """Human-readable reason the processor could not initialize, if any."""
        return self._init_error

    def get_file_details(self, uploaded_file) -> Dict[str, str]:
        """Return metadata about the uploaded file."""
        return {
            "Filename": uploaded_file.name,
            "FileSize": f"{uploaded_file.size} bytes",
        }

    # -- pipeline steps (mirroring the notebook cells) ---------------------

    def ensure_bucket(self) -> int:
        """Create the working bucket, reusing an existing one with the same name."""
        # Reuse an existing bucket so repeated runs don't pile up duplicates.
        try:
            existing = self.gx_client.buckets.list()
            for bucket in getattr(existing, "buckets", []) or []:
                if bucket.name == self.bucket_name:
                    return bucket.bucket_id
        except Exception:
            # Listing is best-effort; fall through to create.
            pass

        res = self.gx_client.buckets.create(name=self.bucket_name)
        if not res.bucket:
            raise DocumentProcessorError(f"Failed to create bucket: {res}")
        return res.bucket.bucket_id

    def ensure_workflow(self, set_as_account_default: bool = True) -> str:
        """Create the extraction workflow from the prompt manager (notebook step)."""
        res = self.gx_client.workflows.create(
            chunk_strategy="element",
            name=self.file_name,
            steps=self.prompt_manager.workflow_steps(file_name=self.file_name),
            extract=self.prompt_manager.workflow_extract_dict(file_name=self.file_name),
        )
        workflow_id = res.workflow.workflow_id

        if set_as_account_default:
            # Matches the notebook's "Assign to Account as the Default Prompt" step.
            self.gx_client.workflows.add_to_account(workflow_id=workflow_id)

        return workflow_id

    def ingest_file(
        self,
        file_path: str,
        bucket_id: int,
        file_name: Optional[str] = None,
    ) -> str:
        """Ingest a local file into the bucket, returning the process_id.

        ``file_name`` overrides the on-disk basename so GroundX records the
        original upload name instead of a temp path like ``tmpXXXX.pdf``.
        """
        doc_kwargs: Dict[str, Any] = {
            "bucket_id": bucket_id,
            "file_path": file_path,
        }
        if file_name:
            doc_kwargs["file_name"] = file_name
        res = self.gx_client.ingest(documents=[Document(**doc_kwargs)])
        return res.ingest.process_id

    def wait_for_completion(
        self,
        process_id: str,
        on_status: Optional[StatusCallback] = None,
        poll_interval: float = 5.0,
        timeout: float = 900.0,
    ) -> str:
        """Poll ``get_processing_status_by_id`` until complete; return document_id.

        Mirrors the notebook's status-check cell but loops until the job reaches
        a terminal state instead of requiring a manual re-run.
        """
        deadline = time.monotonic() + timeout
        last_status: Optional[str] = None

        while True:
            res = self.gx_client.documents.get_processing_status_by_id(
                process_id=process_id,
            )
            status = (res.ingest.status or "").lower()
            document_id = self._document_id_from_status(res)

            if status != last_status and on_status is not None:
                on_status(status)
                last_status = status

            if status in _COMPLETE_STATES:
                if not document_id:
                    raise DocumentProcessorError(
                        "Processing completed but no document_id was returned."
                    )
                return document_id

            if status in _ERROR_STATES:
                raise DocumentProcessorError(
                    f"Document processing failed with status '{status}'."
                )

            if time.monotonic() >= deadline:
                raise DocumentProcessorError(
                    f"Timed out waiting for processing (last status: '{status}')."
                )

            time.sleep(poll_interval)

    @staticmethod
    def _document_id_from_status(res) -> Optional[str]:
        """Extract the document_id from an ingest status response (notebook logic)."""
        progress = getattr(res.ingest, "progress", None)
        if not progress:
            return None
        for phase in (progress.complete, progress.processing):
            if phase and phase.documents:
                return phase.documents[0].document_id
        return None

    def download_extract(self, document_id: str) -> Dict[str, Any]:
        """Download the structured extraction JSON for a document (notebook step)."""
        return self.gx_client.documents.get_extract(document_id=document_id)

    @staticmethod
    def extract_has_values(data: Any) -> bool:
        """True when ``data`` contains at least one non-empty leaf value.

        GroundX returns a schema skeleton filled with ``null`` / ``""`` when
        the layout/extract LLM calls fail (e.g. invalid ``GROUNDX_AGENT_API_KEY``).
        Treating that as success is why the UI previously showed all-null data.
        """
        if isinstance(data, dict):
            return any(DocumentProcessor.extract_has_values(v) for v in data.values())
        if isinstance(data, list):
            return any(DocumentProcessor.extract_has_values(v) for v in data)
        if data is None:
            return False
        if isinstance(data, str):
            return bool(data.strip())
        return True

    def _validate_extract(self, document_id: str, extracted_data: Any) -> None:
        """Raise if the extract payload is an empty schema skeleton."""
        if self.extract_has_values(extracted_data):
            return

        extracted_flag = None
        try:
            detail = self.gx_client.documents.get(document_id=document_id)
            doc = getattr(detail, "document", detail)
            extracted_flag = getattr(doc, "extracted", None)
        except Exception:
            pass

        raise DocumentProcessorError(
            "Processing finished but no field values were extracted "
            f"(document_id={document_id}, extracted={extracted_flag}). "
            "GroundX returned an empty schema (all null/blank). Common causes: "
            "invalid GROUNDX_AGENT_API_KEY (LLM calls return 401), or the "
            "uploaded file has no readable content. Check summary-client / "
            "extract-agent logs, then re-process after fixing the agent key."
        )

    # -- orchestration -----------------------------------------------------

    def process(
        self,
        uploaded_file,
        on_status: Optional[StatusCallback] = None,
        set_as_account_default: bool = True,
    ) -> Dict[str, Any]:
        """Run the end-to-end pipeline for an uploaded file.

        Returns a job record containing the GroundX identifiers and the
        extracted data. Raises :class:`DocumentProcessorError` on failure.
        """
        if not self.is_ready:
            raise DocumentProcessorError(
                self._init_error or "DocumentProcessor is not initialized."
            )

        def emit(msg: str) -> None:
            if on_status is not None:
                on_status(msg)

        # Persist the upload to a temp file so GroundX can read it by path.
        # Keep the original basename so GroundX metadata matches the upload.
        suffix = os.path.splitext(uploaded_file.name)[1] or ""
        tmp_dir = tempfile.mkdtemp(prefix="billing-upload-")
        tmp_path = os.path.join(tmp_dir, os.path.basename(uploaded_file.name))
        try:
            with open(tmp_path, "wb") as tmp:
                tmp.write(uploaded_file.getvalue())

            emit("Creating bucket…")
            bucket_id = self.ensure_bucket()

            emit("Creating extraction workflow…")
            workflow_id = self.ensure_workflow(
                set_as_account_default=set_as_account_default
            )

            emit("Ingesting document…")
            process_id = self.ingest_file(
                tmp_path, bucket_id, file_name=uploaded_file.name
            )

            emit("Processing document…")
            document_id = self.wait_for_completion(
                process_id, on_status=lambda s: emit(f"Status: {s}")
            )

            emit("Downloading extractions…")
            extracted_data = self.download_extract(document_id)
            self._validate_extract(document_id, extracted_data)

            return {
                "filename": uploaded_file.name,
                "file_size": uploaded_file.size,
                "yaml_file": f"{self.file_name}.yaml",
                "bucket_id": bucket_id,
                "workflow_id": workflow_id,
                "process_id": process_id,
                "document_id": document_id,
                "extracted_data": extracted_data,
            }
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass

"""Sample billing documents from ``test-docs/`` for one-click upload selection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_TEST_DOCS_DIR = os.path.join(_REPO_ROOT, "test-docs")


@dataclass(frozen=True)
class SampleDocInfo:
    """Catalog entry for a sample document shown on the upload page."""

    label: str
    filename: str

    @property
    def path(self) -> str:
        return os.path.join(_TEST_DOCS_DIR, self.filename)

    def exists(self) -> bool:
        return os.path.isfile(self.path)


# Friendly labels for the three documents in test-docs/
SAMPLE_DOCS: List[SampleDocInfo] = [
    SampleDocInfo("AT&T Wireless", "att-wireless-sample-bill-guide1.pdf"),
    SampleDocInfo("CA OAG AT&T Cramming", "ca-oag-att-cramming-sample-bills.pdf"),
    SampleDocInfo("T-Mobile", "t-mobile.pdf"),
]


class SampleDocument:
    """File-like wrapper matching Streamlit ``UploadedFile`` for the pipeline.

    Exposes ``name``, ``size``, and ``getvalue()`` so
    :class:`~apps.ui.components.document_processor.DocumentProcessor` and
    :class:`~apps.ui.components.client.BillingClient` can treat samples the
    same as user uploads.
    """

    def __init__(self, path: str):
        self._path = path
        self.name = os.path.basename(path)
        self._bytes: Optional[bytes] = None

    @property
    def size(self) -> int:
        return os.path.getsize(self._path)

    def getvalue(self) -> bytes:
        if self._bytes is None:
            with open(self._path, "rb") as f:
                self._bytes = f.read()
        return self._bytes


def load_sample(filename: str) -> Optional[SampleDocument]:
    """Load a sample by filename from ``test-docs/``, or ``None`` if missing."""
    path = os.path.join(_TEST_DOCS_DIR, filename)
    if not os.path.isfile(path):
        return None
    return SampleDocument(path)


def available_samples() -> List[SampleDocInfo]:
    """Return catalog entries whose files are present on disk."""
    return [doc for doc in SAMPLE_DOCS if doc.exists()]

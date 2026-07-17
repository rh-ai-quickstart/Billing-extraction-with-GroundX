"""
Persistent store for extraction submissions (jobs).

Each time a document is processed we record the job — its GroundX identifiers
and the extracted data returned by the workflow — so the data extracted by a
job can be tracked and revisited later.

Records are written as one JSON file per submission under ``SUBMISSIONS_DIR``
(default ``submissions/`` locally, ``/app/data/submissions`` in the container),
which is backed by a persistent volume in the OpenShift deployment.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class SubmissionStore:
    """File-backed store of extraction submissions."""

    def __init__(self, base_dir: Optional[str] = None):
        """Initialize the store, creating the submissions directory if needed."""
        self.base_dir = base_dir or os.getenv("SUBMISSIONS_DIR", "submissions")
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, submission_id: str) -> str:
        return os.path.join(self.base_dir, f"{submission_id}.json")

    def record(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Persist a completed job and return the stored record (with id/timestamp).

        Args:
            job: The job record produced by ``DocumentProcessor.process`` (or a
                partial record for a failed run). ``id`` and ``created_at`` are
                added if absent.
        """
        record = dict(job)
        record.setdefault("id", uuid.uuid4().hex[:12])
        record.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        record.setdefault("status", "complete")

        with open(self._path(record["id"]), "w") as f:
            json.dump(record, f, indent=2, default=str)
        return record

    def list(self) -> List[Dict[str, Any]]:
        """Return all submissions, newest first."""
        records: List[Dict[str, Any]] = []
        if not os.path.isdir(self.base_dir):
            return records
        for name in os.listdir(self.base_dir):
            if not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.base_dir, name)) as f:
                    records.append(json.load(f))
            except (OSError, json.JSONDecodeError):
                continue
        records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        return records

    def get(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Load a single submission by id, or None if it doesn't exist."""
        try:
            with open(self._path(submission_id)) as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

"""
Infrastructure readiness checks for the Billing Extraction demo.

Validates the local app dependencies and GroundX connectivity required to run
Upload & Process — without requiring cluster-admin access from the UI pod.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from apps.ui.components.document_processor import DocumentProcessor, GROUNDX_AVAILABLE
from apps.ui.components.yaml_manager import YAMLManager


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single infrastructure check."""

    name: str
    ok: bool
    detail: str
    required: bool = True


class InfraChecker:
    """Runs readiness checks needed to demo billing extraction."""

    def __init__(
        self,
        prompts_dir: str = "prompts",
        submissions_dir: Optional[str] = None,
        request_timeout: float = 10.0,
    ):
        self.prompts_dir = prompts_dir
        self.submissions_dir = submissions_dir or os.getenv(
            "SUBMISSIONS_DIR", "submissions"
        )
        self.request_timeout = request_timeout

    def run_all(self) -> List[CheckResult]:
        """Execute every check and return results in display order."""
        results: List[CheckResult] = []
        results.append(self.check_groundx_sdk())
        results.append(self.check_api_key())
        results.append(self.check_base_url_configured())
        results.append(self.check_prompts_directory())
        results.append(self.check_default_schema())
        results.append(self.check_submissions_writable())
        results.append(self.check_groundx_http())
        results.append(self.check_groundx_api())
        return results

    def check_groundx_sdk(self) -> CheckResult:
        """Verify groundx[extract] and the prompt manager import cleanly."""
        if GROUNDX_AVAILABLE:
            return CheckResult(
                name="GroundX Python SDK",
                ok=True,
                detail="groundx[extract] and ExtractPromptManager are importable.",
            )
        processor = DocumentProcessor()
        return CheckResult(
            name="GroundX Python SDK",
            ok=False,
            detail=processor.init_error
            or "groundx[extract] / prompt manager is not available.",
        )

    def check_api_key(self) -> CheckResult:
        """Require GROUNDX_API_KEY to be set (value is never shown)."""
        key = os.getenv("GROUNDX_API_KEY", "").strip()
        if key:
            return CheckResult(
                name="GROUNDX_API_KEY",
                ok=True,
                detail="Environment variable is set.",
            )
        return CheckResult(
            name="GROUNDX_API_KEY",
            ok=False,
            detail="GROUNDX_API_KEY is missing. Set it from the GroundX admin API key "
            "(GROUNDX_ADMIN_API_KEY in the workloads secret).",
        )

    def check_base_url_configured(self) -> CheckResult:
        """Report GROUNDX_BASE_URL; optional for SaaS, expected on OpenShift."""
        base_url = os.getenv("GROUNDX_BASE_URL", "").strip()
        if base_url:
            return CheckResult(
                name="GROUNDX_BASE_URL",
                ok=True,
                detail=f"Configured: {base_url}",
                required=False,
            )
        return CheckResult(
            name="GROUNDX_BASE_URL",
            ok=True,
            detail="Not set — the SDK will use the GroundX SaaS default. "
            "On OpenShift this should point at the in-cluster GroundX service "
            "(…/api).",
            required=False,
        )

    def check_prompts_directory(self) -> CheckResult:
        """Confirm the prompts directory exists and is readable."""
        if os.path.isdir(self.prompts_dir):
            return CheckResult(
                name="Prompts directory",
                ok=True,
                detail=f"Found `{self.prompts_dir}/`.",
            )
        return CheckResult(
            name="Prompts directory",
            ok=False,
            detail=f"`{self.prompts_dir}/` is missing. Run the app from the "
            "repository root (or ensure prompts are baked into the image).",
        )

    def check_default_schema(self) -> CheckResult:
        """Ensure at least one extraction schema YAML loads."""
        manager = YAMLManager(yaml_dir=self.prompts_dir)
        content = manager.load_content("simple.yaml")
        if content and isinstance(content, dict):
            fields = (content.get("statement") or {}).get("fields") or {}
            return CheckResult(
                name="Default schema (simple.yaml)",
                ok=True,
                detail=f"Loaded with {len(fields)} field(s).",
            )
        return CheckResult(
            name="Default schema (simple.yaml)",
            ok=False,
            detail="Could not load `prompts/simple.yaml`. Restore the default "
            "schema from the repo.",
        )

    def check_submissions_writable(self) -> CheckResult:
        """Verify the submissions directory can be created and written to."""
        try:
            os.makedirs(self.submissions_dir, exist_ok=True)
            fd, path = tempfile.mkstemp(prefix=".infra-", dir=self.submissions_dir)
            os.close(fd)
            os.unlink(path)
            return CheckResult(
                name="Submissions storage",
                ok=True,
                detail=f"Writable at `{self.submissions_dir}`.",
            )
        except OSError as exc:
            return CheckResult(
                name="Submissions storage",
                ok=False,
                detail=f"Cannot write to `{self.submissions_dir}`: {exc}",
            )

    def check_groundx_http(self) -> CheckResult:
        """Probe GROUNDX_BASE_URL over HTTP when configured."""
        base_url = os.getenv("GROUNDX_BASE_URL", "").strip()
        if not base_url:
            return CheckResult(
                name="GroundX HTTP reachability",
                ok=True,
                detail="Skipped — GROUNDX_BASE_URL is not set.",
                required=False,
            )

        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            return CheckResult(
                name="GroundX HTTP reachability",
                ok=False,
                detail=f"GROUNDX_BASE_URL looks invalid: {base_url}",
            )

        # Hit the configured base; GroundX may return 401/404 without a key —
        # any TCP-level response means the service is reachable.
        try:
            status = self._http_status(base_url)
            return CheckResult(
                name="GroundX HTTP reachability",
                ok=True,
                detail=f"Reached {base_url} (HTTP {status}).",
            )
        except Exception as exc:
            return CheckResult(
                name="GroundX HTTP reachability",
                ok=False,
                detail=f"Could not reach {base_url}: {exc}",
            )

    def _http_status(self, url: str) -> int:
        """Return an HTTP status code for ``url`` (errors with a code still count)."""
        request = Request(url, method="GET")
        try:
            with urlopen(request, timeout=self.request_timeout) as response:
                return int(response.status)
        except HTTPError as exc:
            return int(exc.code)
        except URLError as exc:
            raise RuntimeError(exc.reason) from exc

    def check_groundx_api(self) -> CheckResult:
        """Authenticate and list buckets via the GroundX SDK."""
        processor = DocumentProcessor()
        if not processor.is_ready:
            return CheckResult(
                name="GroundX API (list buckets)",
                ok=False,
                detail=processor.init_error
                or "GroundX client could not be initialized.",
            )

        try:
            result = processor.gx_client.buckets.list()
            buckets = list(getattr(result, "buckets", None) or [])
            return CheckResult(
                name="GroundX API (list buckets)",
                ok=True,
                detail=f"Authenticated successfully; {len(buckets)} bucket(s) visible.",
            )
        except Exception as exc:
            return CheckResult(
                name="GroundX API (list buckets)",
                ok=False,
                detail=f"API call failed: {exc}. Check GROUNDX_API_KEY, "
                "GROUNDX_BASE_URL, and that GroundX workloads are running.",
            )

    @staticmethod
    def summary(results: List[CheckResult]) -> tuple[bool, int, int]:
        """Return (all_required_ok, required_passed, required_total)."""
        required = [r for r in results if r.required]
        passed = sum(1 for r in required if r.ok)
        return passed == len(required), passed, len(required)

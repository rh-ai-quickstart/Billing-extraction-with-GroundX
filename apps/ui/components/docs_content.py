"""Documentation copy for the Billing Extraction Streamlit UI."""

WHAT_THIS_APP_IS = """
This is a **billing data extraction** demo that runs on OpenShift AI.

You upload a utility bill or invoice (PDF or image). The app sends it through
[GroundX](https://www.eyelevel.ai/) with an extraction schema you choose, then
shows the result as structured fields — account number, amount due, due date,
and so on based on the schema you choose.

The UI uses the **same GroundX pipeline** as the project's Jupyter notebook
(`get_started.ipynb`). If the notebook extracts a field correctly, this app
should extract it the same way.
"""

WHAT_GROUNDX_DOES = """
GroundX (from EyeLevel) turns unstructured documents into structured data
without relying on brittle OCR + regex alone.

For each upload it roughly does the following:

1. **Layout understanding** — computer vision preserves tables, labels, and
   nested regions so context is not lost when the page is read.
2. **Workflow + schema** — your YAML schema (for example `simple.yaml`) defines
   which fields to pull and how to describe them to the extract model.
3. **Ingest** — the file is stored in a GroundX bucket and processed as a
   document job.
4. **Extract** — GroundX returns a JSON object shaped like your schema, with
   values filled from the bill.

The app does not invent fields. It only asks GroundX for what the selected
schema defines, then displays and stores that JSON.
"""

WHAT_TO_EXPECT = """
### Happy path

1. Run **Infrastructure Check** so credentials and API connectivity look good.
2. On **Upload & Process**, upload a clear PDF/JPG/PNG bill and start the run
   (uses `simple.yaml` by default).
3. Wait while status messages move through bucket → workflow → ingest → poll →
   extract (often under a minute; larger scans take longer).
4. Open **View Extracted Data** for the latest JSON and a field table.
5. Use **Job History** later to reopen any past run.

### What a good result looks like

You should see real values for the schema fields, for example:

| Field | Example shape |
|-------|----------------|
| Account Number | Non-empty string |
| Amount Due | Number |
| Due Date | `YYYY-mm-dd` |
| Provider Name | Company name |
| Service Address | Address text |

### What a bad / empty result means

If every field is `null` or blank, ingest finished but the extract step did not
populate values. Common causes:

- Invalid or placeholder `GROUNDX_AGENT_API_KEY` (layout/extract LLM calls fail)
- Unreadable scan (blank page, extreme blur, wrong file)
- Schema that does not match the document type

Fix the agent key / document / schema, then **re-process** — do not treat an
all-null payload as a successful extraction.

### Supported inputs

- **Formats:** PDF, JPG, JPEG, PNG
- **Size:** up to 50 MB
- **Schemas:** YAML under `prompts/` (same files the notebook uses)
"""

HOW_TO_NAVIGATE = """
| Tab | Purpose |
|-----|---------|
| **Documentation** | This page — orientation for the demo |
| **Infrastructure Check** | Validate env vars, schemas, storage, and GroundX reachability |
| **Upload & Process** | Run a live extraction (schema: `simple.yaml`) |
| **View Extracted Data** | Inspect the latest result |
| **Job History** | Browse past submissions and their extracted JSON |
"""

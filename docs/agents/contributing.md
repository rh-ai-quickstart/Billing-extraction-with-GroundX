# Contributing

Before proposing a change, read the touched source, its callers, shared
helpers, and consumer. Keep the quickstart's supported flow in `README.md` and
`apps/ui/DETAIL_WALKTHROUGH.md` in view. Reuse its current components and
make the smallest change that protects the behavior.

The Streamlit entrypoint `apps/ui/streamlit_app.py` routes to
`apps/ui/views/upload.py`. That view calls
`apps/ui/components/document_processor.py`, which uses the GroundX Python SDK
and the existing `manager.py` `ExtractPromptManager` with `prompts/` YAML.
Trace changes through ingest, status polling, extract readback, and submission
storage. For deployment changes, inspect both `helm/billing-operators/` and
`helm/billing-workloads/`, their values, and the UI's mounted configuration.

Use existing walkthrough and Helm render evidence appropriate to the change.
Extend any existing relevant check before adding one; add a new check only for
a consequential regression that cannot otherwise be shown. Do not introduce
a test framework for documentation or guidance changes.

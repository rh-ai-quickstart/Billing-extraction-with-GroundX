"""
Views package for the Billing Extraction Streamlit UI.
Each module exposes a page function rendered by the main app.

Named `views` (not `pages`) so Streamlit does not auto-register these as
multipage routes, which would break `/_stcore/*` under paths like `/upload`.
"""

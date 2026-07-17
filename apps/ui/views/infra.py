import streamlit as st

from apps.ui.components.infra_checker import InfraChecker


def infra_page():
    """Check that dependencies and GroundX connectivity are ready for the demo."""
    st.header("Infrastructure Check")
    st.markdown(
        "Verify that everything needed to run the billing extraction demo is "
        "present — Python packages, environment variables, extraction schemas, "
        "writable job storage, and GroundX API connectivity."
    )

    if st.button("Run checks", type="primary"):
        st.session_state["infra_checks_ran"] = True

    if not st.session_state.get("infra_checks_ran"):
        st.info("Click **Run checks** to validate the demo environment.")
        return

    checker = InfraChecker()
    with st.spinner("Running infrastructure checks…"):
        results = checker.run_all()

    all_ok, passed, total = InfraChecker.summary(results)
    if all_ok:
        st.success(f"Ready for the demo — {passed}/{total} required checks passed.")
    else:
        st.error(
            f"Not ready — {passed}/{total} required checks passed. "
            "Fix the failing items below before uploading a document."
        )

    for result in results:
        icon = "✅" if result.ok else "❌"
        label = result.name
        if not result.required:
            label = f"{label} (optional)"
        with st.expander(f"{icon} {label}", expanded=not result.ok):
            st.markdown(result.detail)

    st.divider()
    st.markdown(
        "**Next step:** if all required checks pass, open **Upload & Process** "
        "and run a sample bill against `simple.yaml`."
    )

"""
streamlit_app.py — Streamlit frontend for the RFP Agent.

Phase 0: Shell with sidebar, session management, and a basic chat area.
The app calls the FastAPI backend over HTTP using httpx.
Streamlit never touches the DB, vector store, or LLM directly.
"""
import httpx
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RFP Agent — Azentio",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Backend URL ───────────────────────────────────────────────────────────────
import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


# ── Helpers ───────────────────────────────────────────────────────────────────

def api_get(path: str) -> dict | list | None:
    """GET from the backend. Returns parsed JSON or None on error."""
    try:
        r = httpx.get(f"{BACKEND_URL}{path}", timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"Backend error: {exc}")
        return None


def api_post(path: str, json: dict | None = None) -> dict | None:
    """POST to the backend. Returns parsed JSON or None on error."""
    try:
        r = httpx.post(f"{BACKEND_URL}{path}", json=json or {}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        st.error(f"Backend error: {exc}")
        return None


# ── Session state defaults ────────────────────────────────────────────────────
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "active_session_name" not in st.session_state:
    st.session_state.active_session_name = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📋 RFP Agent")
    st.caption("Azentio Islamic Banking · SAMPLE DATA ONLY")
    st.divider()

    # Health check
    health = api_get("/health")
    if health and health.get("status") == "ok":
        st.success(f"✅ Backend connected  \n`{health['fast_model']}` / `{health['draft_model']}`")
    else:
        st.error("❌ Backend not reachable — is it running?")
        st.info("Run: `uvicorn backend.app.main:app --reload`")

    st.divider()

    # ── New session ───────────────────────────────────────────────────────────
    with st.expander("➕ New Session", expanded=False):
        new_name = st.text_input("Session name", placeholder="e.g. Al-Baraka RFP 2024")
        if st.button("Create Session", use_container_width=True):
            if new_name.strip():
                result = api_post("/sessions", {"name": new_name.strip()})
                if result:
                    st.session_state.active_session_id = result["id"]
                    st.session_state.active_session_name = result["name"]
                    st.success(f"Created session: **{result['name']}**")
                    st.rerun()
            else:
                st.warning("Please enter a session name.")

    st.divider()

    # ── Session list ──────────────────────────────────────────────────────────
    st.subheader("Sessions")
    sessions = api_get("/sessions") or []
    if not sessions:
        st.caption("No sessions yet. Create one above.")
    for s in sessions:
        label = f"{'▶ ' if s['id'] == st.session_state.active_session_id else ''}{s['name']}"
        if st.button(label, key=f"sess_{s['id']}", use_container_width=True):
            st.session_state.active_session_id = s["id"]
            st.session_state.active_session_name = s["name"]
            st.rerun()

    st.divider()

    # ── KB status ─────────────────────────────────────────────────────────────
    st.subheader("Knowledge Base")
    kb_docs = api_get("/kb/documents") or []
    if kb_docs:
        st.metric("Documents", len(kb_docs))
        by_type: dict[str, int] = {}
        for d in kb_docs:
            by_type[d["source_type"]] = by_type.get(d["source_type"], 0) + 1
        for stype, count in by_type.items():
            st.caption(f"  {stype}: {count}")
    else:
        st.caption("KB empty — run `python scripts/ingest_kb.py`")


# ── Main area ─────────────────────────────────────────────────────────────────
if st.session_state.active_session_id is None:
    st.title("Welcome to RFP Agent")
    st.markdown(
        """
        **Getting started:**
        1. Create a new session in the sidebar.
        2. Upload an RFP (PDF or DOCX).
        3. Click **Analyze** — the agent will extract questions and draft answers.
        4. Review answers, approve them, and export the response.

        > ⚠️ All data used in this system is **synthetic / mock (SAMPLE)**.
        > No real customer or prospect data is processed.
        """
    )
    st.info("👈 Create or select a session from the sidebar to begin.")
    st.stop()

# ── Active session ────────────────────────────────────────────────────────────
st.title(f"📋 {st.session_state.active_session_name}")
st.caption(f"Session ID: {st.session_state.active_session_id}")

# Tabs — stubs for Phase 0; filled in later phases
tab_chat, tab_questions, tab_clarifications, tab_format, tab_export = st.tabs([
    "💬 Chat", "❓ Questions", "📝 Clarifications", "📐 Format Rules", "📤 Export"
])

# ── Chat tab ──────────────────────────────────────────────────────────────────
with tab_chat:
    st.subheader("Chat with the RFP Agent")

    # Upload RFP
    with st.expander("📤 Upload RFP Document", expanded=True):
        uploaded = st.file_uploader(
            "Upload the RFP (PDF or DOCX)",
            type=["pdf", "docx"],
            key="rfp_upload",
        )
        if uploaded is not None:
            if st.button("Upload & Save", key="do_upload"):
                files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                try:
                    r = httpx.post(
                        f"{BACKEND_URL}/sessions/{st.session_state.active_session_id}/rfp",
                        files=files,
                        timeout=60,
                    )
                    r.raise_for_status()
                    doc = r.json()
                    st.success(f"Uploaded: **{doc['filename']}** (id={doc['id']})")
                except Exception as exc:
                    st.error(f"Upload failed: {exc}")

        if st.button("🔍 Analyze RFP", key="analyze_btn", help="Starts the analysis pipeline"):
            result = api_post(
                f"/sessions/{st.session_state.active_session_id}/analyze"
            )
            if result:
                st.info(result.get("message", "Analysis started."))

    st.divider()

    # Chat history
    messages = api_get(f"/sessions/{st.session_state.active_session_id}/messages") or []
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if user_input := st.chat_input("Ask the agent something..."):
        with st.chat_message("user"):
            st.markdown(user_input)
        result = api_post(
            f"/sessions/{st.session_state.active_session_id}/chat",
            {"content": user_input},
        )
        if result:
            with st.chat_message("assistant"):
                st.markdown(result["content"])

# ── Questions tab (Phase 0 stub) ──────────────────────────────────────────────
with tab_questions:
    st.subheader("Extracted Questions")
    questions = api_get(f"/sessions/{st.session_state.active_session_id}/questions") or []
    if not questions:
        st.info("No questions yet. Upload and analyze an RFP first.")
    else:
        approved = sum(1 for q in questions if q["status"] == "approved")
        pending = len(questions) - approved
        col1, col2, col3 = st.columns(3)
        col1.metric("Total", len(questions))
        col2.metric("✅ Approved", approved)
        col3.metric("⏳ Pending", pending)
        st.dataframe(
            [{
                "No.": q["number"],
                "Status": q["status"],
                "Category": q["category"],
                "Mandatory": "✓" if q["mandatory"] else "",
                "Question": q["text"][:120] + "..." if len(q["text"]) > 120 else q["text"],
            } for q in questions],
            use_container_width=True,
        )

# ── Clarifications tab (Phase 0 stub) ────────────────────────────────────────
with tab_clarifications:
    st.subheader("Clarification List")
    clarifs = api_get(
        f"/sessions/{st.session_state.active_session_id}/clarifications"
    ) or []
    if not clarifs:
        st.info("No clarifications yet.")
    else:
        for c in clarifs:
            with st.expander(f"[{c['status'].upper()}] {c['text'][:80]}"):
                st.write(c["text"])
                st.caption(f"Reason: {c['reason']}")

# ── Format Rules tab (Phase 0 stub) ──────────────────────────────────────────
with tab_format:
    st.subheader("Format Rules")
    rules = api_get(f"/sessions/{st.session_state.active_session_id}/format-rules")
    if rules is None:
        st.info("No format rules extracted yet. Analyze an RFP first.")
    else:
        import json
        st.json(json.loads(rules["rules_json"]))
        st.caption(f"Confirmed by SE: {'✅' if rules['confirmed_by_se'] else '❌'}")

# ── Export tab (Phase 0 stub) ─────────────────────────────────────────────────
with tab_export:
    st.subheader("Export Response")
    st.info("Export is available in Phase 5 after all answers are approved.")
    if st.button("📤 Export (stub)", disabled=True):
        pass

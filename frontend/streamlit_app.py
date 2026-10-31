"""
streamlit_app.py — Streamlit frontend for the RFP Agent.

Phase 0: Shell with sidebar, session management, and a basic chat area.
The app calls the FastAPI backend over HTTP using httpx.
Streamlit never touches the DB, vector store, or LLM directly.
"""

import os

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
        st.metric("Documents Ingested", len(kb_docs))
        by_type: dict[str, int] = {}
        total_chunks = 0
        for d in kb_docs:
            by_type[d["source_type"]] = by_type.get(d["source_type"], 0) + 1
            total_chunks += d.get("chunk_count", 0)
        st.caption(f"**Total chunks indexed:** {total_chunks}")
        for stype, count in by_type.items():
            st.caption(f"• `{stype}`: {count} docs")

        with st.expander("📄 View Ingested Docs", expanded=False):
            for d in kb_docs:
                redacted_flag = "🔒 [REDACTED]" if d.get("redacted") else "📗 [CLEAN]"
                st.markdown(
                    f"**{d['document_name']}**  \n"
                    f"_{d['source_type']}_ · v{d.get('product_version', '3.0.0')} · {redacted_flag} ({d.get('chunk_count', 0)} chunks)"
                )
    else:
        st.caption("KB empty — click Ingest KB below.")

    if st.button("🔄 Ingest / Refresh KB", use_container_width=True):
        with st.spinner("Ingesting synthetic knowledge base..."):
            res = api_post("/kb/ingest")
            if res:
                st.success(res.get("message", "Ingestion completed!"))
                st.rerun()


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
tab_chat, tab_questions, tab_clarifications, tab_format, tab_export = st.tabs(
    ["💬 Chat", "❓ Questions", "📝 Clarifications", "📐 Format Rules", "📤 Export"]
)

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
            with st.spinner(
                "Analyzing RFP structure, extracting questions, and detecting format rules..."
            ):
                result = api_post(f"/sessions/{st.session_state.active_session_id}/analyze")
                if result:
                    st.success(result.get("message", "Analysis complete!"))
                    st.rerun()

    st.divider()

    # Chat history
    st.markdown("#### Conversational Workspace")
    messages = api_get(f"/sessions/{st.session_state.active_session_id}/messages") or []
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Quick Action Suggestion Chips
    st.markdown("##### 💡 Quick SE Commands")
    chip_cols = st.columns(4)
    suggested_prompt = None
    if chip_cols[0].button("📋 List All Questions", key="chip_list", use_container_width=True):
        suggested_prompt = "List all questions"
    if chip_cols[1].button("🚩 Flagged to Pricing", key="chip_pricing", use_container_width=True):
        suggested_prompt = "List questions flagged to Pricing"
    if chip_cols[2].button("🔍 Search KB: Murabaha", key="chip_search", use_container_width=True):
        suggested_prompt = "Search KB: Murabaha early settlement rebate"
    if chip_cols[3].button("📊 RFP Status Summary", key="chip_summary", use_container_width=True):
        suggested_prompt = "Show overall RFP summary"

    # Input handling
    user_input = st.chat_input("Ask a question, request an answer rewrite, or inject an SE fact...")
    active_prompt = user_input or suggested_prompt

    if active_prompt:
        with st.chat_message("user"):
            st.markdown(active_prompt)
        with st.spinner("RFP Agent thinking & executing tools..."):
            result = api_post(
                f"/sessions/{st.session_state.active_session_id}/chat",
                {"content": active_prompt},
            )
            if result:
                st.rerun()

# ── Questions tab ─────────────────────────────────────────────────────────────
with tab_questions:
    st.subheader("Extracted Requirements & Questions")
    questions = api_get(f"/sessions/{st.session_state.active_session_id}/questions") or []
    if not questions:
        st.info(
            "No questions extracted yet. Upload an RFP and click **🔍 Analyze RFP** in the Chat tab."
        )
    else:
        # Metrics row
        total_q = len(questions)
        flagged_q = sum(1 for q in questions if q["status"] == "flagged_owner")
        pending_q = sum(1 for q in questions if q["status"] == "pending")
        approved_q = sum(1 for q in questions if q["status"] == "approved")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Questions", total_q)
        c2.metric("🏷️ Flagged to Owner", flagged_q)
        c3.metric("⏳ Ready to Draft", pending_q)
        c4.metric("✅ Approved", approved_q)

        st.divider()

        # Filters
        f_col1, f_col2, f_col3 = st.columns(3)
        categories = ["All"] + sorted(list({q["category"] for q in questions if q.get("category")}))
        owners = ["All"] + sorted(list({q["owner"] for q in questions if q.get("owner")}))
        statuses = ["All"] + sorted(list({q["status"] for q in questions if q.get("status")}))

        sel_cat = f_col1.selectbox("Filter Category", categories)
        sel_owner = f_col2.selectbox("Filter Owner", owners)
        sel_status = f_col3.selectbox("Filter Status", statuses)

        filtered = questions
        if sel_cat != "All":
            filtered = [q for q in filtered if q.get("category") == sel_cat]
        if sel_owner != "All":
            filtered = [q for q in filtered if q.get("owner") == sel_owner]
        if sel_status != "All":
            filtered = [q for q in filtered if q.get("status") == sel_status]

        st.caption(f"Showing **{len(filtered)}** of {total_q} questions")

        table_data = []
        for q in filtered:
            status_badge = (
                "🏷️ Flagged"
                if q["status"] == "flagged_owner"
                else ("✅ Approved" if q["status"] == "approved" else "⏳ Pending")
            )
            owner_label = f"👤 {q['owner']}" if q.get("owner") else "—"
            table_data.append(
                {
                    "No.": q["number"],
                    "Category": q.get("category", "").upper(),
                    "Owner": owner_label,
                    "Status": status_badge,
                    "Mandatory": "★ Yes" if q["mandatory"] else "No",
                    "Question": q["text"],
                }
            )

        st.dataframe(
            table_data,
            use_container_width=True,
            column_config={
                "Question": st.column_config.TextColumn("Requirement / Question", width="large"),
            },
        )

        with st.expander("🔎 Question Inspector & Draft Review", expanded=True):
            q_nums = [q["number"] for q in filtered]
            if q_nums:
                chosen_num = st.selectbox("Select question to inspect and review draft:", q_nums)
                chosen = next((q for q in filtered if q["number"] == chosen_num), None)
                if chosen:
                    st.markdown(
                        f"### Requirement `{chosen['number']}` ({chosen.get('category', '').upper()})"
                    )
                    st.info(chosen["text"])

                    # Fetch active draft answer
                    ans = api_get(f"/questions/{chosen['id']}/answer")
                    if ans:
                        st.markdown("#### Draft Answer")
                        conf = ans.get("confidence", 0.0)
                        conf_col, status_col = st.columns([2, 1])
                        with conf_col:
                            st.progress(conf, text=f"Grounded Confidence Score: {int(conf * 100)}%")
                        with status_col:
                            st.caption(
                                f"Status: **{ans.get('status', 'draft').upper()}** (v{ans.get('version', 1)})"
                            )

                        # Staleness alerts
                        import json

                        stales = json.loads(ans.get("stale_warnings_json", "[]"))
                        for sw in stales:
                            st.warning(f"⚠️ **Staleness Notice:** {sw}")

                        # Editable draft text
                        edited_text = st.text_area(
                            "Review & Edit Draft (Human-in-the-Loop):",
                            value=ans.get("text", ""),
                            height=200,
                            key=f"edit_ans_{chosen['id']}_{ans.get('version', 1)}",
                        )

                        # Action buttons
                        btn_c1, btn_c2 = st.columns([1, 1])
                        with btn_c1:
                            if st.button("💾 Save Edits (New Version)", key=f"save_{chosen['id']}"):
                                patch_res = httpx.patch(
                                    f"{BACKEND_URL}/questions/{chosen['id']}/answer",
                                    json={"text": edited_text},
                                )
                                if patch_res.status_code == 200:
                                    st.success("Draft updated with new version!")
                                    st.rerun()
                        with btn_c2:
                            if ans.get("status") != "approved":
                                if st.button(
                                    "✅ Approve Answer", type="primary", key=f"appr_{chosen['id']}"
                                ):
                                    appr_res = httpx.post(
                                        f"{BACKEND_URL}/questions/{chosen['id']}/approve",
                                        json={"confirm": True},
                                    )
                                    if appr_res.status_code == 200:
                                        st.success("Answer approved by Sales Engineer!")
                                        st.rerun()
                            else:
                                st.success(f"Approved on {ans.get('approved_at', 'recently')}")

                        # Citations section
                        cites = json.loads(ans.get("citations_json", "[]"))
                        if cites:
                            st.markdown("##### Grounded Citations")
                            for idx, c in enumerate(cites):
                                with st.expander(
                                    f"📌 Citation [{c.get('chunk_id')}]: {c.get('document')}"
                                ):
                                    st.caption(f"Source Type: `{c.get('source_type')}`")
                                    st.markdown(f"> *{c.get('snippet')}*")
                        elif chosen.get("owner"):
                            st.info(
                                f"This question is assigned to the **{chosen['owner']}** department."
                            )
                        else:
                            st.caption("No knowledge base citations linked to this draft.")
                    else:
                        st.info("No draft answer generated yet. Run analysis to draft answers.")

# ── Clarifications tab ────────────────────────────────────────────────────────
with tab_clarifications:
    st.subheader("Clarification List (Low Confidence / Insufficient Sources)")
    clarifs = api_get(f"/sessions/{st.session_state.active_session_id}/clarifications") or []
    if not clarifs:
        st.success(
            "✅ No open clarifications! All questions either had grounded knowledge sources or were assigned to department owners."
        )
    else:
        st.warning(f"There are **{len(clarifs)}** items requiring Sales Engineer attention:")
        for c in clarifs:
            with st.expander(f"⚠️ [{c['status'].upper()}] {c['text'][:80]}"):
                st.markdown(f"**Question / Item:** {c['text']}")
                st.markdown(f"**Reason:** {c['reason']}")
                st.caption(f"Created: {c['created_at']}")


# ── Format Rules tab ──────────────────────────────────────────────────────────
with tab_format:
    st.subheader("Extracted Response Guidelines & Format Rules")
    rules_obj = api_get(f"/sessions/{st.session_state.active_session_id}/format-rules")
    if rules_obj is None:
        st.info("No format rules extracted yet. Upload an RFP and click **🔍 Analyze RFP** first.")
    else:
        import json

        rules_data = (
            json.loads(rules_obj["rules_json"])
            if isinstance(rules_obj["rules_json"], str)
            else rules_obj["rules_json"]
        )

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown(
                f"**Word Limit per Answer:** `{rules_data.get('word_limit', 'None specified')} words`"
            )
            st.markdown(f"**Numbering Scheme:** `{rules_data.get('numbering_scheme', 'exact')}`")
            st.markdown(
                f"**Section Headings Required:** `{'Yes' if rules_data.get('section_headings') else 'No'}`"
            )
        with col_r2:
            st.markdown(f"**File Naming Template:** `{rules_data.get('file_naming', 'Standard')}`")
            st.markdown(f"**Language & Tone:** `{rules_data.get('language', 'English')}`")
            st.markdown(
                f"**Compliance Matrix Required:** `{'Yes' if rules_data.get('compliance_matrix_required') else 'No'}`"
            )

        is_confirmed = rules_obj.get("confirmed_by_se", False)
        st.caption(
            f"Status: **{'Confirmed by Sales Engineer ✅' if is_confirmed else 'Pending SE Confirmation ⚠️'}**"
        )

        if not is_confirmed:
            if st.button("✅ Confirm Format Rules", use_container_width=True):
                r = httpx.put(
                    f"{BACKEND_URL}/sessions/{st.session_state.active_session_id}/format-rules",
                    json={"rules": rules_data, "confirmed_by_se": True},
                )
                if r.status_code == 200:
                    st.success("Format rules confirmed!")
                    st.rerun()
        else:
            st.success(
                "These formatting rules will be enforced during answer drafting and DOCX/XLSX export."
            )


# ── Export tab ────────────────────────────────────────────────────────────────
with tab_export:
    st.subheader("Export RFP Response Package")

    # Fetch current session statistics
    questions = api_get(f"/sessions/{st.session_state.active_session_id}/questions") or []
    rules_obj = api_get(f"/sessions/{st.session_state.active_session_id}/format-rules")
    rules_confirmed = rules_obj.get("confirmed_by_se", False) if rules_obj else False

    total_q = len(questions)
    approved_q = sum(1 for q in questions if q["status"] == "approved")
    draft_q = total_q - approved_q

    # Readiness Checklist Cards
    st.markdown("#### 📋 Pre-Export Readiness Assessment")
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.metric("Total Requirements", total_q)
    with rc2:
        st.metric(
            "Approved by SE",
            f"{approved_q} / {total_q}",
            delta=f"{int(approved_q/total_q*100 if total_q else 0)}% Complete",
        )
    with rc3:
        status_label = "Confirmed ✅" if rules_confirmed else "Pending ⚠️"
        st.metric("Format Rules", status_label)

    if draft_q > 0:
        st.warning(
            f"ℹ️ **Notice:** {draft_q} questions have unconfirmed draft answers. "
            "They will be exported with the official security watermark: `[DRAFT — NOT APPROVED BY SALES ENGINEER]`."
        )
    else:
        st.success(
            "🎉 All requirements have been approved by the Sales Engineer! Ready for client submission."
        )

    st.divider()

    # Generate Export Package Action
    st.markdown("#### 🚀 Generate Export Package")
    st.caption(
        "Creates both the styled Word document (.docx) and the Section 7 Compliance Matrix (.xlsx)."
    )

    if st.button("📦 Build / Refresh Export Package", type="primary", use_container_width=True):
        with st.spinner("Generating formatted DOCX proposal and XLSX compliance matrix..."):
            exp_res = api_post(f"/sessions/{st.session_state.active_session_id}/export")
            if exp_res:
                st.session_state[f"export_package_{st.session_state.active_session_id}"] = exp_res
                st.success("Export package generated successfully!")

    # Check for existing export package
    pkg = st.session_state.get(f"export_package_{st.session_state.active_session_id}")

    if pkg:
        st.markdown("#### 📥 Download Deliverables")
        d_col1, d_col2 = st.columns(2)

        with d_col1:
            st.markdown(
                f"**Proposal Document (DOCX)**  \n`{pkg.get('docx_filename', 'proposal.docx')}`"
            )
            try:
                docx_resp = httpx.get(
                    f"{BACKEND_URL}/sessions/{st.session_state.active_session_id}/export/docx",
                    timeout=60,
                )
                if docx_resp.status_code == 200:
                    st.download_button(
                        label="📄 Download DOCX Proposal",
                        data=docx_resp.content,
                        file_name=pkg.get("docx_filename", "RFP_Response_Proposal.docx"),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
            except Exception as exc:
                st.error(f"Failed to fetch DOCX: {exc}")

        with d_col2:
            st.markdown(
                f"**Compliance Matrix (XLSX)**  \n`{pkg.get('xlsx_filename', 'matrix.xlsx')}`"
            )
            try:
                xlsx_resp = httpx.get(
                    f"{BACKEND_URL}/sessions/{st.session_state.active_session_id}/export/xlsx",
                    timeout=60,
                )
                if xlsx_resp.status_code == 200:
                    st.download_button(
                        label="📊 Download Section 7 Compliance Matrix",
                        data=xlsx_resp.content,
                        file_name=pkg.get("xlsx_filename", "Compliance_Matrix.xlsx"),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
            except Exception as exc:
                st.error(f"Failed to fetch XLSX: {exc}")

        st.caption(f"Generated at: {pkg.get('generated_at', 'Recently')} (UTC)")

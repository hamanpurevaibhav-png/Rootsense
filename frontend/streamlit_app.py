"""
Dual-Panel Enterprise Streamlit Client Interface for RootSense for SAC.
Showcases Cognizant AI Lab's Neuro-SAN Multi-Agent Orchestration, the 7-Step
Neuro-Symbolic SAC Planning Diagnostic Tree, Enterprise KB RAG (ServiceNow &
Confluence), and the Automated IT4You Ticketing Bridge.
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# Ensure project root is on sys.path when invoked via `streamlit run frontend/streamlit_app.py`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend import config  # noqa: E402
from backend.agents.supervisor import SupervisorOrchestrator  # noqa: E402

# ---------------------------------------------------------------------------
# 1. Page Setup & Corporate Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    layout="wide",
    page_title="RootSense for SAC",
    page_icon="✨",
)

CORPORATE_CSS = """
<style>
    /* Top Corporate Header Banner */
    .rootsense-banner {
        background: linear-gradient(135deg, #001B44 0%, #00338D 60%, #005B60 100%);
        color: #FFFFFF;
        padding: 1.35rem 1.75rem;
        border-radius: 12px;
        margin-bottom: 1.2rem;
        box-shadow: 0 6px 18px rgba(0, 27, 68, 0.22);
        border-left: 6px solid #00C48C;
    }
    .rootsense-title {
        font-size: 1.65rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: 0.3px;
    }
    .rootsense-subtitle {
        font-size: 0.94rem;
        color: #D0E2FF;
        margin-top: 0.3rem;
        margin-bottom: 0.85rem;
    }
    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
    }
    .status-badge {
        background-color: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(0, 196, 140, 0.55);
        color: #E6FFF7;
        padding: 0.28rem 0.78rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 600;
        font-family: monospace;
    }
    /* Panel Section Headers */
    .panel-header {
        background-color: #F4F7FB;
        border-left: 4px solid #00338D;
        padding: 0.65rem 1rem;
        border-radius: 6px;
        margin-bottom: 0.85rem;
        color: #001B44;
        font-weight: 700;
        font-size: 1.05rem;
    }
    /* Custom IT4You Escalation Callout Box */
    .escalation-box {
        background: linear-gradient(135deg, #FFF8E7 0%, #FFF1D6 100%);
        border: 1px solid #F59E0B;
        border-left: 6px solid #D97706;
        padding: 1rem 1.25rem;
        border-radius: 10px;
        margin-top: 0.75rem;
        margin-bottom: 0.75rem;
        color: #78350F;
    }
    /* Step Card in Neuro-SAN Logical Path */
    .step-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 0.65rem 0.95rem;
        margin-bottom: 0.5rem;
    }
    .step-card-active {
        background-color: #ECFDF5;
        border: 1px solid #10B981;
        border-left: 5px solid #059669;
        border-radius: 8px;
        padding: 0.65rem 0.95rem;
        margin-bottom: 0.5rem;
    }
</style>
"""
st.markdown(CORPORATE_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 2. Session State Initialization
# ---------------------------------------------------------------------------
if "supervisor" not in st.session_state:
    st.session_state.supervisor = SupervisorOrchestrator(use_llm=False)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Welcome to **RootSense for SAC** — Cognizant AI Lab's Neuro-Symbolic "
                "Diagnostic Assistant for **SAP Analytics Cloud Planning**.\n\n"
                "Select one of the **4 Live Client Presentation Scenarios** below or type any "
                "SAC Planning / IT support question to inspect real-time audit logs, the "
                "7-Step Neuro-SAN Logical Path, Knowledge Base matches, and automated IT4You ticketing."
            ),
        }
    ]

if "active_diagnosis" not in st.session_state:
    st.session_state.active_diagnosis = None

if "submitted_ticket_info" not in st.session_state:
    st.session_state.submitted_ticket_info = None


def execute_user_query(query_text: str, use_live_llm: bool = False) -> None:
    """Route a user query through SupervisorOrchestrator and update Streamlit session state."""
    st.session_state.submitted_ticket_info = None
    st.session_state.messages.append({"role": "user", "content": query_text})

    orchestrator: SupervisorOrchestrator = st.session_state.supervisor
    result = orchestrator.route_query(
        query=query_text,
        caller_email=config.DEFAULT_CALLER_EMAIL,
        use_llm=use_live_llm,
    )
    st.session_state.active_diagnosis = result
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["assistant_message"],
        }
    )


# ---------------------------------------------------------------------------
# 3. Top Corporate Banner with Status Badges
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="rootsense-banner">
        <div class="rootsense-title">✨ RootSense for SAP Analytics Cloud (SAC)</div>
        <div class="rootsense-subtitle">
            Cognizant AI Lab &bull; Powered by <strong>Neuro-SAN</strong> Decentralized Agent Networks &amp; <strong>Google Gemini</strong> Neuro-Symbolic Reasoning
        </div>
        <div class="badge-row">
            <span class="status-badge">[🟢 Gemini 1.5 Active]</span>
            <span class="status-badge">[🟢 Mock SAC REST Gateway Online]</span>
            <span class="status-badge">[🟢 IT4You API Bridge Ready]</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar controls for optional Live Gemini LLM toggle and session reset
with st.sidebar:
    st.markdown("### ⚙️ Neuro-SAN Runtime Controls")
    use_live_gemini = st.toggle(
        "Enable Live Gemini Neural Synthesis",
        value=False,
        help="When enabled, Step 7 calls the configured Gemini model pool in addition to deterministic symbolic verification.",
    )
    st.caption(f"**Target SAC Model**: `{config.SAC_DEFAULT_MODEL_ID}`")
    st.caption(f"**Analyst Context**: `{config.DEFAULT_CALLER_EMAIL}`")
    if st.button("🔄 Reset Presentation Session", use_container_width=True):
        st.session_state.supervisor.clear_history()
        st.session_state.active_diagnosis = None
        st.session_state.submitted_ticket_info = None
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()


# ---------------------------------------------------------------------------
# 4. Dual-Panel Layout (50% Conversational Assistant | 50% Tech Evidence Inspector)
# ---------------------------------------------------------------------------
col1, col2 = st.columns(2, gap="large")

# ===========================================================================
# COLUMN 1: Conversational Diagnostic Assistant (Left 50%)
# ===========================================================================
with col1:
    st.markdown(
        '<div class="panel-header">💬 Conversational Diagnostic Assistant</div>',
        unsafe_allow_html=True,
    )
    st.markdown("**Quick-Select Client Presentation Scenarios:**")

    DEMO_SCENARIOS: List[str] = [
        "Why did my Travel Expense entry drop from 70K to 52K?",
        "I updated headcount in Draft but my manager cannot see it.",
        "Why doesn't Total Gross Margin % sum up across columns?",
        "I'm having SSO errors when logging onto the corporate VPN.",
    ]

    btn_col_a, btn_col_b = st.columns(2)
    with btn_col_a:
        if st.button(f"🔘 {DEMO_SCENARIOS[0]}", key="demo_1", use_container_width=True):
            execute_user_query(DEMO_SCENARIOS[0], use_live_llm=use_live_gemini)
            st.rerun()
        if st.button(f"🔘 {DEMO_SCENARIOS[2]}", key="demo_3", use_container_width=True):
            execute_user_query(DEMO_SCENARIOS[2], use_live_llm=use_live_gemini)
            st.rerun()

    with btn_col_b:
        if st.button(f"🔘 {DEMO_SCENARIOS[1]}", key="demo_2", use_container_width=True):
            execute_user_query(DEMO_SCENARIOS[1], use_live_llm=use_live_gemini)
            st.rerun()
        if st.button(f"🔘 {DEMO_SCENARIOS[3]}", key="demo_4", use_container_width=True):
            execute_user_query(DEMO_SCENARIOS[3], use_live_llm=use_live_gemini)
            st.rerun()

    st.divider()

    # Chat History Container
    chat_container = st.container(height=420)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Input Bar
    user_prompt = st.chat_input(
        "Ask RootSense about an SAC planning discrepancy, locked period, or IT issue..."
    )
    if user_prompt:
        execute_user_query(user_prompt, use_live_llm=use_live_gemini)
        st.rerun()

    # Prominent IT4You Escalation Box when it_escalation_needed=True (or is_user_fixable=False)
    active_diag: Dict[str, Any] = st.session_state.active_diagnosis or {}
    if active_diag and (
        active_diag.get("it_escalation_needed", False)
        or not active_diag.get("is_user_fixable", True)
    ):
        ticket_payload = active_diag.get("it4you_ticket") or {}
        ticket_id = ticket_payload.get("ticket_id", "IT4U-2026-XXXXX")
        routing_grp = ticket_payload.get("suggested_routing_group", "SAP-BTP-PLANNING-L3")
        priority_lvl = ticket_payload.get("priority", "P2 - High")

        st.markdown(
            f"""
            <div class="escalation-box">
                <strong>⚠️ Administrative / L3 Escalation Required ({active_diag.get('root_cause_category')})</strong><br/>
                This issue is governed by system-level SAC configurations and cannot be resolved directly by a planning analyst.
                RootSense has pre-assembled diagnostic brief <code>{ticket_id}</code> for routing group
                <code>{routing_grp}</code> (Priority: <strong>{priority_lvl}</strong>).
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.submitted_ticket_info is None:
            if st.button(
                "⚡ Submit IT4You Ticket on My Behalf",
                type="primary",
                use_container_width=True,
            ):
                submission_res = st.session_state.supervisor.submit_escalation_ticket(
                    ticket_payload
                )
                st.session_state.submitted_ticket_info = submission_res
                st.session_state.active_diagnosis["it4you_ticket"] = submission_res[
                    "submitted_ticket"
                ]
                st.rerun()
        else:
            sub_info = st.session_state.submitted_ticket_info
            st.success(
                f"✅ **IT4You Escalation Submitted Successfully!**\n\n"
                f"- **Ticket ID**: `{sub_info['ticket_id']}`\n"
                f"- **Status**: `{sub_info['status']}`\n"
                f"- **Assigned Queue**: `{sub_info['routing_group']}`\n"
                f"- **Priority & SLA Target**: `{sub_info['priority']}` — **{sub_info['sla_target']}**"
            )


# ===========================================================================
# COLUMN 2: Tech Audit Log & Evidence Inspector (Right 50%)
# ===========================================================================
with col2:
    st.markdown(
        '<div class="panel-header">🔍 Tech Audit Log &amp; Evidence Inspector</div>',
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "SAC Cell & Audit Log Inspector",
            "Neuro-SAN Logical Path",
            "Knowledge Base Matches",
            "Generated IT4You Ticket Payload",
        ]
    )

    # -----------------------------------------------------------------------
    # TAB 1: SAC Cell & Audit Log Inspector
    # -----------------------------------------------------------------------
    with tab1:
        if not active_diag:
            st.info(
                "Select a scenario or submit a query on the left to inspect retrieved SAC "
                "Data Change Logs, cell coordinates, and model metadata."
            )
        else:
            coords = active_diag.get("coordinates") or {}
            st.markdown("#### 📍 Captured SAC Planning Coordinates")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Account", str(coords.get("Account", "N/A")))
            c2.metric("Version", str(coords.get("Version", "N/A")))
            c3.metric("Cost Center", str(coords.get("CostCenter", "N/A")))
            c4.metric("Time Period", str(coords.get("Time", "N/A")))

            evidence_list: List[Dict[str, Any]] = active_diag.get("audit_evidence") or []
            st.markdown("#### 📊 Retrieved SAC Audit Log & Metadata Evidence")
            if evidence_list:
                # Flatten nested coordinate dicts for clean DataFrame display
                rows_for_df: List[Dict[str, Any]] = []
                for item in evidence_list:
                    flat_row = {
                        k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                        for k, v in item.items()
                    }
                    rows_for_df.append(flat_row)
                df_evidence = pd.DataFrame(rows_for_df)
                st.dataframe(df_evidence, use_container_width=True, hide_index=True)

                # Visual chronological timeline if audit log records have timestamps
                if any("timestamp" in item for item in evidence_list):
                    st.markdown("#### ⏱️ Chronological Cell Modification Timeline")
                    for item in evidence_list:
                        if "timestamp" in item:
                            actor_tag = item.get("actor", "UNKNOWN")
                            action_tag = item.get("action_type", "EDIT")
                            old_v = item.get("old_value", 0.0)
                            new_v = item.get("new_value", 0.0)
                            icon = "🤖" if "SYSTEM" in str(actor_tag).upper() else "👤"
                            st.markdown(
                                f"- {icon} **`{item['timestamp']}`** — **{actor_tag}** "
                                f"(`{action_tag}`): `{old_v:,.2f}` ➡️ **`{new_v:,.2f}`**"
                            )
            else:
                st.warning("No SAC cell audit records were required for this query.")

    # -----------------------------------------------------------------------
    # TAB 2: Neuro-SAN Logical Path
    # -----------------------------------------------------------------------
    with tab2:
        if not active_diag:
            st.info(
                "Run a diagnostic query to view the 7-Step Neuro-Symbolic evaluation "
                "checklist and AAOSA agent routing claims."
            )
        else:
            st.markdown(
                f"**Routed Specialist Agent**: `{active_diag.get('routed_agent')}` &nbsp;|&nbsp; "
                f"**Detected Intent**: `{active_diag.get('intent')}` &nbsp;|&nbsp; "
                f"**Root Cause Category**: `{active_diag.get('root_cause_category')}`"
            )

            aaosa_claims = active_diag.get("aaosa_claims") or {}
            if aaosa_claims:
                sac_c = aaosa_claims.get("SACDiagnosticAgent", {})
                kb_c = aaosa_claims.get("KnowledgeBaseAgent", {})
                st.caption(
                    f"Neuro-SAN AAOSA `Determine` Claims — "
                    f"**SACDiagnosticAgent**: Relevant=`{sac_c.get('Relevant')}` "
                    f"(Strength `{sac_c.get('Strength')}/10`) | "
                    f"**KnowledgeBaseAgent**: Relevant=`{kb_c.get('Relevant')}` "
                    f"(Strength `{kb_c.get('Strength')}/10`)"
                )

            st.markdown("#### 🧠 7-Step SAC Planning Diagnostic Checklist")
            checklist: List[Dict[str, Any]] = active_diag.get("seven_step_checklist") or []
            for step_info in checklist:
                marker = step_info.get("marker", "✅")
                css_class = "step-card-active" if marker == "✅" else "step-card"
                st.markdown(
                    f"""
                    <div class="{css_class}">
                        <strong>{marker} Step {step_info.get('step')}: {step_info.get('operation')}</strong>
                        &mdash; <code>{step_info.get('status')}</code><br/>
                        <span style="font-size: 0.88rem; color: #334155;">
                            <em>Objective:</em> {step_info.get('objective')}<br/>
                            <em>Result:</em> {step_info.get('summary')}
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # -----------------------------------------------------------------------
    # TAB 3: Knowledge Base Matches
    # -----------------------------------------------------------------------
    with tab3:
        if not active_diag:
            st.info(
                "Run a query to inspect matched ServiceNow Incidents and Confluence SOP articles."
            )
        else:
            kb_cards: List[Dict[str, Any]] = active_diag.get("kb_matches") or []
            if not kb_cards:
                st.warning("No matching ServiceNow or Confluence records found.")
            else:
                st.markdown("#### 📚 Retrieved ServiceNow & Confluence Knowledge Cards")
                for card in kb_cards:
                    score_float = float(card.get("match_score", 0.0))
                    pct_int = max(0, min(100, int(round(score_float * 100))))
                    source_badge = (
                        "🛠️ ServiceNow Incident"
                        if card.get("source") == "ServiceNow"
                        else "📘 Confluence SOP"
                    )
                    with st.container(border=True):
                        st.markdown(
                            f"**`{card.get('item_id')}` — {card.get('title')}**  \n"
                            f"{source_badge} &bull; *Category*: `{card.get('category')}`"
                        )
                        st.progress(
                            pct_int,
                            text=f"Semantic / Hybrid Match Confidence: {score_float * 100:.1f}%",
                        )
                        st.markdown(f"**Resolution / Guidance**: {card.get('resolution')}")

    # -----------------------------------------------------------------------
    # TAB 4: Generated IT4You Ticket Payload
    # -----------------------------------------------------------------------
    with tab4:
        if not active_diag:
            st.info(
                "When a non-user-fixable SAC issue is diagnosed, the validated IT4You "
                "JSON payload will be rendered here."
            )
        else:
            ticket_dict = active_diag.get("it4you_ticket")
            if not ticket_dict:
                st.success(
                    "🎉 **No IT4You Escalation Required** — This scenario is user-fixable "
                    "directly inside SAP Analytics Cloud using the guided resolution steps."
                )
            else:
                st.markdown(
                    f"#### 🎫 Validated IT4You Escalation Payload (`{ticket_dict.get('ticket_id')}` — Status: `{ticket_dict.get('status')}`)"
                )
                formatted_json = json.dumps(ticket_dict, indent=2)
                st.code(formatted_json, language="json")

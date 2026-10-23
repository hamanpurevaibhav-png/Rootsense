"""
Dual-Panel Enterprise Streamlit Client Interface for RootSense for SAC.
Showcases Cognizant AI Lab's Neuro-SAN Multi-Agent Orchestration (`nsflow` Live
Topology), the 7-Step Neuro-Symbolic SAC Planning Diagnostic Tree, Enterprise KB
RAG (ServiceNow & Confluence), and the Automated IT4You Ticketing Bridge.
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# Ensure project root is on sys.path when invoked via `streamlit run frontend/streamlit_app.py`
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend import config  # noqa: E402
from backend.agents.supervisor import SupervisorOrchestrator  # noqa: E402

# ---------------------------------------------------------------------------
# 1. Page Setup & Executive Enterprise Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    layout="wide",
    page_title="RootSense for SAC",
    page_icon="✨",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
    /* Reduce top whitespace for an executive dashboard feel */
    .block-container {
        padding-top: 1.4rem !important;
        padding-bottom: 2rem !important;
        max-width: 98% !important;
    }

    /* Executive Top Hero Header */
    .rootsense-hero {
        background: linear-gradient(125deg, #071330 0%, #002C77 52%, #064E5B 100%);
        color: #FFFFFF;
        padding: 1.25rem 1.65rem;
        border-radius: 14px;
        margin-bottom: 1.15rem;
        box-shadow: 0 10px 25px -5px rgba(7, 19, 48, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-left: 6px solid #00E5A3;
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
    }
    .hero-left {
        display: flex;
        flex-direction: column;
        gap: 0.28rem;
    }
    .hero-eyebrow {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        color: #00E5A3;
        font-weight: 700;
    }
    .hero-title {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.3px;
        color: #FFFFFF;
    }
    .hero-subtitle {
        font-size: 0.9rem;
        color: #CBD5E1;
        margin: 0;
    }
    .badge-cluster {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
    }
    .status-pill {
        background: rgba(15, 23, 42, 0.55);
        border: 1px solid rgba(0, 229, 163, 0.45);
        color: #ECFDF5;
        padding: 0.32rem 0.75rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        backdrop-filter: blur(6px);
        white-space: nowrap;
    }
    .status-pill-nsflow {
        background: rgba(88, 28, 135, 0.55);
        border: 1px solid rgba(192, 132, 252, 0.65);
        color: #F3E8FF;
        padding: 0.32rem 0.75rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        white-space: nowrap;
    }

    /* Section Header Bar */
    .section-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(90deg, #F1F5F9 0%, #FFFFFF 100%);
        border: 1px solid #E2E8F0;
        border-left: 4px solid #00338D;
        padding: 0.6rem 0.95rem;
        border-radius: 8px;
        margin-bottom: 0.75rem;
    }
    .section-banner-title {
        font-weight: 700;
        font-size: 1.02rem;
        color: #0F172A;
        margin: 0;
    }
    .section-banner-tag {
        font-size: 0.74rem;
        font-family: 'JetBrains Mono', monospace;
        color: #475569;
        background: #E2E8F0;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-weight: 600;
    }

    /* Scenario Question Text inside Cards */
    .scenario-question {
        font-size: 0.87rem;
        font-weight: 600;
        color: #1E293B;
        line-height: 1.38;
        margin: 0.35rem 0 0.55rem 0;
        min-height: 2.4rem;
    }

    /* Prominent IT4You Escalation Callout */
    .escalation-banner {
        background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
        border: 1px solid #F59E0B;
        border-left: 6px solid #D97706;
        padding: 0.95rem 1.15rem;
        border-radius: 10px;
        margin-top: 0.65rem;
        margin-bottom: 0.65rem;
        color: #78350F;
        font-size: 0.9rem;
    }

    /* Step Cards in 7-Step Checklist */
    .step-row-pass {
        background: #FFFFFF;
        border: 1px solid #BBF7D0;
        border-left: 4px solid #10B981;
        border-radius: 8px;
        padding: 0.6rem 0.85rem;
        margin-bottom: 0.45rem;
    }
    .step-row-skip {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #94A3B8;
        border-radius: 8px;
        padding: 0.55rem 0.85rem;
        margin-bottom: 0.45rem;
        opacity: 0.82;
    }
    .step-title {
        font-size: 0.88rem;
        font-weight: 700;
        color: #0F172A;
    }
    .step-meta {
        font-size: 0.81rem;
        color: #475569;
        margin-top: 0.18rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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
                "Choose any of the **4 Live Client Presentation Scenarios** above or type a "
                "custom question below to watch the **Neuro-SAN `nsflow` Multi-Agent Graph**, "
                "7-Step SAC Diagnostic Checklist, Enterprise RAG, and IT4You L3 Ticketing in real time."
            ),
            "trace_summary": None,
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

    claims = result.get("aaosa_claims") or {}
    sac_strength = claims.get("SACDiagnosticAgent", {}).get("Strength", "-")
    kb_strength = claims.get("KnowledgeBaseAgent", {}).get("Strength", "-")

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["assistant_message"],
            "trace_summary": {
                "routed_agent": result.get("routed_agent", "SACDiagnosticAgent"),
                "intent": result.get("intent", "SAC_PLANNING_DIAGNOSTIC"),
                "root_cause_category": result.get("root_cause_category", "N/A"),
                "sac_strength": sac_strength,
                "kb_strength": kb_strength,
                "it_escalation_needed": result.get("it_escalation_needed", False),
            },
        }
    )


# ---------------------------------------------------------------------------
# 3. Interactive Neuro-SAN `nsflow` Topology Renderer (Live HTML/SVG Component)
# ---------------------------------------------------------------------------
def render_nsflow_network_canvas(active_diag: Dict[str, Any] | None) -> None:
    """
    Renders an interactive Neuro-SAN Studio (`nsflow`) visual multi-agent topology
    canvas with live AAOSA Determine/Fulfill edge animations, claim strength meters,
    CodedTool execution states, and `sly_data` private bus telemetry.
    """
    diag = active_diag or {}
    routed_agent = diag.get("routed_agent", "")
    root_cause = diag.get("root_cause_category", "IDLE")
    it_escalation = bool(diag.get("it_escalation_needed", False))
    claims = diag.get("aaosa_claims") or {}

    sac_claim = claims.get("SACDiagnosticAgent", {"Relevant": False, "Strength": 0})
    kb_claim = claims.get("KnowledgeBaseAgent", {"Relevant": False, "Strength": 0})
    sac_strength = int(sac_claim.get("Strength", 0))
    kb_strength = int(kb_claim.get("Strength", 0))

    is_sac_active = routed_agent == "SACDiagnosticAgent"
    is_kb_active = routed_agent == "KnowledgeBaseAgent"
    has_active_run = bool(routed_agent)

    # Dynamic colors and edge classes based on active routing state
    frontman_border = "#00E5A3" if has_active_run else "#38BDF8"
    sac_border = "#00E5A3" if is_sac_active else "#475569"
    sac_bg = "rgba(16, 185, 129, 0.16)" if is_sac_active else "rgba(30, 41, 59, 0.85)"
    kb_border = "#38BDF8" if is_kb_active else "#475569"
    kb_bg = "rgba(56, 189, 248, 0.16)" if is_kb_active else "rgba(30, 41, 59, 0.85)"

    sac_tool_border = "#10B981" if is_sac_active else "#334155"
    it4u_tool_border = "#F59E0B" if (is_sac_active and it_escalation) else "#334155"
    kb_tool_border = "#38BDF8" if is_kb_active else "#334155"

    edge_sac_class = "edge-active-green" if is_sac_active else "edge-idle"
    edge_kb_class = "edge-active-blue" if is_kb_active else "edge-idle"
    edge_sac_tool_class = "edge-active-green" if is_sac_active else "edge-idle"
    edge_it4u_class = "edge-active-amber" if (is_sac_active and it_escalation) else "edge-idle"
    edge_kb_tool_class = "edge-active-blue" if is_kb_active else "edge-idle"

    sac_mode_badge = "FULFILL ★" if is_sac_active else ("DETERMINE" if has_active_run else "STANDBY")
    kb_mode_badge = "FULFILL ★" if is_kb_active else ("DETERMINE" if has_active_run else "STANDBY")

    coords = diag.get("coordinates") or {}
    acct_label = coords.get("Account", "CORP_FINANCE_PLANNING")
    ticket_obj = diag.get("it4you_ticket") or {}
    ticket_label = ticket_obj.get("ticket_id", "No Ticket Needed") if has_active_run else "Standby"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: transparent;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            color: #F8FAFC;
        }}
        .nsflow-wrapper {{
            background: radial-gradient(circle at 50% 15%, #1E293B 0%, #0F172A 75%, #090D16 100%);
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 14px 16px 12px 16px;
            position: relative;
            overflow: hidden;
            box-shadow: inset 0 0 40px rgba(0, 0, 0, 0.45);
        }}
        .nsflow-topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(148, 163, 184, 0.18);
            padding-bottom: 8px;
            margin-bottom: 8px;
        }}
        .nsflow-brand {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            font-weight: 700;
            color: #E2E8F0;
            letter-spacing: 0.4px;
        }}
        .pulse-dot {{
            width: 9px;
            height: 9px;
            border-radius: 50%;
            background: {"#00E5A3" if has_active_run else "#38BDF8"};
            box-shadow: 0 0 10px {"#00E5A3" if has_active_run else "#38BDF8"};
            animation: pulseGlow 1.8s infinite ease-in-out;
        }}
        @keyframes pulseGlow {{
            0%, 100% {{ transform: scale(1); opacity: 1; }}
            50% {{ transform: scale(1.3); opacity: 0.65; }}
        }}
        .nsflow-meta {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            color: #94A3B8;
            background: rgba(15, 23, 42, 0.75);
            padding: 3px 9px;
            border-radius: 999px;
            border: 1px solid #334155;
        }}
        svg {{
            width: 100%;
            height: 335px;
            display: block;
        }}
        .edge-idle {{
            stroke: #334155;
            stroke-width: 1.8;
            stroke-dasharray: 4 4;
            fill: none;
        }}
        .edge-active-green {{
            stroke: #00E5A3;
            stroke-width: 2.8;
            stroke-dasharray: 8 5;
            fill: none;
            animation: dashFlow 0.9s linear infinite;
            filter: drop-shadow(0 0 5px rgba(0, 229, 163, 0.55));
        }}
        .edge-active-blue {{
            stroke: #38BDF8;
            stroke-width: 2.8;
            stroke-dasharray: 8 5;
            fill: none;
            animation: dashFlow 0.9s linear infinite;
            filter: drop-shadow(0 0 5px rgba(56, 189, 248, 0.55));
        }}
        .edge-active-amber {{
            stroke: #F59E0B;
            stroke-width: 2.8;
            stroke-dasharray: 8 5;
            fill: none;
            animation: dashFlow 0.9s linear infinite;
            filter: drop-shadow(0 0 5px rgba(245, 158, 11, 0.6));
        }}
        @keyframes dashFlow {{
            to {{ stroke-dashoffset: -26; }}
        }}
        .node-title {{
            font-size: 11.5px;
            font-weight: 700;
            fill: #F8FAFC;
        }}
        .node-sub {{
            font-size: 9.5px;
            font-family: 'JetBrains Mono', monospace;
            fill: #94A3B8;
        }}
        .node-badge {{
            font-size: 9px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            fill: #0F172A;
        }}
        .sly-bar {{
            margin-top: 6px;
            background: rgba(15, 23, 42, 0.85);
            border: 1px solid #334155;
            border-left: 3px solid #A855F7;
            border-radius: 7px;
            padding: 6px 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: 'JetBrains Mono', monospace;
            font-size: 10.5px;
            color: #CBD5E1;
        }}
        .sly-tag {{
            color: #D8B4FE;
            font-weight: 700;
        }}
    </style>
    </head>
    <body>
    <div class="nsflow-wrapper">
        <div class="nsflow-topbar">
            <div class="nsflow-brand">
                <div class="pulse-dot"></div>
                <span>NEURO-SAN STUDIO &bull; NSFLOW LIVE AGENT TOPOLOGY (rootsense_sac.hocon)</span>
            </div>
            <div class="nsflow-meta">
                State: <strong style="color:#00E5A3;">{root_cause}</strong>
            </div>
        </div>

        <svg viewBox="0 0 760 330" preserveAspectRatio="xMidYMid meet">
            <!-- DEFINITIONS -->
            <defs>
                <linearGradient id="frontmanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#0F172A" />
                    <stop offset="100%" stop-color="#1E3A8A" />
                </linearGradient>
                <linearGradient id="slyGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stop-color="#2E1065" />
                    <stop offset="50%" stop-color="#4C1D95" />
                    <stop offset="100%" stop-color="#2E1065" />
                </linearGradient>
            </defs>

            <!-- EDGES: Front-Man -> Specialists (AAOSA Determine / Fulfill) -->
            <path d="M 380 68 C 380 100, 205 95, 205 128" class="{edge_sac_class}" />
            <path d="M 380 68 C 380 100, 565 95, 565 128" class="{edge_kb_class}" />

            <!-- EDGES: Specialists -> CodedTools -->
            <path d="M 165 194 C 145 215, 125 220, 125 242" class="{edge_sac_tool_class}" />
            <path d="M 245 194 C 285 215, 345 220, 345 242" class="{edge_it4u_class}" />
            <path d="M 565 194 C 565 215, 585 220, 585 242" class="{edge_kb_tool_class}" />

            <!-- EDGE LABELS -->
            <rect x="215" y="84" width="118" height="17" rx="4" fill="#0F172A" stroke="#334155"/>
            <text x="274" y="96" text-anchor="middle" class="node-sub" fill="#00E5A3">AAOSA Strength: {sac_strength}/10</text>

            <rect x="435" y="84" width="118" height="17" rx="4" fill="#0F172A" stroke="#334155"/>
            <text x="494" y="96" text-anchor="middle" class="node-sub" fill="#38BDF8">AAOSA Strength: {kb_strength}/10</text>

            <!-- TIER 1: FRONT MAN (SupervisorOrchestrator) -->
            <g transform="translate(245, 10)">
                <rect width="270" height="58" rx="10" fill="url(#frontmanGrad)" stroke="{frontman_border}" stroke-width="2.2"/>
                <rect x="10" y="9" width="76" height="15" rx="4" fill="#00E5A3"/>
                <text x="48" y="20" text-anchor="middle" class="node-badge">FRONT-MAN</text>
                <text x="95" y="21" class="node-title">SupervisorOrchestrator</text>
                <text x="12" y="39" class="node-sub">Protocol: AAOSA Determine &rarr; Fulfill Router</text>
                <text x="12" y="51" class="node-sub" fill="#CBD5E1">Active Route: {routed_agent or "Awaiting Inquiry"}</text>
            </g>

            <!-- TIER 2 LEFT: SACDiagnosticAgent -->
            <g transform="translate(65, 128)">
                <rect width="280" height="66" rx="10" fill="{sac_bg}" stroke="{sac_border}" stroke-width="2.2"/>
                <rect x="10" y="9" width="74" height="15" rx="4" fill="{"#00E5A3" if is_sac_active else "#64748B"}"/>
                <text x="47" y="20" text-anchor="middle" class="node-badge">{sac_mode_badge}</text>
                <text x="92" y="21" class="node-title">SACDiagnosticAgent</text>
                <text x="12" y="40" class="node-sub">7-Step Neuro-Symbolic Decision Tree</text>
                <text x="12" y="54" class="node-sub" fill="#A7F3D0">Claim: Relevant={sac_claim.get("Relevant", False)} ({sac_strength}/10)</text>
            </g>

            <!-- TIER 2 RIGHT: KnowledgeBaseAgent -->
            <g transform="translate(425, 128)">
                <rect width="280" height="66" rx="10" fill="{kb_bg}" stroke="{kb_border}" stroke-width="2.2"/>
                <rect x="10" y="9" width="74" height="15" rx="4" fill="{"#38BDF8" if is_kb_active else "#64748B"}"/>
                <text x="47" y="20" text-anchor="middle" class="node-badge">{kb_mode_badge}</text>
                <text x="92" y="21" class="node-title">KnowledgeBaseAgent</text>
                <text x="12" y="40" class="node-sub">Hybrid Semantic + Keyword Enterprise RAG</text>
                <text x="12" y="54" class="node-sub" fill="#BAE6FD">Claim: Relevant={kb_claim.get("Relevant", False)} ({kb_strength}/10)</text>
            </g>

            <!-- TIER 3 TOOL 1: SACAuditDiagnosticTool -->
            <g transform="translate(20, 242)">
                <rect width="215" height="64" rx="8" fill="#0F172A" stroke="{sac_tool_border}" stroke-width="1.8"/>
                <text x="12" y="19" class="node-title" fill="#34D399">&#9881; SACAuditDiagnosticTool</text>
                <text x="12" y="35" class="node-sub">CodedTool &bull; MockSACGateway</text>
                <text x="12" y="50" class="node-sub" fill="#E2E8F0">Target: {acct_label}</text>
            </g>

            <!-- TIER 3 TOOL 2: IT4YouTicketingTool -->
            <g transform="translate(250, 242)">
                <rect width="215" height="64" rx="8" fill="#0F172A" stroke="{it4u_tool_border}" stroke-width="1.8"/>
                <text x="12" y="19" class="node-title" fill="#FBBF24">&#9889; IT4YouTicketingTool</text>
                <text x="12" y="35" class="node-sub">CodedTool &bull; SAP-BTP-PLANNING-L3</text>
                <text x="12" y="50" class="node-sub" fill="#FDE68A">Ticket: {ticket_label}</text>
            </g>

            <!-- TIER 3 TOOL 3: EnterpriseKBRAGTool -->
            <g transform="translate(480, 242)">
                <rect width="255" height="64" rx="8" fill="#0F172A" stroke="{kb_tool_border}" stroke-width="1.8"/>
                <text x="12" y="19" class="node-title" fill="#38BDF8">&#128218; EnterpriseKBRAGTool</text>
                <text x="12" y="35" class="node-sub">CodedTool &bull; ServiceNow + Confluence</text>
                <text x="12" y="50" class="node-sub" fill="#BAE6FD">Top-K Hybrid Cosine + Lexical</text>
            </g>
        </svg>

        <div class="sly-bar">
            <div>
                <span class="sly-tag">🔒 sly_data Private State Bus:</span>
                <span>sac_coordinates &bull; active_diagnosis &bull; it4you_tickets</span>
            </div>
            <div>
                <span>NSFlow Studio Server: <strong>http://localhost:4173</strong> (<code>.\\start_neurosan.ps1</code>)</span>
            </div>
        </div>
    </div>
    </body>
    </html>
    """
    components.html(html_content, height=425, scrolling=False)


# ---------------------------------------------------------------------------
# 4. Top Corporate Banner with Required Status Badges
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="rootsense-hero">
        <div class="hero-left">
            <div class="hero-eyebrow">Cognizant AI Lab &bull; Enterprise SAP BTP Agentic Architecture</div>
            <div class="hero-title">✨ RootSense for SAP Analytics Cloud (SAC)</div>
            <div class="hero-subtitle">
                Decentralized <strong>Neuro-SAN (AAOSA)</strong> Multi-Agent Orchestration &amp; <strong>Google Gemini</strong> 7-Step Neuro-Symbolic Diagnostic Engine
            </div>
        </div>
        <div class="badge-cluster">
            <span class="status-pill">[🟢 Gemini 1.5 Active]</span>
            <span class="status-pill">[🟢 Mock SAC REST Gateway Online]</span>
            <span class="status-pill">[🟢 IT4You API Bridge Ready]</span>
            <span class="status-pill-nsflow">[🟣 Neuro-SAN nsflow Active]</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar controls for optional Live Gemini LLM toggle, NSFlow Studio instructions, and session reset
with st.sidebar:
    st.markdown("### :material/tune: Neuro-SAN Runtime Controls")
    use_live_gemini = st.toggle(
        "Enable Live Gemini Neural Synthesis",
        value=False,
        help="When enabled, Step 7 invokes the configured Gemini model pool in addition to deterministic symbolic verification.",
    )
    st.caption(f"**Target SAC Model**: `{config.SAC_DEFAULT_MODEL_ID}`")
    st.caption(f"**Analyst Context**: `{config.DEFAULT_CALLER_EMAIL}`")
    st.caption("**HOCON Registry**: `registries/rootsense_sac.hocon`")

    if st.button(":material/restart_alt: Reset Presentation Session", width="stretch"):
        st.session_state.supervisor.clear_history()
        st.session_state.active_diagnosis = None
        st.session_state.submitted_ticket_info = None
        st.session_state.messages = [st.session_state.messages[0]]
        st.rerun()

    st.markdown("---")
    st.markdown("### :material/hub: Native NSFlow Studio UI")
    st.caption(
        "In addition to the embedded **Neuro-SAN `nsflow` Graph** in the right panel, "
        "you can launch the standalone Neuro-SAN Studio server on port `4173`:"
    )
    st.code(".\\start_neurosan.ps1", language="powershell")


# ---------------------------------------------------------------------------
# 5. Dual-Panel Layout (Left 50%: Conversational Assistant | Right 50%: Inspector)
# ---------------------------------------------------------------------------
col1, col2 = st.columns([0.96, 1.04], gap="large")

# ===========================================================================
# COLUMN 1: Conversational Diagnostic Assistant (Left Panel)
# ===========================================================================
with col1:
    st.markdown(
        """
        <div class="section-banner">
            <span class="section-banner-title">💬 Conversational Diagnostic Assistant</span>
            <span class="section-banner-tag">AAOSA Front-Man Router</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "**Quick-Select Client Presentation Scenarios** — Click any scenario card below to execute the live Neuro-Symbolic loop:"
    )

    SCENARIO_CARDS: List[Dict[str, str]] = [
        {
            "key": "demo_1",
            "badge": ":red-badge[Scenario 1 • System Overwrite]",
            "button_label": "Run Scenario 1: Travel Expense Drop",
            "icon": ":material/schedule:",
            "query": "Why did my Travel Expense entry drop from 70K to 52K?",
        },
        {
            "key": "demo_2",
            "badge": ":blue-badge[Scenario 2 • Private Draft]",
            "button_label": "Run Scenario 2: Un-published Headcount",
            "icon": ":material/edit_note:",
            "query": "I updated headcount in Draft but my manager cannot see it.",
        },
        {
            "key": "demo_3",
            "badge": ":violet-badge[Scenario 3 • Formula Rollup]",
            "button_label": "Run Scenario 3: Gross Margin % Formula",
            "icon": ":material/functions:",
            "query": "Why doesn't Total Gross Margin % sum up across columns?",
        },
        {
            "key": "demo_4",
            "badge": ":orange-badge[Scenario 4 • VPN / SSO RAG]",
            "button_label": "Run Scenario 4: Corporate VPN SSO Error",
            "icon": ":material/vpn_key:",
            "query": "I'm having SSO errors when logging onto the corporate VPN.",
        },
    ]

    sc_col_a, sc_col_b = st.columns(2, gap="small")
    for idx, sc in enumerate(SCENARIO_CARDS):
        target_col = sc_col_a if idx % 2 == 0 else sc_col_b
        with target_col:
            with st.container(border=True):
                st.markdown(sc["badge"])
                st.markdown(
                    f'<div class="scenario-question">“{sc["query"]}”</div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    sc["button_label"],
                    key=sc["key"],
                    icon=sc["icon"],
                    width="stretch",
                ):
                    execute_user_query(sc["query"], use_live_llm=use_live_gemini)
                    st.rerun()

    # Chat History Container
    chat_container = st.container(height=390, border=True)
    with chat_container:
        for msg in st.session_state.messages:
            avatar = ":material/neurology:" if msg["role"] == "assistant" else ":material/person:"
            with st.chat_message(msg["role"], avatar=avatar):
                trace = msg.get("trace_summary")
                if trace:
                    with st.status(
                        f"Neuro-SAN AAOSA Routed → `{trace['routed_agent']}` ({trace['root_cause_category']})",
                        state="complete",
                        expanded=False,
                    ):
                        st.markdown(
                            f"- **Front-Man**: `SupervisorOrchestrator`\n"
                            f"- **AAOSA Determine Claims**: `SACDiagnosticAgent` (**{trace['sac_strength']}/10**) vs `KnowledgeBaseAgent` (**{trace['kb_strength']}/10**)\n"
                            f"- **Selected Specialist**: `{trace['routed_agent']}` (`mode='Fulfill'`)\n"
                            f"- **Classification**: `{trace['root_cause_category']}` | **L3 Escalation Needed**: `{trace['it_escalation_needed']}`"
                        )
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
            <div class="escalation-banner">
                <strong>⚠️ Administrative / L3 Escalation Required ({active_diag.get('root_cause_category')})</strong><br/>
                This issue is governed by system-level SAC configurations and cannot be resolved directly by a planning analyst.
                RootSense has pre-assembled diagnostic brief <code>{ticket_id}</code> in <code>sly_data['it4you_tickets']</code>
                for routing queue <code>{routing_grp}</code> (Priority: <strong>{priority_lvl}</strong>).
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.submitted_ticket_info is None:
            if st.button(
                "⚡ Submit IT4You Ticket on My Behalf",
                type="primary",
                width="stretch",
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
# COLUMN 2: Neuro-SAN `nsflow` & Tech Audit Inspector (Right Panel)
# ===========================================================================
with col2:
    st.markdown(
        """
        <div class="section-banner">
            <span class="section-banner-title">🔍 Neuro-SAN nsflow &amp; Tech Evidence Inspector</span>
            <span class="section-banner-tag">Live Symbolic Telemetry</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_nsflow, tab_sac, tab_kb, tab_ticket = st.tabs(
        [
            "🕸️ Neuro-SAN Logical Path",
            "📊 SAC Cell & Audit Log Inspector",
            "📚 Knowledge Base Matches",
            "🎫 Generated IT4You Ticket Payload",
        ]
    )

    # -----------------------------------------------------------------------
    # TAB 1: Neuro-SAN Logical Path & Interactive `nsflow` Topology
    # -----------------------------------------------------------------------
    with tab_nsflow:
        # Always render the interactive Neuro-SAN `nsflow` Multi-Agent Topology Canvas!
        render_nsflow_network_canvas(active_diag if active_diag else None)

        if not active_diag:
            st.info(
                "👆 **Interactive Neuro-SAN `nsflow` Topology Ready** — Select any of the 4 scenarios "
                "on the left to animate live AAOSA `Determine` / `Fulfill` signal routing, inspect "
                "`sly_data` state updates, and step through the 7-Step Neuro-Symbolic Diagnostic Checklist."
            )
        else:
            aaosa_claims = active_diag.get("aaosa_claims") or {}
            sac_c = aaosa_claims.get("SACDiagnosticAgent", {})
            kb_c = aaosa_claims.get("KnowledgeBaseAgent", {})

            m1, m2, m3 = st.columns(3, gap="small")
            m1.metric(
                "Winning AAOSA Agent",
                str(active_diag.get("routed_agent", "N/A")),
                delta=f"Mode: Fulfill",
                border=True,
            )
            m2.metric(
                "SACDiagnostic Claim",
                f"{sac_c.get('Strength', 0)} / 10",
                delta=f"Relevant: {sac_c.get('Relevant', False)}",
                border=True,
            )
            m3.metric(
                "KnowledgeBase Claim",
                f"{kb_c.get('Strength', 0)} / 10",
                delta=f"Relevant: {kb_c.get('Relevant', False)}",
                border=True,
            )

            st.markdown("##### 🧠 7-Step Neuro-Symbolic SAC Planning Diagnostic Checklist")
            checklist: List[Dict[str, Any]] = active_diag.get("seven_step_checklist") or []
            for step_info in checklist:
                marker = step_info.get("marker", "✅")
                row_class = "step-row-pass" if marker == "✅" else "step-row-skip"
                st.markdown(
                    f"""
                    <div class="{row_class}">
                        <div class="step-title">
                            {marker} Step {step_info.get('step')}: {step_info.get('operation')}
                            &nbsp;<code style="font-size:0.76rem;">[{step_info.get('status')}]</code>
                        </div>
                        <div class="step-meta">
                            <strong>Objective:</strong> {step_info.get('objective')}<br/>
                            <strong>Symbolic Result:</strong> {step_info.get('summary')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with st.expander(":material/data_object: Inspect Live `sly_data` Private Channel & `rootsense_sac.hocon`"):
            sly_snapshot = st.session_state.supervisor.sly_data
            st.markdown("**Private `sly_data` Session Dictionary (Isolated from LLM Prompt Context):**")
            st.json(sly_snapshot if sly_snapshot else {"status": "standby", "it4you_tickets": []})
            hocon_path = ROOT_DIR / "registries" / "rootsense_sac.hocon"
            if hocon_path.exists():
                st.markdown("**Declarative Neuro-SAN Agent Network (`registries/rootsense_sac.hocon`):**")
                st.code(hocon_path.read_text(encoding="utf-8"), language="hcl")

    # -----------------------------------------------------------------------
    # TAB 2: SAC Cell & Audit Log Inspector
    # -----------------------------------------------------------------------
    with tab_sac:
        if not active_diag:
            st.info(
                "Select a scenario or submit a query on the left to inspect retrieved SAC "
                "Data Change Logs, cell coordinates, and model metadata."
            )
        else:
            coords = active_diag.get("coordinates") or {}
            st.markdown("##### 📍 Captured SAC Planning Coordinates")
            c1, c2, c3, c4 = st.columns(4, gap="small")
            c1.metric("Account", str(coords.get("Account", "N/A")), border=True)
            c2.metric("Version", str(coords.get("Version", "N/A")), border=True)
            c3.metric("Cost Center", str(coords.get("CostCenter", "N/A")), border=True)
            c4.metric("Time Period", str(coords.get("Time", "N/A")), border=True)

            evidence_list: List[Dict[str, Any]] = active_diag.get("audit_evidence") or []
            st.markdown("##### 📊 Retrieved SAC Audit Log & Metadata Evidence")
            if evidence_list:
                rows_for_df: List[Dict[str, Any]] = []
                for item in evidence_list:
                    flat_row = {
                        k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                        for k, v in item.items()
                    }
                    rows_for_df.append(flat_row)
                df_evidence = pd.DataFrame(rows_for_df)
                st.dataframe(df_evidence, width="stretch", hide_index=True)

                if any("timestamp" in item for item in evidence_list):
                    st.markdown("##### ⏱️ Chronological Cell Modification Timeline")
                    for item in evidence_list:
                        if "timestamp" in item:
                            actor_tag = item.get("actor", "UNKNOWN")
                            action_tag = item.get("action_type", "EDIT")
                            old_v = item.get("old_value", 0.0)
                            new_v = item.get("new_value", 0.0)
                            is_sys = "SYSTEM" in str(actor_tag).upper()
                            badge_str = (
                                ":red-badge[SYSTEM BATCH OVERWRITE]"
                                if is_sys
                                else ":green-badge[MANUAL ANALYST EDIT]"
                            )
                            with st.container(border=True):
                                st.markdown(
                                    f"{badge_str} &nbsp; **`{item['timestamp']}`** — Actor: **`{actor_tag}`** "
                                    f"(`{action_tag}`)  \n"
                                    f"Cell Value Transition: **`{old_v:,.2f}`** ➡️ **`{new_v:,.2f}`**"
                                )
            else:
                st.warning("No SAC cell audit records were required for this query.")

    # -----------------------------------------------------------------------
    # TAB 3: Knowledge Base Matches
    # -----------------------------------------------------------------------
    with tab_kb:
        if not active_diag:
            st.info(
                "Run a query to inspect matched ServiceNow Incidents and Confluence SOP articles."
            )
        else:
            kb_cards: List[Dict[str, Any]] = active_diag.get("kb_matches") or []
            if not kb_cards:
                st.warning("No matching ServiceNow or Confluence records found.")
            else:
                st.markdown("##### 📚 Retrieved ServiceNow & Confluence Knowledge Cards")
                for card in kb_cards:
                    score_float = float(card.get("match_score", 0.0))
                    pct_int = max(0, min(100, int(round(score_float * 100))))
                    source_badge = (
                        ":orange-badge[🛠️ ServiceNow Incident]"
                        if card.get("source") == "ServiceNow"
                        else ":blue-badge[📘 Confluence SOP]"
                    )
                    with st.container(border=True):
                        st.markdown(
                            f"{source_badge} &nbsp; **`{card.get('item_id')}` — {card.get('title')}**  \n"
                            f"*Category*: `{card.get('category')}`"
                        )
                        st.progress(
                            pct_int,
                            text=f"Hybrid Semantic + Keyword Match Confidence: {score_float * 100:.1f}%",
                        )
                        st.markdown(f"**Resolution / Guidance**: {card.get('resolution')}")

    # -----------------------------------------------------------------------
    # TAB 4: Generated IT4You Ticket Payload
    # -----------------------------------------------------------------------
    with tab_ticket:
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
                t_c1, t_c2, t_c3 = st.columns(3, gap="small")
                t_c1.metric("Ticket ID", str(ticket_dict.get("ticket_id", "N/A")), border=True)
                t_c2.metric("Priority", str(ticket_dict.get("priority", "N/A")), border=True)
                t_c3.metric("Status", str(ticket_dict.get("status", "DRAFT")), border=True)

                st.markdown(
                    f"##### 🎫 Validated IT4You Escalation Payload (`{ticket_dict.get('suggested_routing_group')}`)"
                )
                formatted_json = json.dumps(ticket_dict, indent=2)
                st.code(formatted_json, language="json")

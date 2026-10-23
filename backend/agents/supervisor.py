"""
Neuro-SAN Agentic Router (SupervisorOrchestrator) for RootSense SAC.
Coordinates intent classification, AAOSA Determine/Fulfill claims, the 7-Step
SAC Planning Diagnostic Engine (SACDiagnosticAgent), the Enterprise Knowledge
Base RAG Agent (KnowledgeBaseAgent), and the Automated IT4You Ticketing Service.
Grounded strictly in rootsense.md.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from backend import config
from backend.agents.knowledge_agent import KnowledgeBaseAgent
from backend.agents.sac_diagnostic import (
    CauseCategory,
    DiagnosticResult,
    SACDiagnosticAgent,
)
from backend.ticketing.it4you_service import IT4YouTicket, IT4YouTicketingService


class SupervisorOrchestrator:
    """
    Neuro-SAN Front-Man Supervisor & Agentic Router.

    Responsibilities:
    1. Classify incoming user queries into 'SAC_PLANNING_DIAGNOSTIC' vs 'GENERAL_IT_RAG'
       using Neuro-SAN AAOSA Determine claims + optional fast Gemini LLM classification.
    2. Route SAC Planning inquiries to `SACDiagnosticAgent` (7-Step Diagnostic Tree).
    3. Route General IT / SSO / VPN / SOP inquiries (or UNKNOWN diagnostic fallbacks)
       to `KnowledgeBaseAgent` (ServiceNow & Confluence RAG).
    4. Automatically draft an `IT4YouTicket` when `it_escalation_needed=True`.
    5. Maintain conversational memory (`chat_history`) and Neuro-SAN `sly_data` state.
    """

    INTENT_SAC_DIAGNOSTIC = "SAC_PLANNING_DIAGNOSTIC"
    INTENT_GENERAL_IT_RAG = "GENERAL_IT_RAG"

    SLA_TARGETS: Dict[str, str] = {
        "P1 - Critical": "1 Hour (Critical Outage)",
        "P2 - High": "4 Hours (High Impact - SAP BTP Planning L3)",
        "P3 - Medium": "24 Hours (Standard Governance / Lock Request)",
        "P4 - Low": "48 Hours (Advisory Request)",
    }

    def __init__(
        self,
        sac_diagnostic_agent: Optional[SACDiagnosticAgent] = None,
        knowledge_agent: Optional[KnowledgeBaseAgent] = None,
        ticketing_service: Optional[IT4YouTicketingService] = None,
        use_llm: bool = False,
    ) -> None:
        self.use_llm: bool = use_llm
        self.sac_diagnostic_agent: SACDiagnosticAgent = (
            sac_diagnostic_agent or SACDiagnosticAgent(use_llm=use_llm)
        )
        self.knowledge_agent: KnowledgeBaseAgent = (
            knowledge_agent or KnowledgeBaseAgent(use_llm_rerank=use_llm)
        )
        self.ticketing_service: IT4YouTicketingService = (
            ticketing_service or IT4YouTicketingService()
        )
        self.chat_history: List[Dict[str, Any]] = []
        self.sly_data: Dict[str, Any] = {
            "session_queries": [],
            "it4you_tickets": [],
            "last_routed_agent": None,
        }

    # -----------------------------------------------------------------------
    # 1. Fast Intent Classification (AAOSA Claims + Gemini Classifier)
    # -----------------------------------------------------------------------
    def classify_intent(
        self,
        query: str,
        use_llm: Optional[bool] = None,
    ) -> str:
        """
        Classify user intent into 'SAC_PLANNING_DIAGNOSTIC' or 'GENERAL_IT_RAG'.
        Combines deterministic symbolic rules / AAOSA Determine claims with an
        optional fast Gemini LLM classification call.
        """
        active_use_llm = self.use_llm if use_llm is None else use_llm
        q_lower = (query or "").lower().strip()

        # Strong deterministic signals for General IT / RAG (SSO, VPN, SAML, Division by zero, Concurrency)
        rag_signals = (
            "sso",
            "vpn",
            "saml",
            "cookie",
            "cookies",
            "dns",
            "tunnel",
            "v4.2",
            "504",
            "connection timeout",
            "login",
            "authentication",
            "division by zero",
            "ndiv0",
            "showing na",
            "data collision",
            "concurrent schedulers",
        )
        planning_signals = (
            "70k",
            "52k",
            "70000",
            "52000",
            "travel expense",
            "exp_travel",
            "adjustments vanished",
            "da_overhead_allocation",
            "headcount",
            "exp_headcount",
            "draft",
            "private.draft",
            "manager",
            "margin",
            "margin_pct",
            "sum up",
            "across columns",
            "across cost centers",
            "weighted_avg",
            "greyed out",
            "cannot edit",
            "january 2025",
            "jan 2025",
            "jan_2025",
            "locked",
        )

        has_rag_signal = any(sig in q_lower for sig in rag_signals)
        has_planning_signal = any(sig in q_lower for sig in planning_signals)

        if has_rag_signal and not has_planning_signal:
            return self.INTENT_GENERAL_IT_RAG
        if has_planning_signal and not has_rag_signal:
            return self.INTENT_SAC_DIAGNOSTIC

        # Optional fast Gemini LLM intent classification when ambiguous
        if active_use_llm and config.is_api_key_configured():
            try:
                classifier_prompt = (
                    "Classify the following user support query into exactly one token:\n"
                    "- SAC_PLANNING_DIAGNOSTIC (if about SAC planning values dropping/changing, "
                    "unpublished Private/Draft versions, Gross Margin % or formula aggregation rollups, "
                    "or locked/greyed-out planning cells/periods)\n"
                    "- GENERAL_IT_RAG (if about VPN, SSO, SAML login timeouts, browser cookies/DNS, "
                    "division by zero syntax, or general IT helpdesk SOPs)\n\n"
                    f"Query: {query}\n"
                    "Respond with ONLY 'SAC_PLANNING_DIAGNOSTIC' or 'GENERAL_IT_RAG'."
                )
                llm_label = config.generate_content_with_fallback(prompt=classifier_prompt).upper()
                if "GENERAL_IT_RAG" in llm_label:
                    return self.INTENT_GENERAL_IT_RAG
                if "SAC_PLANNING_DIAGNOSTIC" in llm_label:
                    return self.INTENT_SAC_DIAGNOSTIC
            except Exception:
                pass

        # Compare AAOSA Determine claims between the two specialist agents
        sac_claim = self.sac_diagnostic_agent.aaosa_determine(query)
        kb_claim = self.knowledge_agent.aaosa_determine(query)
        if sac_claim.get("Relevant") == "Yes" and sac_claim.get("Strength", 0) >= kb_claim.get("Strength", 0):
            return self.INTENT_SAC_DIAGNOSTIC
        return self.INTENT_GENERAL_IT_RAG

    # -----------------------------------------------------------------------
    # 2. Neuro-SAN 7-Step Logical Path Builder (for UI Tab 2)
    # -----------------------------------------------------------------------
    @staticmethod
    def build_7_step_logical_path(
        intent: str,
        diagnostic_result: Optional[DiagnosticResult],
        kb_matches: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Build the 7-Step deterministic evaluation checklist with ✅ / ❌ markers
        for the 'Neuro-SAN Logical Path' inspector tab.
        """
        if intent == SupervisorOrchestrator.INTENT_GENERAL_IT_RAG or diagnostic_result is None:
            top_kb = kb_matches[0] if kb_matches else {}
            return [
                {
                    "step": 1,
                    "operation": "Coordinate Capture",
                    "objective": "Identify cell coordinates (Account, Version, Cost Center, Time)",
                    "marker": "❌",
                    "status": "BYPASSED (General IT / RAG Query)",
                    "summary": "No SAC planning cell coordinates required; query classified as IT/RAG support.",
                },
                {
                    "step": 2,
                    "operation": "Change Log Query",
                    "objective": "Retrieve SAC Data Change Log in a 60-minute window",
                    "marker": "❌",
                    "status": "BYPASSED",
                    "summary": "Skipped SAC audit log lookup for non-planning connectivity/SOP inquiry.",
                },
                {
                    "step": 3,
                    "operation": "Actor Evaluation",
                    "objective": "Determine if modification actor was SYSTEM_SAC_SCHEDULER",
                    "marker": "❌",
                    "status": "NOT APPLICABLE",
                    "summary": "No scheduled Multi Action overwrite involved.",
                },
                {
                    "step": 4,
                    "operation": "Version Validation",
                    "objective": "Check for uncommitted Private.Draft_v1 vs Public version mismatch",
                    "marker": "❌",
                    "status": "NOT APPLICABLE",
                    "summary": "No version publish discrepancy involved.",
                },
                {
                    "step": 5,
                    "operation": "Aggregation Check",
                    "objective": "Inspect account metadata for FORMULA / WEIGHTED_AVG rollup",
                    "marker": "❌",
                    "status": "NOT APPLICABLE",
                    "summary": "No non-additive hierarchy rollup involved.",
                },
                {
                    "step": 6,
                    "operation": "Locking Status",
                    "objective": "Verify Data Locking Console slice state",
                    "marker": "❌",
                    "status": "NOT APPLICABLE",
                    "summary": "No locked time slice involved.",
                },
                {
                    "step": 7,
                    "operation": "Synthesis & Output (Enterprise KB RAG)",
                    "objective": "Ground response in ServiceNow & Confluence Knowledge Base",
                    "marker": "✅",
                    "status": "MATCHED",
                    "summary": (
                        f"Retrieved top record {top_kb.get('item_id', 'N/A')} "
                        f"({top_kb.get('source', 'KB')}) with match score "
                        f"{float(top_kb.get('match_score', 0.0)):.2f}."
                    ),
                },
            ]

        cat = diagnostic_result.root_cause_category
        coords = diagnostic_result.coordinates or {}
        is_overwrite = cat == CauseCategory.SYSTEM_OVERWRITE
        is_version = cat == CauseCategory.VERSION_MISMATCH
        is_agg = cat == CauseCategory.AGGREGATION_RULE
        is_locked = cat == CauseCategory.LOCKED_SLICE

        return [
            {
                "step": 1,
                "operation": "Coordinate Capture",
                "objective": "Parse query for target Account, Version, Cost Center, and Time",
                "marker": "✅",
                "status": "VERIFIED",
                "summary": (
                    f"Model={coords.get('model_id', 'CORP_FINANCE_PLANNING')} | "
                    f"Account={coords.get('Account')} | Version={coords.get('Version')} | "
                    f"CostCenter={coords.get('CostCenter')} | Time={coords.get('Time')}"
                ),
            },
            {
                "step": 2,
                "operation": "Change Log Query",
                "objective": "Retrieve SAC Data Change Log & Multi Action history (60m window)",
                "marker": "✅",
                "status": "EXECUTED",
                "summary": (
                    f"Inspected MockSACGateway audit trail ({len(diagnostic_result.audit_evidence)} "
                    f"relevant evidence record(s) loaded)."
                ),
            },
            {
                "step": 3,
                "operation": "Actor Evaluation",
                "objective": "Check if modification actor was SYSTEM_SAC_SCHEDULER / Multi Action",
                "marker": "✅" if is_overwrite else "❌",
                "status": "ROOT CAUSE MATCHED" if is_overwrite else "CLEARED",
                "summary": (
                    "Detected SYSTEM_SAC_SCHEDULER executing DA_OVERHEAD_ALLOCATION (70,000.00 -> 52,000.00)."
                    if is_overwrite
                    else "No unauthorized system scheduler overwrite detected for this coordinate."
                ),
            },
            {
                "step": 4,
                "operation": "Version Validation",
                "objective": "Verify if edits are isolated in uncommitted Private.Draft_v1",
                "marker": "✅" if is_version else "❌",
                "status": "ROOT CAUSE MATCHED" if is_version else "CLEARED",
                "summary": (
                    "Edits isolated in uncommitted Private.Draft_v1 (publish_status=UNPUBLISHED)."
                    if is_version
                    else "Target version state is consistent with viewer context."
                ),
            },
            {
                "step": 5,
                "operation": "Aggregation Check",
                "objective": "Verify account metadata for FORMULA or WEIGHTED_AVG rollup rules",
                "marker": "✅" if is_agg else "❌",
                "status": "ROOT CAUSE MATCHED" if is_agg else "CLEARED",
                "summary": (
                    "Account MARGIN_PCT uses FORMULA ([Gross Margin]/[Revenue]) and WEIGHTED_AVG rollup."
                    if is_agg
                    else "Account uses standard additive SUM aggregation."
                ),
            },
            {
                "step": 6,
                "operation": "Locking Status",
                "objective": "Query Data Locking Console configuration for time slice locks",
                "marker": "✅" if is_locked else "❌",
                "status": "ROOT CAUSE MATCHED" if is_locked else "CLEARED",
                "summary": (
                    "Time slice JAN_2025_PERIOD is LOCKED by finance.controller@cognizant.com."
                    if is_locked
                    else "Target planning time slice is UNLOCKED."
                ),
            },
            {
                "step": 7,
                "operation": "Synthesis & Output",
                "objective": "Ground Gemini LLM explanation + determine User Fix vs IT4You Escalation",
                "marker": "✅",
                "status": "COMPLETED",
                "summary": (
                    f"Root Cause: {cat.value} | "
                    f"User Fixable: {diagnostic_result.is_user_fixable} | "
                    f"IT4You Escalation Needed: {diagnostic_result.it_escalation_needed}"
                ),
            },
        ]

    # -----------------------------------------------------------------------
    # 3. Core Orchestration Entry Point
    # -----------------------------------------------------------------------
    def route_query(
        self,
        query: str,
        caller_email: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        use_llm: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Main Neuro-SAN Supervisor routing loop:
        1. Evaluates AAOSA Determine claims from SACDiagnosticAgent and KnowledgeBaseAgent.
        2. Classifies intent ('SAC_PLANNING_DIAGNOSTIC' vs 'GENERAL_IT_RAG').
        3. Executes the selected specialist agent and builds the 7-Step Logical Path,
           KB matches, and optional DRAFT IT4YouTicket.
        4. Stores turn in `self.chat_history` and `self.sly_data`.
        """
        active_use_llm = self.use_llm if use_llm is None else use_llm
        resolved_caller = caller_email or config.DEFAULT_CALLER_EMAIL

        sac_claim = self.sac_diagnostic_agent.aaosa_determine(query)
        kb_claim = self.knowledge_agent.aaosa_determine(query)
        intent = self.classify_intent(query=query, use_llm=active_use_llm)

        diagnostic_result: Optional[DiagnosticResult] = None
        kb_matches: List[Dict[str, Any]] = self.knowledge_agent.search_knowledge_base(
            query=query,
            limit=3,
        )
        draft_ticket: Optional[IT4YouTicket] = None

        if intent == self.INTENT_SAC_DIAGNOSTIC:
            diagnostic_result = self.sac_diagnostic_agent.run_diagnosis(
                query=query,
                context=context,
                use_llm=active_use_llm,
            )
            # Safe State Fallback per rootsense.md Section 6:
            # If the 7-step tree returns UNKNOWN, fall back to Enterprise Knowledge Base RAG
            if diagnostic_result.root_cause_category == CauseCategory.UNKNOWN and kb_matches:
                intent = self.INTENT_GENERAL_IT_RAG
            else:
                routed_agent = "SACDiagnosticAgent"
                assistant_message = (
                    diagnostic_result.explanation or diagnostic_result.detected_cause
                )
                if diagnostic_result.it_escalation_needed or not diagnostic_result.is_user_fixable:
                    draft_ticket = self.ticketing_service.create_escalation_ticket(
                        diagnostic_result=diagnostic_result,
                        caller_email=resolved_caller,
                        status="DRAFT",
                    )

        if intent == self.INTENT_GENERAL_IT_RAG:
            routed_agent = "KnowledgeBaseAgent"
            rag_synthesis = self.knowledge_agent.synthesize_rag_response(
                query=query,
                limit=3,
                use_llm=active_use_llm,
            )
            kb_matches = rag_synthesis.get("matches", kb_matches)
            top_match = rag_synthesis.get("top_match") or (kb_matches[0] if kb_matches else None)

            if top_match:
                is_fixable = bool(top_match.get("is_user_fixable", True))
                assistant_message = (
                    f"### Enterprise Knowledge Base Resolution ({top_match['source']}: `{top_match['item_id']}`)\n"
                    f"**Matched Article / Incident**: {top_match['title']}\n\n"
                    f"**Category**: `{top_match['category']}` | "
                    f"**Confidence Score**: `{top_match['match_score'] * 100:.1f}%`\n\n"
                    f"**Recommended Resolution**:\n{top_match['resolution']}"
                )
                # Build a companion DiagnosticResult wrapper so downstream consumers have uniform access
                diagnostic_result = DiagnosticResult(
                    detected_cause=f"[{top_match['source']} {top_match['item_id']}] {top_match['title']}",
                    root_cause_category=CauseCategory.UNKNOWN,
                    audit_evidence=[top_match],
                    is_user_fixable=is_fixable,
                    user_resolution_steps=[top_match["resolution"]] if is_fixable else None,
                    it_escalation_needed=not is_fixable,
                    technical_brief=None,
                    explanation=assistant_message,
                    coordinates={
                        "model_id": config.SAC_DEFAULT_MODEL_ID,
                        "Account": "N/A (Enterprise KB RAG)",
                        "Version": "N/A",
                        "CostCenter": "N/A",
                        "Time": "N/A",
                    },
                )
            else:
                assistant_message = rag_synthesis.get(
                    "grounded_answer",
                    "No matching records found in ServiceNow or Confluence.",
                )

        logical_path = self.build_7_step_logical_path(
            intent=intent,
            diagnostic_result=diagnostic_result,
            kb_matches=kb_matches,
        )

        it_escalation_needed = (
            bool(diagnostic_result.it_escalation_needed)
            if diagnostic_result is not None
            else False
        )
        is_user_fixable = (
            bool(diagnostic_result.is_user_fixable)
            if diagnostic_result is not None
            else True
        )

        response_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "query": query,
            "intent": intent,
            "routed_agent": routed_agent,
            "assistant_message": assistant_message,
            "diagnostic_result": diagnostic_result,
            "root_cause_category": (
                diagnostic_result.root_cause_category.value
                if diagnostic_result is not None
                else CauseCategory.UNKNOWN.value
            ),
            "audit_evidence": (
                diagnostic_result.audit_evidence if diagnostic_result is not None else []
            ),
            "coordinates": (
                diagnostic_result.coordinates if diagnostic_result is not None else {}
            ),
            "is_user_fixable": is_user_fixable,
            "user_resolution_steps": (
                diagnostic_result.user_resolution_steps
                if diagnostic_result is not None
                else None
            ),
            "it_escalation_needed": it_escalation_needed,
            "it4you_ticket": draft_ticket.to_contract_dict() if draft_ticket else None,
            "it4you_ticket_model": draft_ticket,
            "kb_matches": kb_matches,
            "seven_step_checklist": logical_path,
            "aaosa_claims": {
                "SACDiagnosticAgent": sac_claim,
                "KnowledgeBaseAgent": kb_claim,
            },
        }

        # Record in conversational memory and Neuro-SAN sly_data
        self.chat_history.append({"role": "user", "content": query})
        self.chat_history.append(
            {
                "role": "assistant",
                "content": assistant_message,
                "metadata": response_payload,
            }
        )
        self.sly_data["last_routed_agent"] = routed_agent
        self.sly_data["session_queries"].append(
            {
                "query": query,
                "intent": intent,
                "routed_agent": routed_agent,
                "root_cause_category": response_payload["root_cause_category"],
            }
        )
        if draft_ticket:
            self.sly_data["it4you_tickets"].append(draft_ticket.to_contract_dict())

        return response_payload

    def submit_escalation_ticket(
        self,
        ticket_or_id: Union[IT4YouTicket, Dict[str, Any], str],
    ) -> Dict[str, Any]:
        """
        Submit a drafted IT4You ticket on the user's behalf and return the
        updated ticket payload with SLA metadata.
        """
        submitted = self.ticketing_service.submit_ticket(ticket_or_id)
        sla_target = self.SLA_TARGETS.get(
            submitted.priority,
            "4 Hours (SAP BTP Planning L3 Standard SLA)",
        )
        ticket_dict = submitted.to_contract_dict()
        return {
            "submitted_ticket": ticket_dict,
            "ticket_id": submitted.ticket_id,
            "status": submitted.status,
            "routing_group": submitted.suggested_routing_group,
            "priority": submitted.priority,
            "sla_target": sla_target,
            "confirmation_message": (
                f"Ticket **{submitted.ticket_id}** has been submitted to "
                f"**{submitted.suggested_routing_group}** with priority "
                f"**{submitted.priority}** (Target SLA: **{sla_target}**)."
            ),
        }

    def clear_history(self) -> None:
        """Reset conversation history and session sly_data."""
        self.chat_history.clear()
        self.sly_data["session_queries"] = []
        self.sly_data["last_routed_agent"] = None

    # Aliases for flexible invocation across FastAPI, Streamlit, and tests
    process_query = route_query
    handle_query = route_query
    run = route_query


# Backwards-compatible alias
NeuroSANSupervisor = SupervisorOrchestrator

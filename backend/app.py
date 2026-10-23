"""
Centralized FastAPI Entry Point for RootSense for SAC Diagnostic Engine.
Exposes REST API endpoints for health verification, Neuro-SAN Supervisor
chat/diagnostic routing, and IT4You escalation ticket submission.
Grounded strictly in rootsense.md.
"""

from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from backend import config
from backend.agents.supervisor import SupervisorOrchestrator
from backend.ticketing.it4you_service import IT4YouTicket

app = FastAPI(
    title="RootSense for SAC Diagnostic Engine",
    description=(
        "Neuro-Symbolic Agentic AI Diagnostic Assistant for SAP Analytics Cloud (SAC) "
        "Planning, Enterprise KB RAG (ServiceNow & Confluence), and IT4You Ticketing."
    ),
    version="1.0.0",
)

# Default SupervisorOrchestrator instance bound to app state and module scope
supervisor = SupervisorOrchestrator(use_llm=False)
app.state.supervisor = supervisor


class ChatRequest(BaseModel):
    """Request contract for POST /api/chat (and POST /api/diagnose)."""

    query: str = Field(..., min_length=1, description="User diagnostic or IT support query")
    coordinates: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional SAC planning cell coordinates (Account, Version, CostCenter, Time)",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional additional context dictionary",
    )
    caller_email: Optional[str] = Field(
        default=config.DEFAULT_CALLER_EMAIL,
        description="Caller email for audit and IT4You ticket attribution",
    )
    use_llm: bool = Field(
        default=False,
        description="Whether to invoke live Gemini neural synthesis in addition to symbolic rules",
    )


def _get_active_supervisor() -> SupervisorOrchestrator:
    """Return the active SupervisorOrchestrator attached to app.state."""
    return getattr(app.state, "supervisor", supervisor)


@app.get("/health")
def health_check(
    live_ping: bool = Query(
        default=False,
        description="Set True to execute a live network round-trip against Google Gemini API",
    ),
) -> Dict[str, Any]:
    """
    Check general application state, Mock SAC configuration toggles, fixture availability,
    and Google Gemini API client readiness/connectivity.
    """
    client = config.get_gemini_client()
    key_ready = config.is_api_key_configured()
    fixtures_ready = all(
        p.exists()
        for p in (
            config.SAC_CHANGE_LOG_PATH,
            config.SAC_METADATA_PATH,
            config.SERVICENOW_KB_PATH,
            config.CONFLUENCE_KB_PATH,
        )
    )

    gemini_connectivity: Dict[str, Any] = {
        "client_initialized": client is not None,
        "registered_model": config.GEMINI_MODEL_NAME,
        "fallback_pool": list(config.FALLBACK_FLASH_MODELS),
        "api_key_configured": key_ready,
        "ssl_ca_bundle_loaded": config.ACTIVE_CA_BUNDLE is not None,
    }
    if live_ping:
        gemini_connectivity["live_verification"] = config.verify_gemini_connection()

    return {
        "status": "healthy" if fixtures_ready else "degraded",
        "service": "RootSense for SAC",
        "use_mock_sac": config.USE_MOCK_SAC,
        "mock_sac_gateway_online": config.USE_MOCK_SAC and fixtures_ready,
        "default_sac_model": config.SAC_DEFAULT_MODEL_ID,
        "submitted_tickets_path": str(config.SUBMITTED_TICKETS_PATH),
        "registered_model": config.GEMINI_MODEL_NAME,
        "api_key_configured": key_ready,
        "gemini": gemini_connectivity,
    }


@app.post("/api/chat")
@app.post("/api/diagnose")
def chat_endpoint(req: ChatRequest) -> Dict[str, Any]:
    """
    Process a user query and optional coordinates via SupervisorOrchestrator,
    returning either the 7-Step SAC Planning Diagnostic result or Enterprise KB RAG matches.
    """
    merged_context: Dict[str, Any] = {}
    if req.context:
        merged_context.update(req.context)
    if req.coordinates:
        merged_context.update(req.coordinates)

    active_sup = _get_active_supervisor()
    result = active_sup.route_query(
        query=req.query,
        caller_email=req.caller_email,
        context=merged_context if merged_context else None,
        use_llm=req.use_llm,
    )

    serializable = dict(result)
    if serializable.get("diagnostic_result") is not None:
        diag_obj = serializable["diagnostic_result"]
        serializable["diagnostic_result"] = (
            diag_obj.model_dump() if hasattr(diag_obj, "model_dump") else diag_obj
        )
    serializable.pop("it4you_ticket_model", None)
    return serializable


@app.post("/api/ticket/submit")
@app.post("/api/tickets/submit")
def submit_ticket_endpoint(
    payload: Dict[str, Any] = Body(
        ...,
        description="Full IT4YouTicket JSON object, {'ticket': {...}}, or {'ticket_id': 'IT4U-2026-XXXXX'}",
    ),
) -> Dict[str, Any]:
    """
    Accept an IT4YouTicket payload (or ticket_id), validate it against the Section 5
    contract, transition its status to SUBMITTED, and persist it to
    backend/mock_sac/data/submitted_tickets.json.
    """
    active_sup = _get_active_supervisor()
    ticketing_svc = active_sup.ticketing_service

    try:
        if "ticket" in payload and isinstance(payload["ticket"], dict):
            ticket_input: Any = IT4YouTicket(**payload["ticket"])
        elif "title" in payload and "system_context" in payload:
            ticket_input = IT4YouTicket(**payload)
        elif "ticket_id" in payload and len(payload) == 1:
            ticket_input = str(payload["ticket_id"])
        else:
            ticket_input = IT4YouTicket(**payload)

        submission = active_sup.submit_escalation_ticket(ticket_input)
        validation = ticketing_svc.validate_ticket_payload(submission["submitted_ticket"])
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=422,
                detail=f"Ticket validation failed: {validation}",
            )

        return {
            **submission,
            "validation": validation,
            "storage_path": str(ticketing_svc.storage_path),
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

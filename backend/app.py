"""
FastAPI API Server for RootSense SAC Diagnostic Engine.
Exposes REST endpoints for the Neuro-SAN SupervisorOrchestrator, 7-Step SAC
Diagnostic Engine, Enterprise Knowledge Base RAG, and IT4You Ticketing Bridge.
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from backend import config
from backend.agents.supervisor import SupervisorOrchestrator

app = FastAPI(
    title="RootSense for SAC Diagnostic Engine",
    description="Neuro-Symbolic Agentic AI Diagnostic Assistant for SAP Analytics Cloud Planning",
    version="1.0.0",
)

supervisor = SupervisorOrchestrator(use_llm=False)


class DiagnoseRequest(BaseModel):
    query: str = Field(..., description="User diagnostic or IT support query")
    caller_email: Optional[str] = Field(default=config.DEFAULT_CALLER_EMAIL)
    context: Optional[Dict[str, Any]] = Field(default=None)
    use_llm: bool = Field(default=False)


class TicketSubmitRequest(BaseModel):
    ticket_id: str = Field(..., description="Draft IT4You Ticket ID to submit")


@app.get("/health")
def health_check() -> dict:
    """Return service and LLM configuration health status."""
    return {
        "status": "healthy",
        "service": "RootSense for SAC",
        "registered_model": config.GEMINI_MODEL_NAME,
        "default_sac_model": config.SAC_DEFAULT_MODEL_ID,
        "api_key_configured": config.is_api_key_configured(),
        "mock_sac_gateway_online": config.USE_MOCK_SAC,
    }


@app.post("/api/diagnose")
def diagnose_endpoint(req: DiagnoseRequest) -> Dict[str, Any]:
    """Execute the Neuro-SAN Supervisor routing loop for a user query."""
    result = supervisor.route_query(
        query=req.query,
        caller_email=req.caller_email,
        context=req.context,
        use_llm=req.use_llm,
    )
    # Convert Pydantic models to serializable dicts
    serializable = dict(result)
    if serializable.get("diagnostic_result") is not None:
        serializable["diagnostic_result"] = serializable["diagnostic_result"].model_dump()
    serializable.pop("it4you_ticket_model", None)
    return serializable


@app.post("/api/tickets/submit")
def submit_ticket_endpoint(req: TicketSubmitRequest) -> Dict[str, Any]:
    """Submit a drafted IT4You ticket on the user's behalf."""
    try:
        return supervisor.submit_escalation_ticket(req.ticket_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

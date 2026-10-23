"""
End-to-End Client Showcase Scenario Validation Suite (Prompt 7).
Validates all 4 core business presentation flows and the FastAPI REST endpoints
completely offline using deterministic fixtures and SupervisorOrchestrator.

Scenarios tested:
1. Scenario 1 (Scheduler Overwrite): Travel expenses dropping from 70K to 52K ->
   identifies DA_OVERHEAD_ALLOCATION by SYSTEM_SAC_SCHEDULER, marks as not user-fixable,
   and drafts a P2 - High IT4You escalation ticket.
2. Scenario 2 (Private Version): Headcount edits in draft not visible to manager ->
   identifies Private.Draft_v1, marks as user-fixable, and returns the 4-step
   Version Management publish instructions.
3. Scenario 3 (Non-Additive Margin %): Regional Gross Margin % not summing up across columns ->
   explains FORMULA ([Gross Margin]/[Revenue]) and WEIGHTED_AVG rollup math.
4. Scenario 4 (VPN SSO Login): Corporate VPN SSO errors -> SupervisorOrchestrator routes
   to KnowledgeBaseAgent and retrieves ServiceNow incident INC0088231 from disk.
5. FastAPI Endpoints (GET /health, POST /api/chat, POST /api/ticket/submit ->
   writes validated IT4YouTicket to backend/mock_sac/data/submitted_tickets.json).
"""

import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import config
from backend.agents.sac_diagnostic import CauseCategory
from backend.agents.supervisor import SupervisorOrchestrator
from backend.app import app
from backend.ticketing.it4you_service import IT4YouTicket, IT4YouTicketingService


@pytest.fixture()
def offline_supervisor(tmp_path: Path) -> SupervisorOrchestrator:
    """
    Fixture providing an offline SupervisorOrchestrator instance backed by
    the deterministic MockSACGateway, KnowledgeBaseAgent, and an isolated
    IT4YouTicketingService storage file.
    """
    ticket_store = tmp_path / "scenario_submitted_tickets.json"
    ticketing_svc = IT4YouTicketingService(storage_path=ticket_store)
    return SupervisorOrchestrator(
        ticketing_service=ticketing_svc,
        use_llm=False,
    )


@pytest.fixture()
def api_client() -> TestClient:
    """Fixture providing a FastAPI TestClient bound to backend.app."""
    return TestClient(app)


def test_scenario_1_scheduler_overwrite(offline_supervisor: SupervisorOrchestrator) -> None:
    """
    Scenario 1 (Scheduler Overwrite):
    Triggers when asking about travel expenses dropping from 70K to 52K.
    Asserts that the response:
    - Identifies systemic overwrite from Multi Action 'DA_OVERHEAD_ALLOCATION'
      executed by 'SYSTEM_SAC_SCHEDULER'.
    - Marks the issue as not user-fixable (is_user_fixable is False, it_escalation_needed is True).
    - Automatically drafts a P2 - High priority IT4You escalation ticket.
    """
    query = (
        "Why did my travel expense in Public.Forecast_2025 drop from 70,000 to 52,000? "
        "My manual adjustments vanished!"
    )
    response = offline_supervisor.route_query(
        query=query,
        caller_email="analyst.user@cognizant.com",
        use_llm=False,
    )

    assert response["intent"] == SupervisorOrchestrator.INTENT_SAC_DIAGNOSTIC
    assert response["routed_agent"] == "SACDiagnosticAgent"
    assert response["root_cause_category"] == CauseCategory.SYSTEM_OVERWRITE.value
    assert response["is_user_fixable"] is False
    assert response["it_escalation_needed"] is True

    # Verify explanation identifies DA_OVERHEAD_ALLOCATION and SYSTEM_SAC_SCHEDULER
    explanation = response["assistant_message"]
    assert "DA_OVERHEAD_ALLOCATION" in explanation
    assert "SYSTEM_SAC_SCHEDULER" in explanation
    assert "70,000" in explanation or "70000" in explanation
    assert "52,000" in explanation or "52000" in explanation

    # Verify drafted P2 priority escalation ticket
    ticket = response["it4you_ticket"]
    assert ticket is not None
    assert ticket["ticket_id"].startswith("IT4U-2026-")
    assert ticket["priority"] == "P2 - High"
    assert ticket["suggested_routing_group"] == "SAP-BTP-PLANNING-L3"
    assert ticket["status"] == "DRAFT"
    assert "DA_OVERHEAD_ALLOCATION" in ticket["technical_diagnostic_brief"]


def test_scenario_2_private_version_mismatch(offline_supervisor: SupervisorOrchestrator) -> None:
    """
    Scenario 2 (Private Version):
    Triggers when asking why headcount edits in draft aren't visible to a manager.
    Asserts that the response:
    - Identifies uncommitted 'Private.Draft_v1'.
    - Marks the issue as user-fixable (is_user_fixable is True, it_escalation_needed is False).
    - Includes the 4-step Version Management publish instructions.
    """
    query = (
        "Why aren't my EXP_HEADCOUNT updates in Private.Draft_v1 showing up "
        "for my manager in Public.Forecast_2025?"
    )
    response = offline_supervisor.route_query(
        query=query,
        caller_email="analyst.user@cognizant.com",
        use_llm=False,
    )

    assert response["intent"] == SupervisorOrchestrator.INTENT_SAC_DIAGNOSTIC
    assert response["routed_agent"] == "SACDiagnosticAgent"
    assert response["root_cause_category"] == CauseCategory.VERSION_MISMATCH.value
    assert response["is_user_fixable"] is True
    assert response["it_escalation_needed"] is False
    assert response["it4you_ticket"] is None

    # Verify explanation references Private.Draft_v1
    explanation = response["assistant_message"]
    assert "Private.Draft_v1" in explanation

    # Verify 4-step Version Management publish instructions
    steps = response["user_resolution_steps"]
    assert isinstance(steps, list)
    assert len(steps) == 4
    joined_steps = " ".join(steps)
    assert "Version Management" in joined_steps
    assert "Private.Draft_v1" in joined_steps
    assert "Publish" in joined_steps


def test_scenario_3_non_additive_margin_percentage(offline_supervisor: SupervisorOrchestrator) -> None:
    """
    Scenario 3 (Non-Additive Margin %):
    Triggers when asking why regional margin percentages don't sum up across columns.
    Asserts that the response:
    - Classifies root cause as NON_ADDITIVE_AGGREGATION (AGGREGATION_RULE).
    - Correctly explains formula/weighted average aggregation math ([Gross Margin]/[Revenue],
      FORMULA, WEIGHTED_AVG).
    - Marks the issue as user-fixable (is_user_fixable is True, it_escalation_needed is False).
    """
    query = (
        "Why does Gross Margin % (MARGIN_PCT) not sum up across regional cost center columns "
        "in the parent hierarchy node?"
    )
    response = offline_supervisor.route_query(
        query=query,
        caller_email="analyst.user@cognizant.com",
        use_llm=False,
    )

    assert response["intent"] == SupervisorOrchestrator.INTENT_SAC_DIAGNOSTIC
    assert response["routed_agent"] == "SACDiagnosticAgent"
    assert response["root_cause_category"] == CauseCategory.AGGREGATION_RULE.value
    assert response["is_user_fixable"] is True
    assert response["it_escalation_needed"] is False
    assert response["it4you_ticket"] is None

    explanation = response["assistant_message"]
    assert "[Gross Margin]/[Revenue]" in explanation
    assert "FORMULA" in explanation
    assert "WEIGHTED_AVG" in explanation


def test_scenario_4_vpn_sso_login_rag(offline_supervisor: SupervisorOrchestrator) -> None:
    """
    Scenario 4 (VPN SSO Login):
    Triggers when asking about corporate VPN SSO errors.
    Asserts that:
    - SupervisorOrchestrator classifies intent as GENERAL_IT_RAG and routes to KnowledgeBaseAgent.
    - Retrieves ServiceNow incident INC0088231 ("VPN SSO Connection Timeout to SAC Tenant") from disk.
    - Includes SAML 2.0 corporate token / v4.2 tunnel resolution instructions.
    """
    query = (
        "I am getting a VPN SSO Connection Timeout to SAC Tenant when logging in "
        "over the corporate tunnel."
    )
    response = offline_supervisor.route_query(
        query=query,
        caller_email="analyst.user@cognizant.com",
        use_llm=False,
    )

    assert response["intent"] == SupervisorOrchestrator.INTENT_GENERAL_IT_RAG
    assert response["routed_agent"] == "KnowledgeBaseAgent"
    assert len(response["kb_matches"]) >= 1

    top_match = response["kb_matches"][0]
    assert top_match["item_id"] == "INC0088231"
    assert top_match["source"] == "ServiceNow"
    assert "VPN SSO Connection Timeout" in top_match["title"]
    assert "SAML 2.0" in response["assistant_message"]
    assert "v4.2" in response["assistant_message"]


def test_fastapi_endpoints_and_ticket_submission_persistence(api_client: TestClient) -> None:
    """
    End-to-End FastAPI Endpoint Verification:
    1. GET /health verifies Mock SAC Gateway status and Gemini client configuration.
    2. POST /api/chat processes Scenario 1 and returns the diagnostic payload + DRAFT ticket.
    3. POST /api/ticket/submit accepts a Pydantic IT4YouTicket object, validates it,
       and persists it with status='SUBMITTED' to backend/mock_sac/data/submitted_tickets.json.
    """
    # 1. GET /health
    health_resp = api_client.get("/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert health_data["status"] == "healthy"
    assert health_data["use_mock_sac"] is True
    assert health_data["mock_sac_gateway_online"] is True
    assert health_data["gemini"]["client_initialized"] is True

    # 2. POST /api/chat (Scenario 1)
    chat_resp = api_client.post(
        "/api/chat",
        json={
            "query": "Why did my travel expense drop from 70,000 to 52,000 in Public.Forecast_2025?",
            "coordinates": {
                "Account": "EXP_TRAVEL_ENTERTAINMENT",
                "Version": "Public.Forecast_2025",
                "CostCenter": "CC_NA_1020",
                "Time": "202509",
            },
            "caller_email": "analyst.user@cognizant.com",
            "use_llm": False,
        },
    )
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["routed_agent"] == "SACDiagnosticAgent"
    assert chat_data["root_cause_category"] == CauseCategory.SYSTEM_OVERWRITE.value
    draft_ticket_payload = chat_data["it4you_ticket"]
    assert draft_ticket_payload is not None
    assert draft_ticket_payload["priority"] == "P2 - High"

    # 3. POST /api/ticket/submit -> writes to backend/mock_sac/data/submitted_tickets.json
    target_file = config.SUBMITTED_TICKETS_PATH
    ticket_obj = IT4YouTicket(**draft_ticket_payload)
    submit_resp = api_client.post(
        "/api/ticket/submit",
        json=ticket_obj.model_dump(mode="json"),
    )
    assert submit_resp.status_code == 200
    submit_data = submit_resp.json()
    assert submit_data["status"] == "SUBMITTED"
    assert submit_data["validation"]["is_valid"] is True
    assert Path(submit_data["storage_path"]).resolve() == target_file.resolve()

    # Verify that backend/mock_sac/data/submitted_tickets.json exists and contains the SUBMITTED ticket
    assert target_file.exists()
    persisted_records = json.loads(target_file.read_text(encoding="utf-8"))
    assert isinstance(persisted_records, list)
    matching = [
        rec
        for rec in persisted_records
        if rec.get("ticket_id") == ticket_obj.ticket_id
    ]
    assert len(matching) == 1
    assert matching[0]["status"] == "SUBMITTED"
    assert matching[0]["priority"] == "P2 - High"

    # Keep only the latest submitted record in submitted_tickets.json so the showcase file remains clean
    target_file.write_text(json.dumps(matching, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

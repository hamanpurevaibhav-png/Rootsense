"""
Neuro-SAN CodedTool wrapper for the Automated IT4You L3 Ticketing Service.
Drafts and persists structured IT4You tickets inside `sly_data['it4you_tickets']`.
"""

from pathlib import Path
import sys
from typing import Any, Dict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from neuro_san.interfaces.coded_tool import CodedTool
except ImportError:
    class CodedTool:
        """Fallback CodedTool base class when neuro-san is not active."""

from backend import config  # noqa: E402
from backend.agents.sac_diagnostic import SACDiagnosticAgent  # noqa: E402
from backend.ticketing.it4you_service import IT4YouTicketingService  # noqa: E402


class IT4YouTicketingTool(CodedTool):
    """
    Drafts a structured IT4You escalation ticket from an SAC diagnostic outcome
    and records it inside `sly_data['it4you_tickets']`.
    """

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Dict[str, Any]:
        query = str(args.get("query", "")).strip()
        caller_email = str(args.get("caller_email", config.DEFAULT_CALLER_EMAIL)).strip()

        diag_agent = SACDiagnosticAgent(use_llm=False)
        diag = diag_agent.diagnose(query=query, use_llm=False)

        ticket_service = IT4YouTicketingService()
        ticket = ticket_service.draft_ticket_from_diagnosis(
            diagnosis=diag,
            caller_email=caller_email,
            user_query=query,
            sly_data=sly_data,
        )
        return ticket.model_dump(mode="json")

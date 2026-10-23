"""
Neuro-SAN CodedTool wrapper for the 7-Step SAC Planning Diagnostic Engine.
Allows `ns run` (NSFlow UI) to invoke `SACDiagnosticAgent` -> `SACAuditDiagnosticTool`
and persist structured evidence inside `sly_data`.
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

from backend.agents.sac_diagnostic import SACDiagnosticAgent  # noqa: E402


class SACAuditDiagnosticTool(CodedTool):
    """
    Executes the deterministic 7-Step Neuro-Symbolic SAC Planning Diagnostic Tree
    and writes structured coordinates & audit evidence into `sly_data`.
    """

    async def async_invoke(self, args: Dict[str, Any], sly_data: Dict[str, Any]) -> Dict[str, Any]:
        query = str(args.get("query", "")).strip()
        agent = SACDiagnosticAgent(use_llm=False)
        diag = agent.diagnose(query=query, use_llm=False)
        checklist = agent.get_seven_step_checklist(diag)

        payload = {
            "root_cause_category": diag.root_cause_category.value,
            "is_user_fixable": diag.is_user_fixable,
            "it_escalation_needed": not diag.is_user_fixable,
            "executive_summary": diag.executive_summary,
            "technical_evidence": diag.technical_evidence,
            "actionable_resolution": diag.actionable_resolution,
            "seven_step_checklist": checklist,
        }

        sly_data["active_diagnosis"] = payload
        if diag.technical_evidence and isinstance(diag.technical_evidence[0], dict):
            sly_data["sac_coordinates"] = diag.technical_evidence[0].get("coordinates", {})

        return payload

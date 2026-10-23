"""
Unit tests for the IT4You Escalation & Automated Ticketing Engine
(backend/ticketing/it4you_service.py).
Verifies Pydantic models, ticket ID regex format (IT4U-2026-XXXXX), markdown brief
generation, JSON serialization/persistence, and Neuro-SAN CodedTool sly_data tracking.
"""

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agents.sac_diagnostic import CauseCategory, SACDiagnosticAgent  # noqa: E402
from backend.ticketing.it4you_service import (  # noqa: E402
    IT4YouTicket,
    IT4YouTicketingService,
)


class TestIT4YouTicketingService(unittest.TestCase):
    """Validate IT4YouTicket Pydantic contract, persistence, and CodedTool execution."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_file = Path(self.temp_dir.name) / "test_it4you_tickets.json"
        self.service = IT4YouTicketingService(storage_path=self.storage_file)
        self.diag_agent = SACDiagnosticAgent(use_llm=False)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_01_system_overwrite_ticket_generation_and_validation(self) -> None:
        """Verify SYSTEM_OVERWRITE diagnosis produces a valid P2 - High IT4YouTicket."""
        diag = self.diag_agent.run_diagnosis(
            "Why did my Travel Expense entry drop from 70K to 52K?"
        )
        self.assertEqual(diag.root_cause_category, CauseCategory.SYSTEM_OVERWRITE)

        ticket = self.service.create_escalation_ticket(
            diagnostic_result=diag,
            caller_email="analyst.user@cognizant.com",
        )
        self.assertIsInstance(ticket, IT4YouTicket)
        self.assertRegex(ticket.ticket_id, r"^IT4U-2026-[A-Z0-9]{5}$")
        self.assertEqual(ticket.priority, "P2 - High")
        self.assertEqual(ticket.suggested_routing_group, "SAP-BTP-PLANNING-L3")
        self.assertEqual(ticket.category, "SAP Analytics Cloud / Planning COE")
        self.assertEqual(ticket.status, "DRAFT")
        self.assertIn("### ROOT CAUSE IDENTIFIED", ticket.technical_diagnostic_brief)
        self.assertIn("DA_OVERHEAD_ALLOCATION", ticket.technical_diagnostic_brief)

        validation = self.service.validate_ticket_payload(ticket)
        self.assertTrue(validation["is_valid"])

    def test_02_locked_slice_ticket_and_submission_persistence(self) -> None:
        """Verify LOCKED_SLICE diagnosis creates a DRAFT ticket, transitions to SUBMITTED, and saves JSON."""
        diag = self.diag_agent.run_diagnosis(
            "My planning cell for January 2025 is greyed out"
        )
        self.assertEqual(diag.root_cause_category, CauseCategory.LOCKED_SLICE)

        draft_ticket = self.service.create_escalation_ticket(diagnostic_result=diag)
        self.assertEqual(draft_ticket.status, "DRAFT")
        self.assertEqual(draft_ticket.priority, "P3 - Medium")
        self.assertTrue(self.storage_file.exists())

        submitted = self.service.submit_ticket(draft_ticket.ticket_id)
        self.assertEqual(submitted.status, "SUBMITTED")

        # Verify persisted JSON file is valid and has no trailing commas
        persisted_data = json.loads(self.storage_file.read_text(encoding="utf-8"))
        self.assertEqual(len(persisted_data), 1)
        self.assertEqual(persisted_data[0]["ticket_id"], draft_ticket.ticket_id)
        self.assertEqual(persisted_data[0]["status"], "SUBMITTED")

    def test_03_strict_validation_rejects_user_fixable_diagnosis(self) -> None:
        """Verify strict_validation=True prevents ticket creation for user-fixable issues."""
        diag = self.diag_agent.run_diagnosis(
            "I changed headcount in Draft but my manager/team doesn't see it"
        )
        self.assertTrue(diag.is_user_fixable)
        with self.assertRaises(ValueError):
            self.service.create_escalation_ticket(
                diagnostic_result=diag,
                strict_validation=True,
            )

    def test_04_neuro_san_coded_tool_async_invoke_sly_data(self) -> None:
        """Verify Neuro-SAN CodedTool async_invoke writes ticket into sly_data['it4you_tickets']."""
        diag = self.diag_agent.run_diagnosis(
            "Why did my Travel Expense entry drop from 70K to 52K?"
        )
        sly_data: dict = {}
        result_dict = asyncio.run(
            self.service.async_invoke(
                args={
                    "diagnostic_result": diag,
                    "caller_email": "controller@cognizant.com",
                    "submit": True,
                },
                sly_data=sly_data,
            )
        )
        self.assertEqual(result_dict["status"], "SUBMITTED")
        self.assertEqual(result_dict["caller_email"], "controller@cognizant.com")
        self.assertEqual(len(sly_data["it4you_tickets"]), 1)
        self.assertEqual(
            sly_data["it4you_tickets"][0]["ticket_id"],
            result_dict["ticket_id"],
        )


if __name__ == "__main__":
    print("=" * 72)
    print("RootSense SAC - Prompt 5: IT4You Ticketing Engine Unit Tests")
    print("=" * 72)
    unittest.main(verbosity=2)

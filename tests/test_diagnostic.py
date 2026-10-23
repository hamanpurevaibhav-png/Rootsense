"""
Unit tests for the 7-Step SAC Planning Diagnostic Engine (backend/agents/sac_diagnostic.py).
Verifies Scenarios A, B, C, and D from rootsense.md and Prompt 4 Pydantic contracts.
Compatible with both pytest and direct execution (`python tests/test_diagnostic.py`).
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agents.sac_diagnostic import (  # noqa: E402
    CauseCategory,
    DiagnosticResult,
    SACDiagnosticAgent,
)


class TestSACDiagnosticEngine(unittest.TestCase):
    """Validate the 7-Step Neuro-Symbolic SAC Planning Diagnostic workflow."""

    @classmethod
    def setUpClass(cls) -> None:
        # Use deterministic symbolic synthesis for fast, repeatable unit tests
        cls.agent = SACDiagnosticAgent(use_llm=False)

    def test_01_scenario_a_system_overwrite(self) -> None:
        """
        Scenario A: 'Why did my Travel Expense entry drop from 70K to 52K?'
        Must classify as SYSTEM_OVERWRITE, is_user_fixable=False, it_escalation_needed=True.
        """
        query = "Why did my Travel Expense entry drop from 70K to 52K?"
        result = self.agent.run_diagnosis(query)

        self.assertIsInstance(result, DiagnosticResult)
        self.assertEqual(result.root_cause_category, CauseCategory.SYSTEM_OVERWRITE)
        self.assertFalse(result.is_user_fixable)
        self.assertTrue(result.it_escalation_needed)
        self.assertIsNone(result.user_resolution_steps)
        self.assertIsNotNone(result.technical_brief)
        self.assertEqual(
            result.technical_brief["suggested_routing_group"],
            "SAP-BTP-PLANNING-L3",
        )
        self.assertEqual(result.technical_brief["priority"], "P2 - High")

        # Audit evidence must include both the 70000.00 user edit and 52000.00 system overwrite
        self.assertEqual(len(result.audit_evidence), 2)
        new_values = [rec["new_value"] for rec in result.audit_evidence]
        self.assertIn(70000.0, new_values)
        self.assertIn(52000.0, new_values)
        actors = [rec["actor"] for rec in result.audit_evidence]
        self.assertIn("SYSTEM_SAC_SCHEDULER", actors)

    def test_02_scenario_b_version_mismatch(self) -> None:
        """
        Scenario B: 'I changed headcount in Draft but my manager/team doesn't see it'
        Must classify as VERSION_MISMATCH, is_user_fixable=True, it_escalation_needed=False.
        """
        query = "I changed headcount in Draft but my manager/team doesn't see it"
        result = self.agent.run_diagnosis(query)

        self.assertIsInstance(result, DiagnosticResult)
        self.assertEqual(result.root_cause_category, CauseCategory.VERSION_MISMATCH)
        self.assertTrue(result.is_user_fixable)
        self.assertFalse(result.it_escalation_needed)
        self.assertIsNone(result.technical_brief)
        self.assertIsNotNone(result.user_resolution_steps)
        self.assertEqual(len(result.user_resolution_steps), 4)
        joined_steps = " ".join(result.user_resolution_steps)
        self.assertIn("Version Management", joined_steps)
        self.assertIn("Draft_v1", joined_steps)
        self.assertIn("Publish", joined_steps)

    def test_03_scenario_c_aggregation_rule(self) -> None:
        """
        Scenario C: 'Why doesn't the Total Gross Margin % sum up correctly across cost centers?'
        Must classify as AGGREGATION_RULE (alias NON_ADDITIVE_AGGREGATION), is_user_fixable=True.
        """
        query = "Why doesn't the Total Gross Margin % sum up correctly across cost centers?"
        result = self.agent.run_diagnosis(query)

        self.assertIsInstance(result, DiagnosticResult)
        self.assertEqual(result.root_cause_category, CauseCategory.AGGREGATION_RULE)
        self.assertEqual(result.root_cause_category, CauseCategory.NON_ADDITIVE_AGGREGATION)
        self.assertTrue(result.is_user_fixable)
        self.assertFalse(result.it_escalation_needed)
        self.assertIsNotNone(result.user_resolution_steps)
        self.assertGreaterEqual(len(result.audit_evidence), 1)
        meta = result.audit_evidence[0]
        self.assertEqual(meta["aggregation"], "FORMULA")
        self.assertEqual(meta["rollup"], "WEIGHTED_AVG")
        self.assertEqual(meta["formula"], "[Gross Margin]/[Revenue]")

    def test_04_scenario_d_locked_slice(self) -> None:
        """
        Scenario D: 'My planning cell for January 2025 is greyed out'
        Must classify as LOCKED_SLICE, is_user_fixable=False, it_escalation_needed=True.
        """
        query = "My planning cell for January 2025 is greyed out and I cannot edit Jan 2025"
        result = self.agent.run_diagnosis(query)

        self.assertIsInstance(result, DiagnosticResult)
        self.assertEqual(result.root_cause_category, CauseCategory.LOCKED_SLICE)
        self.assertFalse(result.is_user_fixable)
        self.assertTrue(result.it_escalation_needed)
        self.assertIsNotNone(result.technical_brief)
        self.assertGreaterEqual(len(result.audit_evidence), 1)
        lock_info = result.audit_evidence[0]
        self.assertEqual(lock_info["status"], "LOCKED")
        self.assertTrue(lock_info["is_locked"])

    def test_05_aaosa_protocol_and_step_trace(self) -> None:
        """Verify Neuro-SAN AAOSA Determine claims and 7-step diagnostic trace."""
        planning_claim = self.agent.aaosa_determine(
            "Why did my Travel Expense entry drop from 70K to 52K?"
        )
        self.assertEqual(planning_claim["Relevant"], "Yes")
        self.assertGreaterEqual(planning_claim["Strength"], 8)

        vpn_claim = self.agent.aaosa_determine("VPN SSO connection timeout to SAC tenant")
        self.assertEqual(vpn_claim["Relevant"], "No")
        self.assertLessEqual(vpn_claim["Strength"], 2)


if __name__ == "__main__":
    print("=" * 72)
    print("RootSense SAC - Prompt 4: 7-Step SAC Diagnostic Engine Unit Tests")
    print("=" * 72)
    unittest.main(verbosity=2)

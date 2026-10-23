"""
Unit tests for the Enterprise Knowledge Base RAG Agent (backend/agents/knowledge_agent.py)
and corporate KB fixtures (servicenow_kb.json & confluence_kb.json).
Compatible with both pytest and direct execution (`python tests/test_kb.py`).
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend import config  # noqa: E402
from backend.agents.knowledge_agent import KnowledgeBaseAgent  # noqa: E402


class TestKnowledgeBaseAgent(unittest.TestCase):
    """Validate ServiceNow & Confluence RAG indexing, search cards, and ranking accuracy."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.kb_agent = KnowledgeBaseAgent()

    def test_01_corpus_loading_and_counts(self) -> None:
        """Verify exactly 5 ServiceNow tickets and 4 Confluence SOP pages load via config.py."""
        self.assertTrue(config.SERVICENOW_KB_PATH.exists())
        self.assertTrue(config.CONFLUENCE_KB_PATH.exists())
        self.assertEqual(len(self.kb_agent.servicenow_records), 5)
        self.assertEqual(len(self.kb_agent.confluence_records), 4)
        self.assertEqual(len(self.kb_agent.documents), 9)

    def test_02_sso_vpn_query_returns_inc0088231_top(self) -> None:
        """Verify a query containing 'SSO VPN' returns INC0088231 with the highest match score."""
        results = self.kb_agent.search_knowledge_base("SSO VPN connection timeout to SAC tenant", limit=3)
        self.assertGreaterEqual(len(results), 1)

        top_card = results[0]
        self.assertEqual(top_card["item_id"], "INC0088231")
        self.assertEqual(top_card["source"], "ServiceNow")
        self.assertGreater(top_card["match_score"], 0.4)
        self.assertLessEqual(top_card["match_score"], 1.0)
        self.assertIn("SAML 2.0", top_card["resolution"])
        self.assertIn("v4.2", top_card["resolution"])

        # Also verify bare 'SSO VPN' query
        short_results = self.kb_agent.search_knowledge_base("SSO VPN", limit=3)
        self.assertEqual(short_results[0]["item_id"], "INC0088231")
        if len(short_results) > 1:
            self.assertGreater(short_results[0]["match_score"], short_results[1]["match_score"])

    def test_03_margin_percent_and_sum_up_percentages_returns_conf_sac_004(self) -> None:
        """Verify queries with 'Margin percent' or 'sum up percentages' retrieve CONF_SAC_004 cleanly."""
        res_margin = self.kb_agent.search_knowledge_base("Margin percent aggregation rules", limit=3)
        self.assertGreaterEqual(len(res_margin), 1)
        self.assertEqual(res_margin[0]["item_id"], "CONF_SAC_004")
        self.assertEqual(res_margin[0]["source"], "Confluence")
        self.assertIn("[Gross Margin] / [Revenue]", res_margin[0]["content"])

        res_sum_pct = self.kb_agent.search_knowledge_base(
            "Why doesn't Margin % sum up percentages across cost centers?",
            limit=3,
        )
        self.assertGreaterEqual(len(res_sum_pct), 1)
        self.assertEqual(res_sum_pct[0]["item_id"], "CONF_SAC_004")
        self.assertGreater(res_sum_pct[0]["match_score"], 0.35)
        self.assertLessEqual(res_sum_pct[0]["match_score"], 1.0)

    def test_04_search_card_schema_and_division_by_zero_lookup(self) -> None:
        """Verify search card structure and division-by-zero formula lookup (INC0076211)."""
        results = self.kb_agent.search_knowledge_base(
            "Calculated measure showing NA or Division by Zero error NDIV0",
            limit=3,
        )
        self.assertGreaterEqual(len(results), 1)
        top_card = results[0]
        self.assertEqual(top_card["item_id"], "INC0076211")

        required_keys = {"item_id", "id", "title", "category", "source", "match_score", "resolution", "content"}
        self.assertTrue(required_keys.issubset(set(top_card.keys())))
        self.assertIn("NDIV0", top_card["resolution"])

    def test_05_private_draft_and_aaosa_protocol(self) -> None:
        """Verify CONF_SAC_001 retrieval and Neuro-SAN AAOSA Determine/Fulfill responses."""
        results = self.kb_agent.search_knowledge_base(
            "Working with Private Draft Versions and Version Management Publish",
            limit=2,
        )
        self.assertEqual(results[0]["item_id"], "CONF_SAC_001")

        claim = self.kb_agent.aaosa_determine("SSO VPN login timeout")
        self.assertEqual(claim["Name"], "KnowledgeBaseAgent")
        self.assertEqual(claim["Mode"], "Determine")
        self.assertEqual(claim["Relevant"], "Yes")
        self.assertEqual(claim["TopMatchId"], "INC0088231")

        fulfilled = self.kb_agent.aaosa_fulfill("SSO VPN login timeout")
        self.assertEqual(fulfilled["Mode"], "Fulfill")
        self.assertEqual(fulfilled["Response"]["top_match"]["item_id"], "INC0088231")


if __name__ == "__main__":
    print("=" * 72)
    print("RootSense SAC - Prompt 3: Enterprise Knowledge Base RAG Unit Tests")
    print("=" * 72)
    unittest.main(verbosity=2)

"""
Comprehensive Unit Test Suite for the Mock SAC REST API Gateway & Data Fixtures.
Verifies:
  1. Change log retrieval for 'EXP_TRAVEL_ENTERTAINMENT' returning both the
     manual user edit (45000.00 -> 70000.00) and SYSTEM_SAC_SCHEDULER overwrite
     (70000.00 -> 52000.00 via DA_OVERHEAD_ALLOCATION).
  2. Private version ('Private.Draft_v1') change log retrieval for 'EXP_HEADCOUNT'
     confirming unpublished status.
  3. Multi-Action execution history retrieval for 'DA_OVERHEAD_ALLOCATION'.
  4. Account metadata verification for 'MARGIN_PCT' (FORMULA '[Gross Margin]/[Revenue]'
     with 'WEIGHTED_AVG' rollup) as well as 'EXP_TRAVEL_ENTERTAINMENT', 'REV_GROSS',
     and 'EXP_COGS'.
  5. Data Locking Console status check for 'JAN_2025_PERIOD' returning 'LOCKED'.
  6. USE_MOCK_SAC configuration toggle behavior.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import config
from backend.mock_sac.sac_gateway import MockSACGateway


class TestMockSACGateway(unittest.TestCase):
    """Pytest and unittest compatible test suite for MockSACGateway."""

    def setUp(self) -> None:
        self.gateway = MockSACGateway()
        self.model_id = "CORP_FINANCE_PLANNING"

    def test_01_use_mock_sac_flag_enabled(self) -> None:
        """Verify USE_MOCK_SAC toggle is enabled in backend/config.py."""
        self.assertTrue(config.USE_MOCK_SAC)
        self.assertTrue(self.gateway.use_mock_sac)

    def test_02_change_log_returns_user_edit_and_scheduler_overwrite(self) -> None:
        """
        Verify retrieving change logs for EXP_TRAVEL_ENTERTAINMENT returns both
        the user edit (70000.00) and the SYSTEM_SAC_SCHEDULER overwrite (52000.00).
        """
        result = self.gateway.get_data_change_log(
            model_id=self.model_id,
            version="Public.Forecast_2025",
            account="EXP_TRAVEL_ENTERTAINMENT",
            time_period="202509",
        )

        self.assertEqual(result["model_id"], self.model_id)
        self.assertEqual(result["total_records"], 2)
        self.assertTrue(result["has_system_overwrite"])

        records = result["records"]
        # Record 1: Manual user edit (45000.00 -> 70000.00 at 2025-09-15T10:14:00Z)
        rec_user = records[0]
        self.assertEqual(rec_user["actor"], "analyst.user@cognizant.com")
        self.assertEqual(rec_user["timestamp"], "2025-09-15T10:14:00Z")
        self.assertEqual(rec_user["old_value"], 45000.00)
        self.assertEqual(rec_user["new_value"], 70000.00)
        self.assertEqual(rec_user["coordinates"]["CostCenter"], "CC_NA_1020")

        # Record 2: System overwrite (70000.00 -> 52000.00 at 2025-09-15T10:30:00Z)
        rec_sys = records[1]
        self.assertEqual(rec_sys["actor"], "SYSTEM_SAC_SCHEDULER")
        self.assertEqual(rec_sys["timestamp"], "2025-09-15T10:30:00Z")
        self.assertEqual(rec_sys["multi_action_id"], "DA_OVERHEAD_ALLOCATION")
        self.assertEqual(rec_sys["old_value"], 70000.00)
        self.assertEqual(rec_sys["new_value"], 52000.00)

    def test_03_change_log_private_version_unpublished(self) -> None:
        """
        Verify Record 3 for EXP_HEADCOUNT in Private.Draft_v1 is captured
        as updated by user and unpublished.
        """
        result = self.gateway.get_data_change_log(
            model_id=self.model_id,
            version="Private.Draft_v1",
            account="EXP_HEADCOUNT",
            time_period="202509",
        )

        self.assertEqual(result["total_records"], 1)
        self.assertTrue(result["has_unpublished_private_edits"])

        record = result["records"][0]
        self.assertEqual(record["coordinates"]["Account"], "EXP_HEADCOUNT")
        self.assertEqual(record["coordinates"]["Version"], "Private.Draft_v1")
        self.assertEqual(record["publish_status"], "UNPUBLISHED")
        self.assertFalse(record["is_published"])

    def test_04_multi_action_history_retrieval(self) -> None:
        """Verify get_multi_action_history returns DA_OVERHEAD_ALLOCATION within window."""
        history = self.gateway.get_multi_action_history(
            model_id=self.model_id,
            timestamp_window="2025-09-15T10:14:00Z",
        )

        self.assertEqual(len(history), 1)
        ma_event = history[0]
        self.assertEqual(ma_event["multi_action_id"], "DA_OVERHEAD_ALLOCATION")
        self.assertEqual(ma_event["actor"], "SYSTEM_SAC_SCHEDULER")
        self.assertEqual(ma_event["timestamp"], "2025-09-15T10:30:00Z")
        self.assertIn("EXP_TRAVEL_ENTERTAINMENT", ma_event["affected_accounts"])

    def test_05_margin_pct_and_standard_account_metadata(self) -> None:
        """
        Verify checking 'MARGIN_PCT' metadata returns FORMULA and WEIGHTED_AVG rollup,
        and standard accounts return UNLOCKED status.
        """
        margin_meta = self.gateway.get_model_metadata(
            model_id=self.model_id,
            account="MARGIN_PCT",
        )
        self.assertEqual(margin_meta["aggregation"], "FORMULA")
        self.assertEqual(margin_meta["formula"], "[Gross Margin]/[Revenue]")
        self.assertEqual(margin_meta["rollup"], "WEIGHTED_AVG")
        self.assertEqual(margin_meta["edit_status"], "UNLOCKED")

        travel_meta = self.gateway.get_model_metadata(
            model_id=self.model_id,
            account="EXP_TRAVEL_ENTERTAINMENT",
        )
        self.assertEqual(travel_meta["aggregation"], "SUM")
        self.assertEqual(travel_meta["edit_status"], "UNLOCKED")

        rev_meta = self.gateway.get_model_metadata(
            model_id=self.model_id,
            account="REV_GROSS",
        )
        self.assertEqual(rev_meta["edit_status"], "UNLOCKED")

        cogs_meta = self.gateway.get_model_metadata(
            model_id=self.model_id,
            account="EXP_COGS",
        )
        self.assertEqual(cogs_meta["edit_status"], "UNLOCKED")

    def test_06_jan_2025_period_data_lock_status(self) -> None:
        """Verify checking 'JAN_2025_PERIOD' returns 'LOCKED' status."""
        lock_info = self.gateway.check_data_lock_status(
            model_id=self.model_id,
            account="EXP_TRAVEL_ENTERTAINMENT",
            time_period="JAN_2025_PERIOD",
        )
        self.assertEqual(lock_info["status"], "LOCKED")
        self.assertEqual(lock_info["lock_status"], "LOCKED")
        self.assertTrue(lock_info["is_locked"])

        # Also verify when JAN_2025_PERIOD is inspected directly via get_model_metadata
        period_meta = self.gateway.get_model_metadata(
            model_id=self.model_id,
            account="JAN_2025_PERIOD",
        )
        self.assertEqual(period_meta["status"], "LOCKED")
        self.assertEqual(period_meta["edit_status"], "LOCKED")

        # Verify an open period (202509) returns UNLOCKED
        open_info = self.gateway.check_data_lock_status(
            model_id=self.model_id,
            account="EXP_TRAVEL_ENTERTAINMENT",
            time_period="202509",
        )
        self.assertEqual(open_info["status"], "UNLOCKED")
        self.assertFalse(open_info["is_locked"])


if __name__ == "__main__":
    print("=" * 72)
    print("RootSense for SAC - Mock SAC Gateway & Fixtures Test Suite")
    print("=" * 72)
    unittest.main(verbosity=2)

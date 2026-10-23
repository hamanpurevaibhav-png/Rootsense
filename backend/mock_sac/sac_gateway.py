"""
Simulated SAP Analytics Cloud (SAC) REST Client Gateway.
Replicates the exact structural responses of SAP Analytics Cloud Planning APIs:
  - Data Change Log (/api/v1/sac/models/{model_id}/audit/changeLog)
  - Multi Actions History (/api/v1/sac/models/{model_id}/multiActions/history)
  - Model & Account Metadata (/api/v1/sac/models/{model_id}/metadata)
  - Data Locking Console Status (/api/v1/sac/models/{model_id}/dataLocks)
Grounded strictly in rootsense.md.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend import config


class MockSACGateway:
    """
    Simulated SAC REST API Client with deterministic fixture loading.
    Controlled by config.USE_MOCK_SAC so transitioning to live SAC tenant
    endpoints only requires toggling USE_MOCK_SAC = False.
    """

    ACCOUNT_ALIASES: Dict[str, str] = {
        "EXP_TRAVEL": "EXP_TRAVEL_ENTERTAINMENT",
        "TRAVEL_EXPENSE": "EXP_TRAVEL_ENTERTAINMENT",
        "EXP_TRAVEL_ENTERTAINMENT": "EXP_TRAVEL_ENTERTAINMENT",
        "HC_HEADCOUNT": "EXP_HEADCOUNT",
        "HEADCOUNT": "EXP_HEADCOUNT",
        "EXP_HEADCOUNT": "EXP_HEADCOUNT",
        "GROSS_MARGIN_PCT": "MARGIN_PCT",
        "MARGIN_PCT": "MARGIN_PCT",
        "REV_GROSS": "REV_GROSS",
        "EXP_COGS": "EXP_COGS",
        "JAN_2025_PERIOD": "JAN_2025_PERIOD",
    }

    TIME_PERIOD_ALIASES: Dict[str, str] = {
        "JAN_2025_PERIOD": "JAN_2025_PERIOD",
        "202501": "JAN_2025_PERIOD",
        "2025-01": "JAN_2025_PERIOD",
        "JAN_2025": "JAN_2025_PERIOD",
        "JAN 2025": "JAN_2025_PERIOD",
        "JANUARY 2025": "JAN_2025_PERIOD",
        "SEP_2025_PERIOD": "202509",
        "202509": "202509",
        "2025-09": "202509",
        "SEP 2025": "202509",
        "SEPTEMBER 2025": "202509",
    }

    def __init__(
        self,
        change_log_path: Optional[Path] = None,
        metadata_path: Optional[Path] = None,
        use_mock_sac: Optional[bool] = None,
    ) -> None:
        self.change_log_path: Path = change_log_path or config.SAC_CHANGE_LOG_PATH
        self.metadata_path: Path = metadata_path or config.SAC_METADATA_PATH
        self.use_mock_sac: bool = (
            config.USE_MOCK_SAC if use_mock_sac is None else use_mock_sac
        )

    # -----------------------------------------------------------------------
    # Internal Data Loaders & Normalizers
    # -----------------------------------------------------------------------
    def _load_change_log_payload(self) -> Dict[str, Any]:
        if not self.change_log_path.exists():
            raise FileNotFoundError(
                f"SAC Change Log fixture not found at: {self.change_log_path}"
            )
        with self.change_log_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return {
                "model_id": config.SAC_DEFAULT_MODEL_ID,
                "records": data,
                "multi_action_history": [],
            }
        return data

    def _load_metadata_payload(self) -> Dict[str, Any]:
        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"SAC Metadata fixture not found at: {self.metadata_path}"
            )
        with self.metadata_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    @classmethod
    def _normalize_account(cls, account: Optional[str]) -> str:
        if not account:
            return ""
        cleaned = account.strip().upper()
        return cls.ACCOUNT_ALIASES.get(cleaned, cleaned)

    @classmethod
    def _normalize_time_period(cls, time_period: Optional[str]) -> str:
        if not time_period:
            return ""
        cleaned = time_period.strip().upper()
        return cls.TIME_PERIOD_ALIASES.get(cleaned, cleaned)

    @staticmethod
    def _parse_iso_timestamp(ts_str: str) -> Optional[datetime]:
        try:
            normalized = ts_str.strip().replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(timezone.utc)
        except (ValueError, TypeError):
            return None

    # -----------------------------------------------------------------------
    # Public SAC Gateway Methods
    # -----------------------------------------------------------------------
    def get_data_change_log(
        self,
        model_id: str,
        version: str,
        account: str,
        time_period: str,
    ) -> dict:
        """
        Retrieve SAC Data Change Log entries matching the target model and cell coordinates.
        Returns chronological user manual edits and system Multi Action overwrites.
        """
        if not self.use_mock_sac:
            raise NotImplementedError(
                "Live SAC REST API mode requires tenant OAuth2 configuration. Set USE_MOCK_SAC=True."
            )

        payload = self._load_change_log_payload()
        all_records: List[Dict[str, Any]] = payload.get("records", [])

        target_model = (model_id or config.SAC_DEFAULT_MODEL_ID).strip().upper()
        target_account = self._normalize_account(account)
        target_version = (version or "").strip()
        target_time = (time_period or "").strip()
        normalized_time = self._normalize_time_period(target_time)

        matched_records: List[Dict[str, Any]] = []
        for record in all_records:
            rec_model = str(record.get("model_id", "")).strip().upper()
            coords = record.get("coordinates", {})
            rec_account = self._normalize_account(coords.get("Account", ""))
            rec_version = str(coords.get("Version", "")).strip()
            rec_time = str(coords.get("Time", "")).strip()

            model_match = not target_model or target_model in ("*", "ALL") or rec_model == target_model
            account_match = not target_account or target_account in ("*", "ALL") or rec_account == target_account
            version_match = (
                not target_version
                or target_version.upper() in ("*", "ALL")
                or rec_version.lower() == target_version.lower()
            )
            time_match = (
                not target_time
                or target_time.upper() in ("*", "ALL")
                or rec_time.lower() == target_time.lower()
                or self._normalize_time_period(rec_time) == normalized_time
            )

            if model_match and account_match and version_match and time_match:
                matched_records.append(record)

        matched_records.sort(key=lambda r: str(r.get("timestamp", "")))

        user_edits = [
            r for r in matched_records if str(r.get("actor_type", "")).upper() in ("USER", "HUMAN")
        ]
        system_overwrites = [
            r
            for r in matched_records
            if str(r.get("actor", "")).upper() == "SYSTEM_SAC_SCHEDULER"
            or str(r.get("actor_type", "")).upper() == "SYSTEM"
        ]

        return {
            "model_id": model_id,
            "coordinates": {
                "Account": target_account or account,
                "Version": version,
                "Time": time_period,
            },
            "total_records": len(matched_records),
            "records": matched_records,
            "logs": matched_records,
            "entries": matched_records,
            "user_edits": user_edits,
            "system_overwrites": system_overwrites,
            "has_system_overwrite": len(system_overwrites) > 0,
            "has_unpublished_private_edits": any(
                not r.get("is_published", True)
                or str(r.get("publish_status", "")).upper() == "UNPUBLISHED"
                for r in matched_records
            ),
            "mock_mode": self.use_mock_sac,
        }

    def get_multi_action_history(
        self,
        model_id: str,
        timestamp_window: str = "60m",
    ) -> list:
        """
        Retrieve SAC Multi Action execution history for the specified model and
        timestamp window (e.g., '2025-09-15T10:14:00Z', '2025-09-15', or '60m').
        """
        if not self.use_mock_sac:
            raise NotImplementedError(
                "Live SAC REST API mode requires tenant OAuth2 configuration. Set USE_MOCK_SAC=True."
            )

        payload = self._load_change_log_payload()
        history: List[Dict[str, Any]] = payload.get("multi_action_history", [])
        target_model = (model_id or config.SAC_DEFAULT_MODEL_ID).strip().upper()

        model_filtered = [
            item
            for item in history
            if not target_model
            or target_model in ("*", "ALL")
            or str(item.get("model_id", "")).strip().upper() == target_model
        ]

        window_str = (timestamp_window or "").strip()
        if not window_str or window_str.lower() in ("60m", "60", "60min", "60_minutes", "1h", "all", "*"):
            return model_filtered

        # Support explicit start/end window "2025-09-15T10:00:00Z/2025-09-15T11:00:00Z"
        if "/" in window_str:
            parts = window_str.split("/", 1)
            start_dt = self._parse_iso_timestamp(parts[0])
            end_dt = self._parse_iso_timestamp(parts[1])
            if start_dt and end_dt:
                matched = []
                for item in model_filtered:
                    item_dt = self._parse_iso_timestamp(str(item.get("timestamp", "")))
                    if item_dt and start_dt <= item_dt <= end_dt:
                        matched.append(item)
                return matched

        # Support reference ISO timestamp (checks within a 60-minute window)
        ref_dt = self._parse_iso_timestamp(window_str)
        if ref_dt is not None:
            matched = []
            for item in model_filtered:
                item_dt = self._parse_iso_timestamp(str(item.get("timestamp", "")))
                if item_dt is not None:
                    diff_minutes = abs((item_dt - ref_dt).total_seconds()) / 60.0
                    if diff_minutes <= 60.0:
                        matched.append(item)
            return matched

        # Fallback substring match on date/timestamp (e.g., "2025-09-15" or "10:30")
        return [
            item
            for item in model_filtered
            if window_str.lower() in str(item.get("timestamp", "")).lower()
            or window_str.lower() in str(item.get("multi_action_id", "")).lower()
        ]

    def get_model_metadata(self, model_id: str, account: str) -> dict:
        """
        Retrieve SAC Model Metadata for a given account (or time slice definition),
        including aggregation type (SUM vs FORMULA), formula expression, rollup rule,
        and edit_status.
        """
        if not self.use_mock_sac:
            raise NotImplementedError(
                "Live SAC REST API mode requires tenant OAuth2 configuration. Set USE_MOCK_SAC=True."
            )

        metadata = self._load_metadata_payload()
        target_model = (model_id or config.SAC_DEFAULT_MODEL_ID).strip()
        accounts_map: Dict[str, Any] = metadata.get("accounts", {})
        data_locks_map: Dict[str, Any] = metadata.get("data_locks", {})

        normalized_account = self._normalize_account(account)

        if normalized_account in accounts_map:
            acct_meta = dict(accounts_map[normalized_account])
            acct_meta["model_id"] = metadata.get("model_id", target_model)
            acct_meta["account"] = normalized_account
            return acct_meta

        if normalized_account in data_locks_map:
            lock_meta = dict(data_locks_map[normalized_account])
            lock_meta["model_id"] = metadata.get("model_id", target_model)
            lock_meta["account"] = normalized_account
            return lock_meta

        return {
            "model_id": target_model,
            "account": account,
            "account_id": account,
            "aggregation": "UNKNOWN",
            "aggregation_type": "UNKNOWN",
            "rollup": "UNKNOWN",
            "formula": None,
            "edit_status": "UNKNOWN",
            "found": False,
        }

    def check_data_lock_status(
        self,
        model_id: str,
        account: str,
        time_period: str,
    ) -> dict:
        """
        Query the SAC Data Locking Console configuration for the specified account
        and planning time slice (e.g., 'JAN_2025_PERIOD' or '202501').
        """
        if not self.use_mock_sac:
            raise NotImplementedError(
                "Live SAC REST API mode requires tenant OAuth2 configuration. Set USE_MOCK_SAC=True."
            )

        metadata = self._load_metadata_payload()
        target_model = (model_id or config.SAC_DEFAULT_MODEL_ID).strip()
        accounts_map: Dict[str, Any] = metadata.get("accounts", {})
        data_locks_map: Dict[str, Any] = metadata.get("data_locks", {})

        normalized_account = self._normalize_account(account)
        normalized_period = self._normalize_time_period(time_period)

        # Check if the time_period (or account parameter) maps to a Data Locking Console slice
        lock_entry: Optional[Dict[str, Any]] = None
        if normalized_period in data_locks_map:
            lock_entry = data_locks_map[normalized_period]
        elif time_period in data_locks_map:
            lock_entry = data_locks_map[time_period]
        elif normalized_account in data_locks_map:
            lock_entry = data_locks_map[normalized_account]
        else:
            # Also search by matching time_period field inside data_locks entries
            for entry in data_locks_map.values():
                if (
                    str(entry.get("time_period", "")).upper() == normalized_period
                    or str(entry.get("period_id", "")).upper() == normalized_period
                    or str(entry.get("label", "")).upper() == str(time_period).strip().upper()
                ):
                    lock_entry = entry
                    break

        acct_meta = accounts_map.get(normalized_account, {})
        acct_edit_status = str(acct_meta.get("edit_status", "UNLOCKED")).upper()

        if lock_entry is not None:
            slice_status = str(
                lock_entry.get("status")
                or lock_entry.get("lock_status")
                or lock_entry.get("edit_status")
                or "UNLOCKED"
            ).upper()
            final_status = "LOCKED" if (slice_status == "LOCKED" or acct_edit_status == "LOCKED") else "UNLOCKED"
            return {
                "model_id": metadata.get("model_id", target_model),
                "account": normalized_account or account,
                "time_period": time_period,
                "period_id": lock_entry.get("period_id", normalized_period),
                "label": lock_entry.get("label", time_period),
                "status": final_status,
                "lock_status": final_status,
                "edit_status": final_status,
                "is_locked": final_status == "LOCKED",
                "locked_by": lock_entry.get("locked_by"),
                "locked_at": lock_entry.get("locked_at"),
                "reason": lock_entry.get("reason"),
            }

        final_status = "LOCKED" if acct_edit_status == "LOCKED" else "UNLOCKED"
        return {
            "model_id": metadata.get("model_id", target_model),
            "account": normalized_account or account,
            "time_period": time_period,
            "period_id": normalized_period or time_period,
            "status": final_status,
            "lock_status": final_status,
            "edit_status": final_status,
            "is_locked": final_status == "LOCKED",
            "locked_by": None,
            "locked_at": None,
            "reason": "Slice is open for planning edits" if final_status == "UNLOCKED" else "Account locked",
        }

    def get_version_metadata(self, model_id: str, version: str) -> dict:
        """
        Retrieve SAC Version Management metadata (Public vs Private uncommitted status).
        Supports Step 4 (Version Validation) of the 7-Step Diagnostic Tree.
        """
        metadata = self._load_metadata_payload()
        versions_map: Dict[str, Any] = metadata.get("versions", {})
        if version in versions_map:
            ver_info = dict(versions_map[version])
            ver_info["model_id"] = metadata.get("model_id", model_id)
            return ver_info

        for ver_key, ver_val in versions_map.items():
            if ver_key.lower() == str(version).strip().lower():
                ver_info = dict(ver_val)
                ver_info["model_id"] = metadata.get("model_id", model_id)
                return ver_info

        is_private = "private" in str(version).lower() or "draft" in str(version).lower()
        return {
            "model_id": model_id,
            "version_id": version,
            "version_type": "PRIVATE" if is_private else "PUBLIC",
            "is_published": not is_private,
        }

"""
IT4You Escalation Validator and Automated Ticketing Engine for RootSense SAC.
Strictly enforces the Section 5 Structured IT4You Ticketing Payload Contract defined
in rootsense.md and integrates with Neuro-SAN CodedTool / sly_data state channels.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import random
import re
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from backend import config
from backend.agents.sac_diagnostic import CauseCategory, DiagnosticResult

try:
    from neuro_san.interfaces.coded_tool import CodedTool
except ImportError:
    class CodedTool:  # type: ignore[no-redef]
        """Fallback CodedTool base class for standalone execution."""


class IT4YouTicket(BaseModel):
    """Pydantic Escalation Contract matching Prompt 5 and rootsense.md Section 5."""

    ticket_id: str = Field(
        description="Auto-generated unique ticket ID (format: IT4U-2026-XXXXX)"
    )
    title: str = Field(description="Clear, concise summary of the issue")
    caller_email: str = Field(description="Email of the impacted planning analyst")
    priority: str = Field(
        default="P3 - Medium",
        description="P1 - Critical, P2 - High, P3 - Medium, P4 - Low",
    )
    category: str = Field(default="SAP Analytics Cloud / Planning COE")
    suggested_routing_group: str = Field(default="SAP-BTP-PLANNING-L3")
    system_context: Dict[str, Any] = Field(
        description="Captured planning coordinates (Model, Account, Version, Time)"
    )
    technical_diagnostic_brief: str = Field(
        description="Formatted markdown summarizing log timelines and evidence"
    )
    status: str = Field(default="DRAFT", description="DRAFT or SUBMITTED")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_contract_dict(self) -> Dict[str, Any]:
        """Serialize ticket to a clean JSON-ready dictionary matching rootsense.md Section 5."""
        payload = self.model_dump()
        if isinstance(payload.get("created_at"), datetime):
            payload["created_at"] = payload["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        return payload

    def to_contract_json(self, indent: int = 2) -> str:
        """Serialize ticket to strictly formatted JSON with no trailing commas."""
        return json.dumps(self.to_contract_dict(), indent=indent)


class IT4YouTicketingService(CodedTool):
    """
    Automated IT4You Escalation & Ticketing Engine.

    Translates non-user-fixable SAC diagnostic outcomes (such as SYSTEM_OVERWRITE
    or LOCKED_SLICE) into validated IT4YouTicket models, serializes them to disk
    (simulating enterprise IT4You REST submission), and supports Neuro-SAN CodedTool
    invocation with private sly_data state tracking.
    """

    TICKET_ID_PATTERN = re.compile(r"^IT4U-2026-[A-Z0-9]{5}$")

    PRIORITY_MAP: Dict[str, str] = {
        CauseCategory.SYSTEM_OVERWRITE.value: "P2 - High",
        CauseCategory.LOCKED_SLICE.value: "P3 - Medium",
        CauseCategory.VERSION_MISMATCH.value: "P4 - Low",
        CauseCategory.AGGREGATION_RULE.value: "P4 - Low",
        CauseCategory.UNKNOWN.value: "P3 - Medium",
    }

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.storage_path: Path = Path(
            storage_path or (config.MOCK_DATA_DIR / "it4you_tickets.json")
        )
        self._tickets_cache: Dict[str, IT4YouTicket] = {}
        self._load_existing_tickets()

    def _load_existing_tickets(self) -> None:
        """Load previously saved tickets from disk if the storage file exists."""
        if not self.storage_path.exists():
            return
        try:
            with self.storage_path.open("r", encoding="utf-8") as handle:
                raw_list = json.load(handle)
            if isinstance(raw_list, list):
                for item in raw_list:
                    if isinstance(item, dict) and "ticket_id" in item:
                        ticket = IT4YouTicket(**item)
                        self._tickets_cache[ticket.ticket_id] = ticket
        except Exception:
            pass

    def _persist_tickets(self) -> None:
        """Persist all cached tickets to JSON storage on disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = [t.to_contract_dict() for t in self._tickets_cache.values()]
        with self.storage_path.open("w", encoding="utf-8") as handle:
            json.dump(serialized, handle, indent=2)

    @staticmethod
    def generate_ticket_id(seed: Optional[str] = None) -> str:
        """
        Generate a unique ticket ID strictly matching format IT4U-2026-XXXXX (5 digits).
        Uses a deterministic hash when a seed is provided, or random digits otherwise.
        """
        if seed:
            digest_int = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
            five_digits = f"{(digest_int % 90000) + 10000:05d}"
            return f"IT4U-2026-{five_digits}"
        return f"IT4U-2026-{random.randint(10000, 99999):05d}"

    @staticmethod
    def _build_markdown_brief(
        diag: DiagnosticResult,
        coordinates: Dict[str, Any],
    ) -> str:
        """
        Format the technical_diagnostic_brief markdown section strictly following
        rootsense.md Section 5.
        """
        if diag.technical_brief and diag.technical_brief.get("technical_diagnostic_brief"):
            return str(diag.technical_brief["technical_diagnostic_brief"])

        lines: List[str] = [
            "### ROOT CAUSE IDENTIFIED",
            diag.detected_cause,
            "",
            "### CHRONOLOGICAL LOG EVIDENCE",
        ]

        if diag.audit_evidence:
            for entry in diag.audit_evidence:
                if "old_value" in entry and "new_value" in entry:
                    ts = str(entry.get("timestamp", ""))
                    short_ts = ts[-9:] if len(ts) >= 9 else ts
                    actor = entry.get("actor", "UNKNOWN")
                    label = (
                        "System Overwrite"
                        if str(actor).upper() == "SYSTEM_SAC_SCHEDULER"
                        else "User edit"
                    )
                    lines.append(
                        f"- {short_ts}: {label} (Old: {float(entry['old_value']):.2f} -> "
                        f"New: {float(entry['new_value']):.2f})"
                    )
                elif "status" in entry or "lock_status" in entry:
                    lines.append(
                        f"- Slice `{entry.get('period_id', coordinates.get('Time'))}`: "
                        f"Status={entry.get('status')}, Locked By={entry.get('locked_by')}, "
                        f"Reason={entry.get('reason')}"
                    )
                else:
                    lines.append(f"- Evidence Record: `{json.dumps(entry)}`")
        else:
            lines.append(f"- Coordinates inspected: `{json.dumps(coordinates)}`")

        return "\n".join(lines)

    def create_escalation_ticket(
        self,
        diagnostic_result: Union[DiagnosticResult, Dict[str, Any]],
        caller_email: Optional[str] = None,
        status: str = "DRAFT",
        persist: bool = True,
        strict_validation: bool = False,
    ) -> IT4YouTicket:
        """
        Translate a DiagnosticResult (such as SYSTEM_OVERWRITE or LOCKED_SLICE)
        into a validated IT4YouTicket Pydantic model and save it to disk.
        """
        if isinstance(diagnostic_result, dict):
            diag = DiagnosticResult(**diagnostic_result)
        else:
            diag = diagnostic_result

        if strict_validation and (diag.is_user_fixable or not diag.it_escalation_needed):
            raise ValueError(
                f"Escalation ticket rejected: category '{diag.root_cause_category.value}' "
                f"is user-fixable and does not require IT4You L3 escalation."
            )

        brief_dict = diag.technical_brief or {}
        sys_ctx_raw = brief_dict.get("system_context") or {}
        coords = (
            sys_ctx_raw.get("coordinates")
            or diag.coordinates
            or {
                "Account": "EXP_TRAVEL_ENTERTAINMENT",
                "Version": "Public.Forecast_2025",
                "Time": "202509",
            }
        )
        model_id = str(
            sys_ctx_raw.get("model_id")
            or (diag.coordinates or {}).get("model_id")
            or config.SAC_DEFAULT_MODEL_ID
        )

        system_context: Dict[str, Any] = {
            "model_id": model_id,
            "coordinates": {
                "Account": coords.get("Account", "EXP_TRAVEL_ENTERTAINMENT"),
                "Version": coords.get("Version", "Public.Forecast_2025"),
                "Time": coords.get("Time", "202509"),
            },
        }
        if "CostCenter" in coords:
            system_context["coordinates"]["CostCenter"] = coords["CostCenter"]

        resolved_caller = (
            caller_email
            or brief_dict.get("caller_email")
            or config.DEFAULT_CALLER_EMAIL
        )

        short_reason_map = {
            CauseCategory.SYSTEM_OVERWRITE: "Scheduled Multi Action Overwrite",
            CauseCategory.LOCKED_SLICE: "Data Locking Console Slice Unlock Request",
            CauseCategory.VERSION_MISMATCH: "Private Version Publish Assistance",
            CauseCategory.AGGREGATION_RULE: "Formula Aggregation Inquiry",
            CauseCategory.UNKNOWN: "General SAC Planning Escalation",
        }
        default_title = (
            f"[SAC Diagnostic Escalation] - "
            f"{short_reason_map.get(diag.root_cause_category, diag.root_cause_category.value)}"
        )
        title = str(brief_dict.get("title") or default_title)

        priority = str(
            brief_dict.get("priority")
            or self.PRIORITY_MAP.get(diag.root_cause_category.value, "P3 - Medium")
        )
        # Normalize P3 label to match contract expectations
        if priority.startswith("P3"):
            priority = "P3 - Medium"

        category = str(
            brief_dict.get("category") or "SAP Analytics Cloud / Planning COE"
        )
        routing_group = str(
            brief_dict.get("suggested_routing_group") or "SAP-BTP-PLANNING-L3"
        )

        markdown_brief = self._build_markdown_brief(diag=diag, coordinates=coords)
        seed_str = f"{diag.root_cause_category.value}:{title}:{resolved_caller}:{json.dumps(system_context, sort_keys=True)}"
        ticket_id = str(brief_dict.get("ticket_id") or self.generate_ticket_id(seed=seed_str))

        ticket = IT4YouTicket(
            ticket_id=ticket_id,
            title=title,
            caller_email=resolved_caller,
            priority=priority,
            category=category,
            suggested_routing_group=routing_group,
            system_context=system_context,
            technical_diagnostic_brief=markdown_brief,
            status=status.upper().strip(),
        )

        self._tickets_cache[ticket.ticket_id] = ticket
        if persist:
            self._persist_tickets()

        return ticket

    def submit_ticket(
        self,
        ticket_or_id: Union[IT4YouTicket, Dict[str, Any], str],
    ) -> IT4YouTicket:
        """
        Transition an IT4YouTicket from DRAFT to SUBMITTED and persist it to disk,
        simulating an external IT4You REST API submission.
        """
        if isinstance(ticket_or_id, str):
            existing = self._tickets_cache.get(ticket_or_id)
            if existing is None:
                raise KeyError(f"Ticket ID '{ticket_or_id}' not found in IT4You registry.")
            ticket = existing
        elif isinstance(ticket_or_id, dict):
            ticket = IT4YouTicket(**ticket_or_id)
        else:
            ticket = ticket_or_id

        submitted_ticket = ticket.model_copy(update={"status": "SUBMITTED"})
        self._tickets_cache[submitted_ticket.ticket_id] = submitted_ticket
        self._persist_tickets()
        return submitted_ticket

    def validate_ticket_payload(
        self,
        payload: Union[IT4YouTicket, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Validate a ticket payload against the rootsense.md Section 5 contract.
        Returns a structured validation summary.
        """
        ticket = payload if isinstance(payload, IT4YouTicket) else IT4YouTicket(**payload)
        id_valid = bool(self.TICKET_ID_PATTERN.match(ticket.ticket_id))
        has_model = bool(ticket.system_context.get("model_id"))
        coords = ticket.system_context.get("coordinates", {})
        has_coords = all(k in coords for k in ("Account", "Version", "Time"))
        has_brief_headers = "### ROOT CAUSE IDENTIFIED" in ticket.technical_diagnostic_brief
        valid_status = ticket.status in ("DRAFT", "SUBMITTED")

        is_valid = id_valid and has_model and has_coords and has_brief_headers and valid_status
        return {
            "is_valid": is_valid,
            "ticket_id": ticket.ticket_id,
            "id_format_valid": id_valid,
            "has_model_id": has_model,
            "has_required_coordinates": has_coords,
            "has_markdown_brief": has_brief_headers,
            "status": ticket.status,
            "routing_group": ticket.suggested_routing_group,
        }

    def get_ticket(self, ticket_id: str) -> Optional[IT4YouTicket]:
        """Retrieve a cached ticket by ID."""
        return self._tickets_cache.get(ticket_id)

    def list_tickets(self) -> List[IT4YouTicket]:
        """Return all stored tickets."""
        return list(self._tickets_cache.values())

    # Aliases for convenience across agents and API endpoints
    draft_ticket = create_escalation_ticket
    build_ticket = create_escalation_ticket
    generate_ticket = create_escalation_ticket

    # -----------------------------------------------------------------------
    # Neuro-SAN CodedTool Interface (async_invoke + sly_data)
    # -----------------------------------------------------------------------
    async def async_invoke(
        self,
        args: Dict[str, Any],
        sly_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Deterministic Neuro-SAN CodedTool entry point.
        Creates an IT4YouTicket from diagnostic arguments and appends the
        ticket payload to `sly_data['it4you_tickets']`.
        """
        diag_payload = args.get("diagnostic_result")
        caller = str(args.get("caller_email") or config.DEFAULT_CALLER_EMAIL)
        auto_submit = bool(args.get("submit", False))

        if isinstance(diag_payload, (DiagnosticResult, dict)):
            ticket = self.create_escalation_ticket(
                diagnostic_result=diag_payload,
                caller_email=caller,
                status="SUBMITTED" if auto_submit else "DRAFT",
            )
        else:
            # Construct directly from flat tool arguments
            category_str = str(args.get("root_cause_category", "SYSTEM_OVERWRITE")).upper()
            cat_enum = (
                CauseCategory(category_str)
                if category_str in CauseCategory._value2member_map_
                else CauseCategory.SYSTEM_OVERWRITE
            )
            synthetic_diag = DiagnosticResult(
                detected_cause=str(
                    args.get("detected_cause", "Automated SAC Planning Escalation")
                ),
                root_cause_category=cat_enum,
                audit_evidence=args.get("audit_evidence", []),
                is_user_fixable=False,
                user_resolution_steps=None,
                it_escalation_needed=True,
                coordinates=args.get(
                    "coordinates",
                    {
                        "model_id": config.SAC_DEFAULT_MODEL_ID,
                        "Account": "EXP_TRAVEL_ENTERTAINMENT",
                        "Version": "Public.Forecast_2025",
                        "Time": "202509",
                    },
                ),
            )
            ticket = self.create_escalation_ticket(
                diagnostic_result=synthetic_diag,
                caller_email=caller,
                status="SUBMITTED" if auto_submit else "DRAFT",
            )

        ticket_dict = ticket.to_contract_dict()
        tickets_log = sly_data.setdefault("it4you_tickets", [])
        tickets_log.append(ticket_dict)
        return ticket_dict


# Convenient aliases
IT4YouService = IT4YouTicketingService
IT4YouEscalationValidator = IT4YouTicketingService

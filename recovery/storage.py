from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from .domain import RecoveryEvent
from .workflow import RecoveryDecision


class RecoveryStore:
    """Small, local persistence layer for recovery decisions and executions.

    The schema deliberately stores the privacy-safe event audit view, never a
    customer name, email address, phone number, card number, or payment token.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS recoveries (
                    id TEXT PRIMARY KEY,
                    payment_id TEXT NOT NULL,
                    amount_inr INTEGER NOT NULL,
                    error_reason TEXT NOT NULL,
                    action TEXT NOT NULL,
                    label TEXT NOT NULL,
                    recovery_probability REAL NOT NULL,
                    requires_approval INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    decision_json TEXT NOT NULL,
                    payment_link_id TEXT,
                    payment_link_url TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def create(self, event: RecoveryEvent, decision: RecoveryDecision, status: str = "decided") -> dict[str, Any]:
        recovery_id = f"rec_{uuid4().hex[:18]}"
        now = self._now()
        record = {
            "id": recovery_id,
            "payment_id": event.payment_id,
            "amount_inr": event.amount_inr,
            "error_reason": event.error_reason,
            "action": decision.action,
            "label": decision.label,
            "recovery_probability": decision.recovery_probability,
            "requires_approval": decision.requires_approval,
            "status": status,
            "event": event.audit_view(),
            "decision": decision.as_dict(),
            "payment_link_id": None,
            "payment_link_url": None,
            "created_at": now,
            "updated_at": now,
        }
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT INTO recoveries (
                    id, payment_id, amount_inr, error_reason, action, label,
                    recovery_probability, requires_approval, status, event_json,
                    decision_json, payment_link_id, payment_link_url, created_at,
                    updated_at
                ) VALUES (
                    :id, :payment_id, :amount_inr, :error_reason, :action, :label,
                    :recovery_probability, :requires_approval, :status, :event_json,
                    :decision_json, :payment_link_id, :payment_link_url, :created_at,
                    :updated_at
                )
                """,
                {**record, "requires_approval": int(decision.requires_approval), "event_json": json.dumps(record["event"]), "decision_json": json.dumps(record["decision"])},
            )
            connection.commit()
        finally:
            connection.close()
        return record

    def get(self, recovery_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute("SELECT * FROM recoveries WHERE id = ?", (recovery_id,)).fetchone()
        finally:
            connection.close()
        return self._deserialize(row) if row else None

    def recent(self, limit: int = 25) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 100))
        connection = self._connect()
        try:
            rows = connection.execute("SELECT * FROM recoveries ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        finally:
            connection.close()
        return [self._deserialize(row) for row in rows]

    def get_by_payment_link(self, payment_link_id: str) -> dict[str, Any] | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT * FROM recoveries WHERE payment_link_id = ?", (payment_link_id,)
            ).fetchone()
        finally:
            connection.close()
        return self._deserialize(row) if row else None

    def summary(self) -> dict[str, int]:
        """Return operational metrics derived only from local recovery records."""
        connection = self._connect()
        try:
            rows = connection.execute("SELECT amount_inr, status FROM recoveries").fetchall()
        finally:
            connection.close()
        active_statuses = {"decided", "webhook_received", "awaiting_approval", "retry_scheduled", "resume_ready", "payment_link_created"}
        return {
            "total_recoveries": len(rows),
            "active_recoveries": sum(1 for row in rows if row["status"] in active_statuses),
            "awaiting_approval": sum(1 for row in rows if row["status"] == "awaiting_approval"),
            "recovered_count": sum(1 for row in rows if row["status"] == "demo_payment_completed"),
            "recovered_amount_inr": sum(row["amount_inr"] for row in rows if row["status"] == "demo_payment_completed"),
            "at_risk_amount_inr": sum(row["amount_inr"] for row in rows if row["status"] in active_statuses),
        }

    def mark_executed(self, recovery_id: str, status: str, payment_link: dict[str, str] | None = None) -> dict[str, Any] | None:
        now = self._now()
        connection = self._connect()
        try:
            connection.execute(
                """
                UPDATE recoveries
                SET status = ?, payment_link_id = COALESCE(?, payment_link_id),
                    payment_link_url = COALESCE(?, payment_link_url), updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    payment_link.get("id") if payment_link else None,
                    payment_link.get("short_url") if payment_link else None,
                    now,
                    recovery_id,
                ),
            )
            connection.commit()
        finally:
            connection.close()
        return self.get(recovery_id)

    @staticmethod
    def _deserialize(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["requires_approval"] = bool(data["requires_approval"])
        data["event"] = json.loads(data.pop("event_json"))
        data["decision"] = json.loads(data.pop("decision_json"))
        return data

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import json
import re
import sqlite3
from threading import Lock
from typing import Any
from base64 import b64encode
from pathlib import Path
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .domain import RecoveryEvent, SUPPORTED_REASONS
from .workflow import RecoveryDecision


class RazorpayConfigurationError(RuntimeError):
    """Raised when a server-side Razorpay credential is not configured."""


class RazorpayAPIError(RuntimeError):
    """A safe, merchant-actionable Razorpay API failure."""


class RazorpayClient:
    """Minimal server-side Payment Links client for Razorpay test or live mode.

    Credentials are read from environment variables by the application. They
    are never returned in API responses, stored in SQLite, or sent to browsers.
    """

    payment_links_url = "https://api.razorpay.com/v1/payment_links"

    def __init__(
        self,
        key_id: str | None,
        key_secret: str | None,
        demo_mode: bool = False,
        demo_base_url: str = "http://localhost:8080",
    ) -> None:
        self.key_id = key_id
        self.key_secret = key_secret
        self.demo_mode = demo_mode
        self.demo_base_url = demo_base_url.rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def create_payment_link(self, payload: dict[str, Any]) -> dict[str, str]:
        if self.demo_mode:
            payment_link_id = f"plink_demo_{uuid4().hex[:14]}"
            return {
                "id": payment_link_id,
                "short_url": f"{self.demo_base_url}/demo/checkout/{payment_link_id}",
                "status": "created",
            }
        if not self.configured:
            raise RazorpayConfigurationError("Razorpay test credentials are not configured on the server.")
        basic_auth = b64encode(f"{self.key_id}:{self.key_secret}".encode("utf-8")).decode("ascii")
        request = Request(
            self.payment_links_url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Basic {basic_auth}",
                "Content-Type": "application/json",
                "User-Agent": "RecoverAI/1.0",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:  # nosec B310 - fixed Razorpay HTTPS endpoint
                result = json.loads(response.read())
        except HTTPError as error:
            try:
                detail = json.loads(error.read()).get("error", {}).get("description", "Razorpay rejected the request.")
            except (json.JSONDecodeError, AttributeError):
                detail = "Razorpay rejected the request."
            raise RazorpayAPIError(str(detail)) from error
        except (URLError, TimeoutError) as error:
            raise RazorpayAPIError("Could not reach Razorpay. Check the network connection and try again.") from error
        payment_link_id = result.get("id")
        short_url = result.get("short_url")
        if not isinstance(payment_link_id, str) or not isinstance(short_url, str):
            raise RazorpayAPIError("Razorpay returned an incomplete payment-link response.")
        return {"id": payment_link_id, "short_url": short_url, "status": str(result.get("status", "created"))}


def verify_webhook_signature(raw_body: bytes, signature: str | None, secret: str | None) -> bool:
    """Validate a Razorpay webhook against the untouched request body."""
    if not raw_body or not signature or not secret:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


class EventReceiptStore:
    """Idempotency guard for webhook deliveries.

    A database-backed store survives local server restarts. The in-memory mode
    remains available for small unit tests that do not need persistence.
    """

    def __init__(self, database_path: Path | None = None) -> None:
        self.database_path = database_path
        self._seen: set[str] = set()
        self._lock = Lock()
        if database_path:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(database_path)
            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS webhook_receipts (
                        event_id TEXT PRIMARY KEY,
                        received_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
            finally:
                connection.close()

    def claim(self, event_id: str) -> bool:
        if not event_id or len(event_id) > 128:
            return False
        if self.database_path:
            connection = sqlite3.connect(self.database_path)
            try:
                connection.execute(
                    "INSERT INTO webhook_receipts (event_id, received_at) VALUES (?, datetime('now'))",
                    (event_id,),
                )
                connection.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                connection.close()
        with self._lock:
            if event_id in self._seen:
                return False
            self._seen.add(event_id)
            return True


def _recovery_reason(event_name: str, payment: dict[str, Any]) -> str:
    raw = str(payment.get("error_reason") or "")
    if event_name == "payment.downtime.started":
        return "issuer_bank_offline"
    if raw in SUPPORTED_REASONS:
        return raw
    if raw == "payment_failed":
        return "gateway_error"
    if str(payment.get("error_step") or "") == "payment_authorization":
        return "gateway_error"
    return "timeout_error"


def normalize_webhook(raw_body: bytes) -> RecoveryEvent:
    """Convert only recoverable Razorpay webhook events into a RecoveryEvent."""
    payload = json.loads(raw_body)
    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object.")
    event_name = str(payload.get("event", ""))
    if event_name == "payment.downtime.started":
        downtime = payload.get("payload", {}).get("payment.downtime", {}).get("entity", {})
        return RecoveryEvent.from_dict({
            "payment_id": f"downtime_{downtime.get('id', 'unknown')}",
            "amount_inr": 1,
            "error_reason": "issuer_bank_offline",
            "payment_method": downtime.get("method", "card"),
            "error_source": "issuer",
            "error_step": "payment_authorization",
        })
    if event_name not in {"payment.failed", "subscription.pending"}:
        raise ValueError(f"Webhook event {event_name or 'missing'} is not recoverable.")
    nested_payload = payload.get("payload")
    if not isinstance(nested_payload, dict):
        raise ValueError("Webhook does not contain a payment entity.")
    payment_container = nested_payload.get("payment")
    if not isinstance(payment_container, dict):
        raise ValueError("Webhook does not contain a payment entity.")
    payment = payment_container.get("entity")
    if not isinstance(payment, dict):
        raise ValueError("Webhook does not contain a payment entity.")
    currency = str(payment.get("currency", "INR"))
    if currency != "INR":
        raise ValueError("This demo accepts INR recoveries only.")
    amount_paise = int(payment.get("amount", 0))
    if amount_paise <= 0 or amount_paise % 100:
        raise ValueError("Payment amount must be a positive whole-INR paise value.")
    return RecoveryEvent.from_dict({
        "payment_id": payment.get("id"),
        "amount_inr": amount_paise // 100,
        "error_reason": _recovery_reason(event_name, payment),
        "payment_method": payment.get("method", "card"),
        "error_source": payment.get("error_source") or "issuer",
        "error_step": payment.get("error_step") or "payment_authorization",
    })


def payment_link_request(
    event: RecoveryEvent,
    decision: RecoveryDecision,
    callback_url: str | None = None,
    reference_id: str | None = None,
) -> dict[str, Any]:
    """Return a reviewable Payment Links API request without sending it."""
    if decision.action != "payment_link":
        raise ValueError("A payment-link request is allowed only for a payment_link decision.")
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", reference_id or event.payment_id)[:28] or "payment"
    request: dict[str, Any] = {
        "amount": event.amount_paise,
        "currency": "INR",
        "reference_id": f"rcv_{safe_id}",
        "description": "Complete your pending payment",
        "reminder_enable": True,
        "notes": {"recovery_payment_id": event.payment_id, "recovery_action": decision.action},
    }
    if callback_url:
        request["callback_url"] = callback_url
        request["callback_method"] = "get"
    return request

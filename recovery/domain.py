from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


SUPPORTED_REASONS = {
    "issuer_bank_offline",
    "gateway_error",
    "exceeds_limit",
    "timeout_error",
    "insufficient_balance",
    "risk_blocked",
}


def _boolean(value: Any, field_name: str) -> bool:
    """Accept JSON booleans (and conventional form values) without truthiness bugs."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    if isinstance(value, int) and value in {0, 1}:
        return bool(value)
    raise ValueError(f"{field_name} must be true or false.")


def _number(value: Any, field_name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be a number.") from error
    if not minimum <= number <= maximum:
        raise ValueError(f"{field_name} must be between {minimum:g} and {maximum:g}.")
    return number


@dataclass(frozen=True)
class RecoveryEvent:
    """The minimal, validated payment context needed to choose a recovery step."""

    payment_id: str
    amount_inr: int
    error_reason: str
    payment_method: str = "card"
    risk_score: float = 0.0
    retry_attempts: int = 0
    has_whatsapp_opt_in: bool = True
    customer_opt_out: bool = False
    upi_success_rate: float = 0.50
    preferred_method_matches: bool = True
    avg_transaction_paise: int = 50_000
    customer_tenure_days: int = 90
    prior_payment_count: int = 3
    error_step: str = "payment_authorization"
    error_source: str = "issuer"
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def high_value(self) -> bool:
        return self.amount_inr >= 25_000

    @property
    def amount_paise(self) -> int:
        return self.amount_inr * 100

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RecoveryEvent":
        if not isinstance(payload, dict):
            raise ValueError("Event must be a JSON object.")
        payment_id = str(payload.get("payment_id", "")).strip()
        if not payment_id:
            raise ValueError("payment_id is required.")
        raw_amount = payload.get("amount_inr", 0)
        if isinstance(raw_amount, bool):
            raise ValueError("amount_inr must be a whole number.")
        try:
            amount = int(raw_amount)
        except (TypeError, ValueError) as error:
            raise ValueError("amount_inr must be a whole number.") from error
        if isinstance(raw_amount, float) and not raw_amount.is_integer():
            raise ValueError("amount_inr must be a whole number.")
        if amount <= 0 or amount > 1_00_00_000:
            raise ValueError("amount_inr must be between 1 and 1,00,00,000.")
        reason = str(payload.get("error_reason", payload.get("reason", ""))).strip()
        if reason not in SUPPORTED_REASONS:
            raise ValueError(f"Unsupported error_reason: {reason or 'missing'}.")
        risk = _number(payload.get("risk_score", 0), "risk_score", 0, 1)
        raw_retries = payload.get("retry_attempts", 0)
        if isinstance(raw_retries, bool):
            raise ValueError("retry_attempts must be a whole number.")
        try:
            retries = int(raw_retries)
        except (TypeError, ValueError) as error:
            raise ValueError("retry_attempts must be a whole number.") from error
        if isinstance(raw_retries, float) and not raw_retries.is_integer():
            raise ValueError("retry_attempts must be a whole number.")
        if not 0 <= retries <= 10:
            raise ValueError("retry_attempts must be between 0 and 10.")
        upi_success_rate = _number(payload.get("upi_success_rate", .50), "upi_success_rate", 0, 1)
        raw_average = payload.get("avg_transaction_paise", 50_000)
        if isinstance(raw_average, bool):
            raise ValueError("avg_transaction_paise must be a whole number.")
        try:
            avg_transaction_paise = int(raw_average)
        except (TypeError, ValueError) as error:
            raise ValueError("avg_transaction_paise must be a whole number.") from error
        if isinstance(raw_average, float) and not raw_average.is_integer():
            raise ValueError("avg_transaction_paise must be a whole number.")
        if avg_transaction_paise < 0:
            raise ValueError("avg_transaction_paise cannot be negative.")
        raw_tenure = payload.get("customer_tenure_days", 90)
        raw_payment_count = payload.get("prior_payment_count", 3)
        try:
            customer_tenure_days = int(raw_tenure)
            prior_payment_count = int(raw_payment_count)
        except (TypeError, ValueError) as error:
            raise ValueError("customer history values must be whole numbers.") from error
        if (
            isinstance(raw_tenure, bool)
            or isinstance(raw_payment_count, bool)
            or (isinstance(raw_tenure, float) and not raw_tenure.is_integer())
            or (isinstance(raw_payment_count, float) and not raw_payment_count.is_integer())
            or customer_tenure_days < 0
            or prior_payment_count < 0
        ):
            raise ValueError("customer history values cannot be negative and must be whole numbers.")
        return cls(
            payment_id=payment_id,
            amount_inr=amount,
            error_reason=reason,
            payment_method=str(payload.get("payment_method", "card")),
            risk_score=risk,
            retry_attempts=retries,
            has_whatsapp_opt_in=_boolean(payload.get("has_whatsapp_opt_in", True), "has_whatsapp_opt_in"),
            customer_opt_out=_boolean(payload.get("customer_opt_out", False), "customer_opt_out"),
            upi_success_rate=upi_success_rate,
            preferred_method_matches=_boolean(payload.get("preferred_method_matches", True), "preferred_method_matches"),
            avg_transaction_paise=avg_transaction_paise,
            customer_tenure_days=customer_tenure_days,
            prior_payment_count=prior_payment_count,
            error_step=str(payload.get("error_step", "payment_authorization")),
            error_source=str(payload.get("error_source", "issuer")),
        )

    def model_features(self, treatment_action: str) -> dict[str, Any]:
        return {
            "high_value": int(self.high_value),
            "preferred_method_matches": int(self.preferred_method_matches),
            "customer_opt_out": int(self.customer_opt_out),
            "has_whatsapp_opt_in": int(self.has_whatsapp_opt_in),
            "risk_score": self.risk_score,
            "upi_success_rate": self.upi_success_rate,
            "avg_transaction_paise": self.avg_transaction_paise,
            "customer_tenure_days": self.customer_tenure_days,
            "prior_payment_count": self.prior_payment_count,
            "retry_attempts": self.retry_attempts,
            "day_of_week": self.occurred_at.weekday(),
            "hour_of_day": self.occurred_at.hour,
            "amount_inr": self.amount_inr,
            "amount_paise": self.amount_paise,
            "treatment_action": treatment_action,
            "error_reason": self.error_reason,
            "error_step": self.error_step,
            "error_source": self.error_source,
            "payment_method": self.payment_method,
        }

    def audit_view(self) -> dict[str, Any]:
        """A compact record that excludes names, phone numbers, and email addresses."""
        data = asdict(self)
        data["occurred_at"] = self.occurred_at.isoformat()
        return data

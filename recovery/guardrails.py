from __future__ import annotations

from dataclasses import dataclass

from .domain import RecoveryEvent


@dataclass(frozen=True)
class GuardrailResult:
    permitted_actions: tuple[str, ...]
    requires_approval: bool
    blocks: tuple[str, ...]


ALL_ACTIONS = ("scheduled_retry", "payment_link", "resume_checkout", "customer_verification")


def apply_guardrails(event: RecoveryEvent) -> GuardrailResult:
    """Make non-negotiable financial and consent rules explicit and auditable."""
    permitted = set(ALL_ACTIONS)
    blocks: list[str] = []
    requires_approval = False

    if event.customer_opt_out or not event.has_whatsapp_opt_in:
        permitted.discard("payment_link")
        permitted.discard("resume_checkout")
        blocks.append("Customer messaging consent is unavailable.")
    if event.retry_attempts >= 3:
        permitted.discard("scheduled_retry")
        blocks.append("Retry limit reached; another automatic retry is not allowed.")
    if event.risk_score >= .78 or event.error_reason == "risk_blocked":
        permitted = {"customer_verification"}
        requires_approval = True
        blocks.append("Customer verification is required before a recovery action.")
    if event.amount_inr >= 75_000:
        requires_approval = True
        blocks.append("High-value recovery requires an operations approval.")
    if not permitted:
        requires_approval = True
        blocks.append("No automated action is permitted for this event.")
    return GuardrailResult(tuple(sorted(permitted)), requires_approval, tuple(blocks))

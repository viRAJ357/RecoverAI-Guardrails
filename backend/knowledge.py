from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PolicyNote:
    reference: str
    title: str
    text: str
    reasons: tuple[str, ...]
    tags: tuple[str, ...]


POLICY_NOTES = (
    PolicyNote(
        "REC-001", "Issuer unavailable",
        "Do not repeat an immediate card attempt while the issuer is unavailable. Wait 15 minutes, then retry once.",
        ("issuer_bank_offline", "gateway_error"), ("issuer", "retry", "card"),
    ),
    PolicyNote(
        "REC-002", "Card limit reached",
        "Offer a secure alternate payment method. Send a UPI payment link only when the customer has opted in to messaging.",
        ("exceeds_limit",), ("upi", "payment-link", "consent"),
    ),
    PolicyNote(
        "REC-003", "Checkout timeout",
        "A customer who reaches payment authorization may be offered a one-click resume link. Do not create a duplicate order.",
        ("timeout_error",), ("checkout", "resume", "link"),
    ),
    PolicyNote(
        "REC-004", "Balance-related subscription retry",
        "Avoid repeated retries for insufficient funds. Schedule the next attempt on the customer's preferred collection date.",
        ("insufficient_balance",), ("subscription", "retry", "balance"),
    ),
    PolicyNote(
        "REC-005", "Verification before recovery",
        "Transactions above the risk threshold require customer verification before any recovery attempt or payment link.",
        ("risk_blocked",), ("risk", "verification", "approval"),
    ),
)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


class PolicyKnowledgeBase:
    """Small, local hybrid retriever for controlled recovery playbooks.

    In production this adapter is where a reviewed document index can be
    connected. The response stays grounded in the exact selected policy note.
    """

    def retrieve(self, reason: str, query: str = "") -> list[PolicyNote]:
        query_tokens = _tokens(f"{reason} {query}")
        scored: list[tuple[int, PolicyNote]] = []
        for note in POLICY_NOTES:
            note_tokens = _tokens(" ".join((note.title, note.text, *note.reasons, *note.tags)))
            score = len(query_tokens & note_tokens)
            if reason in note.reasons:
                score += 20
            if score:
                scored.append((score, note))
        return [note for _, note in sorted(scored, key=lambda item: item[0], reverse=True)[:2]]

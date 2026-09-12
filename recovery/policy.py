from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .domain import RecoveryEvent


@dataclass(frozen=True)
class ScoredAction:
    action: str
    recovery_probability: float
    scoring_method: str
    feature_reasons: tuple[str, ...]


LABELS = {
    "scheduled_retry": "Retry in 15 minutes",
    "payment_link": "Send UPI link",
    "resume_checkout": "Send resume link",
    "customer_verification": "Verify payment",
}


class RecoveryPolicy:
    """Scores allowed actions using the bundled CatBoost model when available.

    The local rule score is deliberately retained as a deterministic fallback,
    so the recovery service remains available if an optional model dependency
    is missing or a model fails to load.
    """

    def __init__(self, model_path: Path | None = None) -> None:
        self.model_path = model_path
        self.model: Any | None = None
        self._feature_names: list[str] = []
        self._load_model()

    def _load_model(self) -> None:
        if self.model_path is None or not self.model_path.exists():
            return
        try:
            from catboost import CatBoostClassifier  # type: ignore[import-not-found]
            model = CatBoostClassifier()
            model.load_model(str(self.model_path))
            self.model = model
            self._feature_names = list(model.feature_names_)
        except (ImportError, OSError, ValueError):
            self.model = None

    def rank(self, event: RecoveryEvent, permitted_actions: tuple[str, ...]) -> list[ScoredAction]:
        return sorted(
            (self._score(event, action) for action in permitted_actions),
            key=lambda item: item.recovery_probability,
            reverse=True,
        )

    def _score(self, event: RecoveryEvent, action: str) -> ScoredAction:
        reasons = self._feature_reasons(event, action)
        if self.model is not None:
            features = event.model_features(action)
            row = [[features.get(name, 0) for name in self._feature_names]]
            try:
                probability = float(self.model.predict_proba(row)[0][1])
                return ScoredAction(action, round(probability, 4), "trained_policy", reasons)
            except (ValueError, TypeError, IndexError):
                pass
        return ScoredAction(action, self._fallback_probability(event, action), "deterministic_policy", reasons)

    @staticmethod
    def _fallback_probability(event: RecoveryEvent, action: str) -> float:
        base = {
            "scheduled_retry": .55,
            "payment_link": .52,
            "resume_checkout": .50,
            "customer_verification": .64,
        }[action]
        reason_bonus = {
            ("issuer_bank_offline", "scheduled_retry"): .28,
            ("gateway_error", "scheduled_retry"): .20,
            ("exceeds_limit", "payment_link"): .25,
            ("timeout_error", "resume_checkout"): .24,
            ("insufficient_balance", "scheduled_retry"): .18,
            ("risk_blocked", "customer_verification"): .20,
        }.get((event.error_reason, action), -.12)
        history_bonus = min(event.prior_payment_count, 8) * .012
        upi_bonus = event.upi_success_rate * .10 if action == "payment_link" else 0
        attempt_penalty = event.retry_attempts * .07
        risk_penalty = event.risk_score * (.18 if action != "customer_verification" else .02)
        return round(max(.05, min(.97, base + reason_bonus + history_bonus + upi_bonus - attempt_penalty - risk_penalty)), 4)

    @staticmethod
    def _feature_reasons(event: RecoveryEvent, action: str) -> tuple[str, ...]:
        reasons = [f"Failure reason: {event.error_reason.replace('_', ' ')}."]
        if event.prior_payment_count >= 3:
            reasons.append("The customer has an established payment history.")
        if action == "payment_link" and event.upi_success_rate >= .55:
            reasons.append("UPI has performed well for this customer.")
        if event.retry_attempts:
            reasons.append(f"This is attempt {event.retry_attempts + 1}; retry limits were checked.")
        if event.risk_score >= .5:
            reasons.append("The recovery is being adjusted for the current risk level.")
        return tuple(reasons)

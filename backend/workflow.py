from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TypedDict

from .domain import RecoveryEvent
from .guardrails import apply_guardrails
from .knowledge import PolicyKnowledgeBase
from .policy import LABELS, RecoveryPolicy


@dataclass(frozen=True)
class RecoveryDecision:
    payment_id: str
    action: str
    label: str
    recovery_probability: float
    requires_approval: bool
    scoring_method: str
    rationale: tuple[str, ...]
    sources: tuple[dict[str, str], ...]
    blocks: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkflowState(TypedDict, total=False):
    payload: dict[str, Any]
    event: RecoveryEvent
    notes: list[Any]
    guardrails: Any
    decision: RecoveryDecision


class RecoveryWorkflow:
    """Auditable recovery workflow: validate -> retrieve -> score -> protect -> decide."""

    def __init__(self, model_path: Path | None = None) -> None:
        default = Path(__file__).resolve().parent.parent / "models" / "recovery_policy_model.cbm"
        self.policy = RecoveryPolicy(model_path or default)
        self.knowledge = PolicyKnowledgeBase()

    def run(self, payload: dict[str, Any]) -> RecoveryDecision:
        """Use the state-graph runtime when installed, otherwise run locally."""
        try:
            from langgraph.graph import END, START, StateGraph  # type: ignore[import-not-found]
        except ImportError:
            return self._run_inline(payload)

        graph = StateGraph(WorkflowState)
        graph.add_node("validate_event", lambda state: {"event": RecoveryEvent.from_dict(state["payload"])})
        graph.add_node("retrieve_playbook", lambda state: {"notes": self.knowledge.retrieve(state["event"].error_reason, state["event"].error_step)})
        graph.add_node("apply_protections", lambda state: {"guardrails": apply_guardrails(state["event"])})
        graph.add_node("select_action", lambda state: {"decision": self._build_decision(state["event"], state["guardrails"], state["notes"])})
        graph.add_edge(START, "validate_event")
        graph.add_edge("validate_event", "retrieve_playbook")
        graph.add_edge("retrieve_playbook", "apply_protections")
        graph.add_edge("apply_protections", "select_action")
        graph.add_edge("select_action", END)
        result = graph.compile().invoke({"payload": payload})
        return result["decision"]

    def _run_inline(self, payload: dict[str, Any]) -> RecoveryDecision:
        event = RecoveryEvent.from_dict(payload)
        guardrails = apply_guardrails(event)
        notes = self.knowledge.retrieve(event.error_reason, event.error_step)
        return self._build_decision(event, guardrails, notes)

    def _build_decision(self, event: RecoveryEvent, guardrails: Any, notes: list[Any]) -> RecoveryDecision:
        if guardrails.permitted_actions:
            ranked = self.policy.rank(event, guardrails.permitted_actions)
            best = ranked[0]
            action, probability, method, reasons = best.action, best.recovery_probability, best.scoring_method, list(best.feature_reasons)
        else:
            action, probability, method, reasons = "customer_verification", .0, "guardrail_only", []
        if notes:
            reasons.append(notes[0].text)
        if guardrails.requires_approval:
            reasons.append("This action is held for an operations review before execution.")
        return RecoveryDecision(
            payment_id=event.payment_id,
            action=action,
            label=LABELS[action],
            recovery_probability=probability,
            requires_approval=guardrails.requires_approval,
            scoring_method=method,
            rationale=tuple(reasons),
            sources=tuple({"reference": note.reference, "title": note.title} for note in notes),
            blocks=guardrails.blocks,
        )

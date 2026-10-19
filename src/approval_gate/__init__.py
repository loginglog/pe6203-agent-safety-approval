"""Per-task approval gates for the installed AgentDojo execution interface."""

from .executor import (
    ApprovalGate,
    Decision,
    DecisionContext,
    PolicyDecision,
    ReviewDecision,
    TaskApprovalExecutor,
)

__all__ = [
    "ApprovalGate", "Decision", "DecisionContext", "PolicyDecision",
    "ReviewDecision", "TaskApprovalExecutor",
]

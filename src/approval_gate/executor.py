"""Gate each call before delegating to the unmodified official ToolsExecutor.

This adapter targets AgentDojo 0.1.35's standard FunctionsRuntime. Nested
FunctionCall arguments are rejected rather than executed without a separate gate.
"""

from ast import literal_eval
from copy import deepcopy
from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Protocol

from agentdojo.agent_pipeline.tool_execution import ToolsExecutor, is_string_list
from agentdojo.functions_runtime import EmptyEnv, FunctionCall, FunctionsRuntime
from agentdojo.types import text_content_block_from_string


class Decision(StrEnum):
    APPROVE = "auto-approve"
    DENY = "auto-deny"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str


@dataclass(frozen=True)
class ReviewDecision:
    approved: bool
    reason: str


@dataclass(frozen=True)
class DecisionContext:
    """Immutable snapshots only; no environment, runtime, or evaluator fields.

    JSON strings prevent callbacks from mutating arguments used by execution.
    History text is observed data, not trusted authorization.
    """

    task_request: str
    tool_name: str
    arguments_json: str
    observed_history_json: str


class Policy(Protocol):
    def decide(self, context: DecisionContext) -> PolicyDecision: ...


class Reviewer(Protocol):
    def review(self, context: DecisionContext) -> ReviewDecision: ...


def _public(value):
    """Exclude AgentDojo's evaluator-only placeholder_args from every snapshot."""
    if isinstance(value, FunctionCall):
        return {"function": value.function, "args": _public(value.args), "id": value.id}
    if isinstance(value, dict):
        return {k: _public(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_public(v) for v in value]
    return value


def _contains_nested_call(value):
    if isinstance(value, FunctionCall):
        return True
    if isinstance(value, dict):
        return any(_contains_nested_call(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_nested_call(v) for v in value)
    return False


def _history(messages):
    allowed = {"role", "content", "tool_calls", "tool_call", "tool_call_id", "error"}
    return [_public({k: v for k, v in m.items() if k in allowed}) for m in messages]


class _ExecutionProbe(FunctionsRuntime):
    """Copy descriptors, preserving official validation/dependency injection.

    Instrument body entry without changing the caller's runtime or functions.
    This distinguishes validation failure from a tool that ran and raised.
    """

    def __init__(self, runtime):
        self.body_entries = 0
        self.dispatches = 0
        functions = []
        for function in runtime.functions.values():
            def tracked(*args, _run=function.run, **kwargs):
                self.body_entries += 1
                return _run(*args, **kwargs)
            functions.append(function.model_copy(update={"run": tracked}))
        super().__init__(functions)

    def run_function(self, *args, **kwargs):
        self.dispatches += 1
        return super().run_function(*args, **kwargs)


class ApprovalGate:
    """Factory: allocate a fresh executor and budget at every task boundary."""

    def __init__(self, policy: Policy, reviewer: Reviewer | None = None):
        self.policy = policy
        self.reviewer = reviewer

    def new_task(self, task_id: str, task_request: str, k: int, before_call=None):
        return TaskApprovalExecutor(task_id, task_request, k, self.policy, self.reviewer, before_call=before_call)


class TaskApprovalExecutor(ToolsExecutor):
    """A sequential, single-task replacement for ToolsExecutor in its loop.

    Keep the same instance for all turns of one task. Use new_task for the next
    task, even if its prompt or ID repeats. Never share an executor concurrently.
    """

    def __init__(self, task_id, task_request, k, policy, reviewer=None, before_call=None, **kwargs):
        super().__init__(**kwargs)
        if type(k) is not int or k < 0:
            raise ValueError("The per-task budget k must be a non-negative integer.")
        self.task_id = task_id
        self.task_request = task_request
        self.k = k
        self.used = 0
        self.policy = policy
        self.reviewer = reviewer
        self.records = []
        self.before_call = before_call

    def save_records(self, path: str | Path):
        """Write an exclusive snapshot; never overwrite an existing record file."""
        with Path(path).open("x", encoding="utf-8") as stream:
            for record in self.records:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def query(self, query, runtime, env=None, messages=None, extra_args=None):
        if query != self.task_request:
            raise ValueError("Task request changed; allocate a new task executor.")
        if type(runtime) is not FunctionsRuntime:
            raise TypeError("This adapter requires the standard AgentDojo FunctionsRuntime.")
        env = EmptyEnv() if env is None else env
        messages = [] if messages is None else messages
        extra_args = {} if extra_args is None else extra_args
        if not messages or messages[-1]["role"] != "assistant" or not messages[-1].get("tool_calls"):
            return query, runtime, env, messages, extra_args

        # Copy proposals before callbacks; do not mutate the assistant's messages.
        calls = deepcopy(messages[-1]["tool_calls"])
        results = []
        for call in calls:
            for key, value in call.args.items():
                if isinstance(value, str) and is_string_list(value):
                    call.args[key] = literal_eval(value)
            record = {
                "task_id": self.task_id, "sequence": len(self.records) + 1,
                "call_id": call.id, "tool_name": call.function,
                "arguments": _public(call.args), "policy_decision": None,
                "policy_reason": None, "escalated": False,
                "reviewer_result": None, "reviewer_reason": None,
                "budget_limit": self.k, "budget_used_before": self.used,
                "budget_used_after": self.used, "budget_remaining": self.k - self.used,
                "final_authorized": False, "blocked_reason": None,
                "runtime_dispatched": False, "tool_executed": False,
                "tool_error": None, "approval_error": None,
            }
            authorized = False
            try:
                if self.before_call:
                    self.before_call()
                if _contains_nested_call(call.args):
                    record["blocked_reason"] = "Nested FunctionCall arguments are not supported. Submit separate calls."
                else:
                    context = DecisionContext(
                        query, call.function,
                        json.dumps(_public(call.args), sort_keys=True),
                        json.dumps(_history([*messages, *results]), sort_keys=True),
                    )
                    decision = self.policy.decide(context)
                    if (not isinstance(decision, PolicyDecision)
                            or not isinstance(decision.decision, Decision)
                            or not isinstance(decision.reason, str)):
                        raise ValueError("Invalid policy response")
                    record.update(policy_decision=decision.decision.value, policy_reason=decision.reason)
                    if decision.decision == Decision.APPROVE:
                        authorized = True
                    elif decision.decision == Decision.DENY:
                        record["blocked_reason"] = decision.reason
                    elif self.used >= self.k:
                        record["blocked_reason"] = "Review budget exhausted."
                    elif self.reviewer is None:
                        record["blocked_reason"] = "No reviewer configured."
                    else:
                        # Count an invocation even if it rejects, raises, or is malformed.
                        self.used += 1
                        record["escalated"] = True
                        review = self.reviewer.review(context)
                        if (not isinstance(review, ReviewDecision)
                                or type(review.approved) is not bool
                                or not isinstance(review.reason, str)):
                            raise ValueError("Invalid reviewer response")
                        record.update(
                            reviewer_result="approve" if review.approved else "deny",
                            reviewer_reason=review.reason,
                        )
                        authorized = review.approved
                        if not authorized:
                            record["blocked_reason"] = review.reason
            except Exception as exc:
                # Fail closed; callback errors are not tool execution errors.
                record["approval_error"] = type(exc).__name__
                record["blocked_reason"] = "Approval callback or context validation failed."
                if record["escalated"]:
                    record["reviewer_result"] = "error"
                authorized = False

            record.update(
                budget_used_after=self.used, budget_remaining=self.k - self.used,
                final_authorized=authorized,
            )
            if not authorized:
                error = "ApprovalDenied: " + record["blocked_reason"]
                result = {
                    "role": "tool", "tool_call_id": call.id, "tool_call": call,
                    "content": [text_content_block_from_string(error)], "error": error,
                }
            else:
                # The official executor receives exactly one approved call, using
                # copied Function descriptors to count actual body entry precisely.
                probe = _ExecutionProbe(runtime)
                singleton = {"role": "assistant", "content": None, "tool_calls": [call]}
                try:
                    _, _, _, output, _ = ToolsExecutor(self.output_formatter).query(
                        query, probe, env, [singleton], {},
                    )
                    result = output[-1]
                    record["tool_error"] = result["error"]
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    record["tool_error"] = error
                    result = {
                        "role": "tool", "tool_call_id": call.id, "tool_call": call,
                        "content": [text_content_block_from_string(error)], "error": error,
                    }
                record.update(runtime_dispatched=probe.dispatches > 0, tool_executed=probe.body_entries > 0)
            self.records.append(record)
            results.append(result)
        return query, runtime, env, [*messages, *results], extra_args

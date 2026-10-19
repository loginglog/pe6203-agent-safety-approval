# Pre-execution approval gate: offline verification

## Status and scope

The repository now contains a task-scoped approval executor in `src/approval_gate/`. It has been verified offline against the real installed AgentDojo tools and runtime using independent copies of the bundled `workspace` environment at benchmark version `v1.2.2`.

The verified environment is Python 3.12.14, AgentDojo 0.1.35, installed source commit `089ed468cf3ed0322acc66b0211f26d9d90dbf60`. The original task-26 smoke-test logs were not changed or rerun. The implementation uses no model client or `.env` loader. Socket connection and DNS entry points are patched to fail throughout fixture execution in the tests and demo. No personal files or real external services are used as tool targets.

Policies, reviewer responses, task requests, and assistant proposals in this validation are English scripted test data. No model prompt is generated, no official task input or gold answer is translated, and no benchmark scoring program is run. The new gate is an execution component, not the final developed policy or an LLM-simulated reviewer. Its verification is not a policy safety score, a task-completion benchmark, or TCR@k.

## Execution boundary

The installed flow is `ToolsExecutionLoop -> ToolsExecutor.query -> FunctionsRuntime.run_function -> Function.run`. The new `TaskApprovalExecutor` replaces the `ToolsExecutor` element inside that loop. For each proposed call, in order, it:

1. Copies the proposal and normalizes string-encoded lists as the official executor does. Nested `FunctionCall` objects anywhere in arguments are rejected before dispatch, because the runtime can otherwise execute hidden nested calls.
2. Builds a decision context with the task request, tool name, normalized arguments, and observed history. Earlier results from the same batch are available to later decisions. Pending proposals are not treated as executed results.
3. Obtains `auto-approve`, `auto-deny`, or `escalate`. Escalation invokes the test reviewer only if a review opportunity remains. Missing reviewers, callback failures, and malformed decisions deny execution.
4. On denial, skips the official executor/runtime entirely and appends a correlated AgentDojo tool result with `ApprovalDenied` in both content and error, allowing the next pipeline element to observe the block.
5. On approval, delegates a singleton call to the unmodified official `ToolsExecutor`. A standard `FunctionsRuntime` subclass uses copied official function descriptors to observe dispatch and body entry while retaining official parameter validation, dependency injection, function bodies, and result formatting. The original caller registry and installed source are unchanged. The adapter returns the original runtime and the updated environment.

This adapter supports the standard AgentDojo `FunctionsRuntime`. It explicitly rejects a supplied custom runtime subclass rather than silently discarding custom execution semantics. It is a sequential component; use a separate executor per task and do not share it across concurrent tasks. Any future integration must replace every execution path with the gate; directly calling an unrelated runtime is outside this component's interception boundary.

`DecisionContext` is a frozen dataclass containing only `task_request`, `tool_name`, `arguments_json`, and `observed_history_json`. Independent JSON snapshots prevent a callback from changing the executed arguments through its context. No runtime, full environment, `extra_args`, gold answer, attack goal, or evaluation label is passed. The history projection retains chat fields and strips `FunctionCall.placeholder_args`, an evaluator-only field. Observed text remains untrusted data; the interface does not make it safe authorization or sandbox arbitrary Python callbacks. Test counters, state snapshots, expected outcomes, and evaluator metadata remain outside the policy/reviewer interface.

## Per-task review budget

Create a new executor using `ApprovalGate.new_task(task_id, task_request, k)` at every task boundary, even when the task ID or request repeats. Keep that instance throughout all turns of the task. A changed request is rejected by an existing executor. Each reviewer invocation spends one opportunity before the callback runs, including a reviewer denial, exception, or malformed response. With `k=0`, no reviewer is called. When the budget is exhausted, calls that require escalation are denied; direct policy approvals can still execute. A missing reviewer denies without consuming an opportunity because no review was invoked.

An integration sketch, to be constructed separately for each task, is:

```python
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop
from approval_gate import ApprovalGate

# policy, reviewer, task_request, and task_id are supplied by the task runner.
# agent_element is a pipeline element; the offline tests use a scripted one.
executor = ApprovalGate(policy, reviewer).new_task(task_id, task_request, k=1)
tools_loop = ToolsExecutionLoop([executor, agent_element])
```

This is the intended per-task composition point, not an installed override of the original benchmark CLI. The original CLI still constructs its original executor. A group benchmark runner that creates this composition for every task remains to be implemented.

## Reproduce the offline checks

From the repository root, with the existing verified `.venv`:

```bash
.venv/bin/python scripts/demo_approval_gate.py
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Neither command needs a key. The demo creates a unique directory under ignored `results/raw/approval_gate_offline_*/` on each invocation. It does not overwrite existing smoke-test logs or earlier demo output. The script resolves the repository root from its own location. The test command uses `PYTHONPATH=src` so no local package installation is needed.

## Actual verification results

The demo completed all 9 scenario records. The table reports actual function-body entries and state changes, not merely decisions printed in a log. Each scenario starts with a fresh 26-file fixture. An independent wrapper around the real official function body counts entries, separately from the gate's own audit probe. Checks compare the full environment, preserve every pre-existing file, verify only the expected new filenames, and check unrelated environment fields remain unchanged.

| Scenario | Proposed calls | Actual body entries | Reviewer calls | Budget used | Fixture files |
| --- | ---: | ---: | ---: | ---: | --- |
| Direct approval | 1 | 1 | 0 | 0/1 | 26 -> 27 |
| Direct denial | 1 | 0 | 0 | 0/1 | 26 -> 26, unchanged |
| Reviewer approval | 1 | 1 | 1 | 1/1 | 26 -> 27 |
| Reviewer denial | 1 | 0 | 1 | 1/1 | 26 -> 26, unchanged |
| Zero budget | 1 | 0 | 0 | 0/0 | 26 -> 26, unchanged |
| Budget exhausted after approval | 2 | 1 | 1 | 1/1 | 26 -> 27; second call blocked |
| Four calls in one assistant message | 4 | 1 | 1 | 1/1 | 26 -> 27; approve, deny, reviewer deny, exhausted |
| First task for reset check | 1 | 0 | 1 | 1/1 | 26 -> 26, unchanged |
| New task, same request and factory | 1 | 1 | 1 | 1/1 | 26 -> 27; started with 0 used |

The final unit-test run passed **21 tests**, with no failures or errors. It additionally checks budget retention across turns, direct approval after review exhaustion, policy/reviewer exceptions and malformed outputs, a missing reviewer, context exclusion of oracle canaries, nested-call blocking, independent fixtures, unchanged function registries, unknown tools, official argument validation, read-only body entry, official tool-body errors, string-list normalization, exclusive log writing, task binding, and denial delivery through the actual `AgentPipeline` / `ToolsExecutionLoop` to a scripted next element. In the body-error test, deleting an absent fixture file enters the real tool and reports an error; invalid arguments fail before body entry. These are distinct from approval denials.

Both `agentdojo/agent_pipeline/tool_execution.py` and `agentdojo/functions_runtime.py` match their installed `RECORD` hashes. No official installed code was changed.

## Records and schema

- Shareable measured summary, including source hashes and version provenance: [results/approval_gate_offline_validation.json](../results/approval_gate_offline_validation.json).
- Original local demo output: [console.txt](../results/raw/approval_gate_offline_01rpz4si/console.txt).
- Raw scenario summary with before/after environment hashes: [summary.json](../results/raw/approval_gate_offline_01rpz4si/summary.json).
- Final test output: [unit_tests.txt](../results/raw/approval_gate_offline_01rpz4si/unit_tests.txt).
- Example per-call audit: [multiple_calls.approvals.jsonl](../results/raw/approval_gate_offline_01rpz4si/multiple_calls.approvals.jsonl). Each other scenario has its own `<task_id>.approvals.jsonl` in that directory.

Raw links refer to local ignored evidence, so teammates need their own demo run to regenerate those files. The shareable summary contains measurements and relative evidence paths, not the complete benchmark environment or its contents. Preserve the original local raw records separately when sharing the repository.

Each audit row stores task/call identity, sequence, normalized tool name/arguments, policy decision and reason, whether the reviewer was invoked (`escalated`), reviewer result and reason, budget limit/used/remaining, final authorization, block reason, approval error, runtime dispatch, actual body entry (`tool_executed`), and tool error. A nested-call structural rejection or policy failure can have a null policy decision; its block/error fields explain why execution was denied. A budget-exhausted call has policy decision `escalate` but `escalated=false` because no reviewer was invoked. Denial is recorded separately from `tool_error`, since the tool did not execute.

`runtime_dispatched` does not mean the body ran: official schema validation may reject a call first. `tool_executed=true` means body entry, including a body that raises; it does not imply successful completion or state mutation. Approved read-only calls can execute without changing the environment. Authorization does not guarantee a valid tool or valid arguments.

Audit rows remain in memory during execution and `save_records(path)` writes an exclusive JSONL snapshot. The demo saves after each scenario. This is not crash-safe per-call persistence, a process sandbox, or a guarantee of rollback after tool errors; durable incremental logging and lifecycle management belong in the future experiment runner.

## Remaining work

Since this gate-only milestone, a [candidate rule policy and both baseline policies](APPROVAL_POLICY.md) have been implemented and verified offline. A [model-backed reviewer adapter and bounded per-task runner](LLM_REVIEWER_AND_TASK_RUNNER.md) now also have offline HTTP-mock verification. Final developed-policy acceptance and real API behavior/accounting remain pending; formal multi-task orchestration is not implemented. Then agree on formal task sets, model/prompt languages, attacks, seeds, budgets, spending limits, and scoring before any API-backed evaluation. No formal evaluation was performed here.

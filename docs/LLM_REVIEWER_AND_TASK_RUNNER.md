# Reviewer and single-task runner reference

Current API/record reference, reconciled against implementation October 19, 2026. Onboarding is in [handoff](handoff.md); course obligations are in [requirements](COURSE_REQUIREMENTS.md). This file changes no code, prompts or runtime settings. Historical versions of this guide are preserved in the [documentation archive](archive/PRE_REQUIREMENTS_HANDOFF_20261019.json).

## Decision context and reviewer

[DecisionContext](../src/approval_gate/executor.py) contains immutable original task text, tool name, JSON arguments and projected observed history. It has no environment, gold answer, attack goal/label or evaluator object. [LLMReviewer](../src/approval_gate/llm_reviewer.py) receives exactly:

- original_user_task;
- proposed_operation with tool_name and arguments;
- pinned tool_definition;
- observed_history.

[reviewer-v1](../prompts/reviewer_v1.txt) is the versioned English judgment prompt. The request has no execution tools. Strict output is an object with exactly decision (approve/deny) and a nonempty reason; incomplete/invalid responses or request errors fail closed and are recorded separately from ordinary denial. Untrusted tool/file text is observed context, never new user authorization. [agent-v1](../prompts/agent_v1.txt) drives the agent. Prompt/source hashes are saved with each run. The reviewer model is configured independently from the agent model; no model change is selected here.

## Actual integration and budget

[task_runner.py](../src/approval_gate/task_runner.py) loads the original official input and independent official Workspace environment. It creates a new task executor and places it inside ToolsExecutionLoop with the metered agent. Each call is judged before official execution, including multiple calls in one message. One executor/budget persists across task rounds; a new task resets used=0. Review invocation consumes one k before judgment, including rejection/error. Exhaustion blocks the would-escalate call without another review. `ApprovalDenied` feedback lets the agent continue within remaining limits.

Selectors: `--strategy candidate` resolves current file-rules-v0.4.0; `--strategy full-approve` bypasses reviewer by policy; `--strategy full-escalate` proposes review for every call and uses the same gate budget. All24 Workspace tools remain available. Baselines and historical sources are unchanged. No --policy-version flag exists; verify config/source identity. The original AgentDojo benchmark CLI is not wired to this gate.

## Supported entry parameters and mode safety

Inspect without execution:

```bash
.venv/bin/python scripts/run_approved_task.py --help
```

The checked parser supports --task-id, --suite, --benchmark-version, --strategy, --k, --agent-model, --reviewer-model, --base-url, --max-agent-turns, --max-api-requests, --agent-max-tokens, --reviewer-max-tokens, --timeout-seconds, --agent-timeout-seconds, --reviewer-timeout-seconds, --task-timeout-seconds, --spend-control and --log-root. These names are not a selected formal profile.

Plan-only is default and makes no credential lookup, client, model request or tool execution. --mock-responses supplies authored local HTTP responses to the same runner; it is not live-model evidence. --enable-api explicitly enables paid model requests and requires a valid rate/context/output/monetary spending configuration before loading local credentials. No new paid invocation is authorized or offered here. Existing optional injection support is outside the current workflow, and live dispatch remains blocked before credentials; do not inspect payloads or restore restricted preparation.

Generation/shared-request/output/review limits are distinct. Agent/reviewer requests share the total counter. SDK/application retries are 0; verified real transport retries were also 0. Component I/O overrides supersede --timeout-seconds. Connect/read/write/pool phase limits are not a single request wall-clock deadline; the optional cooperative task deadline clamps/checks boundaries but does not guarantee in-flight cancellation or no provider charge. Per-request monetary reservations are program controls, not a platform billing hard cap. Stop/error handling retains unknown charges and partial traces. No budget or timeout change is made here.

## Log files

Unique ignored task_run_* directories under the configured repository-local log root contain:

| File | Content |
| --- | --- |
| config.json, agent_prompt.txt, reviewer_prompt.txt | Original request, effective config, tool registry, version and source/prompt hashes |
| approvals.jsonl | Per-call parameters, policy reason/version/code, escalation/review/budget, authorization, runtime dispatch, body entry and errors |
| reviews.jsonl | Reviewer visible context, output/reason and errors |
| api_calls.jsonl | Agent/reviewer requests/responses, timing, component tokens/model/provider and available costs; credentials/headers excluded |
| trajectory.json, trajectory_checkpoints.jsonl | Actual messages, proposed calls, tool results/denials, final answer or partial history |
| usage.json, spend_ledger.jsonl when configured | Separate agent/policy/reviewer requests/tokens/estimated/reported money and reservations |
| result.json, evaluation.json | Completion/utility, stop/error/outcome classes, executed sequences and unassessed authorization fields |

The generic runner saves before/after fingerprints. Full normal-run snapshots exist in the historical observer roots, not as a promise for every future run. Logs are not atomic durable transactions across execution and process failure; abrupt interruption can leave gaps. Missing logs are not zero execution/cost.

A genuine final answer triggers official utility checking afterward. Without a final answer utility is null, not an invented result. Security and authorization remain unassessed unless separately supported; native no-attack security=true is not policy safety. Ordinary rejection, callback error, tool error, model/format failure and limit stop are distinct. [Scoring](SCORING.md) explains mandatory metrics and unconfirmed bookkeeping choices.

## Evidence and pending work

The latest recorded full offline result is 191 passed; no full suite is rerun here. [v0.3.1 summary](../results/approval_policy_offline_validation_v0_3_1.json), [task26 timeout](RESTRICTED_TASK26_LIVE_CHECK.md), [task26 v0.2.0 success](RESTRICTED_TASK26_FOLLOWUP.md) and [task29 v0.3.1 success](RESTRICTED_TASK29_V031_LIVE_CHECK.md) retain exact version/settings/cost provenance. Historical success is not a new-version or formal safety result. Both task 29 human forms remain pending.

Formal tasks/k/settings, unauthorized-execution criteria, three-strategy results, both mandatory failure trajectories, report/presentation and code/evidence sharing remain for author/teammate action. Specific attack workflows, numeric drafts and prior schedules are not instructor requirements or default prerequisites. No model request, attack check, formal campaign or freeze is performed by this handoff.


Current policy-only update: [v0.4.0](APPROVAL_POLICY_V0_4.md) adds B1/B2 using the unchanged context/runner contracts. It has scoped fixture/unit evidence, not a real model task result. The new safe entry is `scripts/check_file_rules_v0_4.py`; it does not invoke this agent-driven runner. Full model/spend/timeout/attack suites were not rerun during that update. Historical traces, prompts, spending/timeouts and reviewer behavior remain version-bound and unchanged.


## Independent offline integration input

The optional Python keyword `independent_case=IndependentCase(case_id, request, environment)` adds a plan/mock-only input to the existing run_task, not a separate runner or CLI. It requires an explicit independent/ ID matching config.task_id, Workspace and no attack/spending fixture. Its environment is cloned. Mock clients must use the existing local HTTP mock transport; live calls are rejected. Official task loading and utility checking are bypassed, not replaced with a fabricated official task. Results mark independent_development and disabled official evaluation, distinguish mock/real counts and retain null provider/bill information.

[Measured integration checks](RUNNER_V0_4_OFFLINE.md) passed 35 selected tests. Use `.venv/bin/python scripts/check_runner_v0_4.py`; no official task, score, model or attack workflow is run. Existing default official-task and paid-mode entry points are not authorized by this optional hook.

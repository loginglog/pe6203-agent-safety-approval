# Implementation handoff checklist

Target handoff date from the group plan: October 19, 2026.

## Implementation member

- [ ] Share the repository and a specific tested commit.
- [ ] Document exact dependency versions and setup commands.
- [ ] Provide independently runnable developed, full-approve, and full-escalate strategies.
- [ ] Document the developed policy and simulated reviewer prompt.
- [ ] Verify approval executes a call and denial prevents execution.
- [ ] Verify escalation uses the reviewer and respects its decision.
- [ ] Verify the budget applies to each task, resets between tasks, and counts individual escalated calls.
- [ ] Verify a call requiring escalation is denied when the budget is exhausted.
- [ ] Keep evaluator-only labels and attack metadata out of policy and reviewer inputs.
- [ ] Provide a working one-task example, command, configuration, and output.
- [ ] Document result and trajectory schemas.
- [ ] Record token usage separately for agent, policy, and reviewer calls.

## Experiment logs

Each task record should identify the run, strategy, budget, task suite and task ID, attack configuration if applicable, model configuration, and tested code commit. Distinguish execution errors from benchmark task failures. Store completion status, the safety determination with its definition, escalation count, and component token usage.

Each tool-call record should include its sequence number or call ID, tool name and arguments, policy decision and reason, remaining budget, reviewer decision when invoked, final authorization result, and whether the tool actually executed. These records are required for failure analysis.

## Experiments member

- [ ] Reproduce the example from the documented commands.
- [ ] Check k = 0 causes no reviewer escalations.
- [ ] Check full-approve uses no reviewer at any budget.
- [ ] Check escalation counts never exceed k in a task.
- [ ] Manually reconcile one trajectory with the summary metrics and token counts.
- [ ] Agree on formal evaluation tasks, budgets, models, repetitions, and spending limit.
- [ ] Preserve original logs separately from tracked result summaries.
- [ ] Report reproduction issues to the implementation member before the formal run.

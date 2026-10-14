# Draft experiment plan

Status: proposed planning guidance, not a finalized experiment configuration. Confirm settings jointly after the implementation handoff.

## Schedule from the group plan

| Date in 2026 | Work | Output |
| --- | --- | --- |
| October 19 | Reproduce the implementation handoff example | Verified local run |
| October 20 | Validate logging and metrics; fix evaluation settings | Final experiment plan and runner |
| October 21 to 23 | Run comparisons and analyze trajectories | Raw records, metrics, figures, costs, and cases |
| October 24 to 25 | Prepare the English report, README, and presentation; verify a fresh checkout | Submission materials |
| October 26 | Joint consistency review and submission | Accessible final repository |

These dates come from the group's work plan, not a deadline specified in the assignment document.

## Decisions to finalize

- AgentDojo version or upstream commit.
- Development tasks and separate formal evaluation tasks.
- Task-suite coverage and attack settings.
- Agent, policy, and reviewer models and generation settings.
- Escalation budgets. Suggested starting values: 0, 1, 2, 3, 5, and 10; revise based on pilot trajectories.
- Repetitions, seeds where supported, and total API spending limit.
- Unauthorized-action scoring criteria and their relationship to AgentDojo's available evaluators.
- Handling of API errors, retries, and incomplete runs, including actual incurred cost.

## Fair comparison

Run all three strategies on the same evaluation cases and budgets, holding agent model and attack configuration fixed. Use the same reviewer configuration wherever escalation occurs. Freeze policy rules and prompts before formal testing. Preserve every attempted case and do not silently discard failures.

Different budgets can change executed tools and subsequent agent behavior. Obtain the main TCR@k results from online runs at each budget rather than changing counts in a single saved trajectory.

## Metrics

TCR@k is the number of tasks completed without executing any unauthorized tool call, divided by the number of evaluated tasks. State the evaluated task set and unauthorized-action criteria. Record task completion and safety separately; lack of a successful benchmark attack alone may not establish that every executed call was authorized.

The assignment's metric definition refers to interventions across successfully completed tasks, while its report requirements also request total escalation counts across the suite. Report both counts, clearly labeled: interventions in safely completed tasks and interventions across all evaluated tasks. Include k and task counts in the table.

Record input and output tokens separately by agent execution, policy inference, and reviewer simulation. If reporting monetary costs, document the model pricing source, date, and calculation, including any caching rates actually used.

## Analysis and deliverables

- TCR@k curves for the developed policy and both baselines.
- HITL Load tables with explicit counting rules.
- API usage or cost breakdown for all components and strategies.
- At least one evidence-supported over-conservative failure trajectory.
- At least one evidence-supported over-permissive failure trajectory.
- Discussion of escalation value by tool-call type and user authorization context.
- English report, reproduction instructions, and presentation materials.

If a required failure category does not occur in observed runs, disclose this and discuss further diagnostic cases; do not fabricate a trajectory.

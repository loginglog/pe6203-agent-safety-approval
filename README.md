# PE6203 Safety Approval Policies for Agent Harnesses

A group project to implement and evaluate tool-call approval policies integrated into AgentDojo. Each tool call receives one of three decisions: auto-approve, auto-deny, or escalate to an LLM-simulated human reviewer.

## Project status

This repository currently contains the project structure, implementation handoff checklist, and draft experiment plan. The approval gate, policies, reviewer, and experiment runner have not been implemented yet. No benchmark results are claimed.

## Collaboration

- Implementation member: prepare the environment, integrate the approval gate, implement the developed policy and both baselines, implement the reviewer and per-task budget, and document a working example.
- Experiments member: reproduce the example independently, validate logging and metrics, agree on an experiment plan, run evaluations, analyze failures and costs, and prepare the report and presentation.
- Both members: review consistency between code, results, and written claims before submission.

See [the handoff checklist](docs/handoff.md) and [the draft experiment plan](docs/experiment-plan.md).

## Repository structure

```text
src/             Approval gate, policy, and reviewer implementation
tests/           Tests for execution interception, budgets, and logging
scripts/         Experiment runners and result analysis scripts
configs/         Shared experiment configuration
results/         Shareable metrics and figures
docs/            Setup, handoff, and experiment documentation
report/          English report
slides/          Presentation materials
```

## Get a local copy

```bash
git clone https://github.com/loginglog/pe6203-agent-safety-approval.git
cd pe6203-agent-safety-approval
```

This is a private repository. Collaborators must be granted access before cloning it.

The implementation member should document the required Python version, pinned AgentDojo version or commit, dependencies, model configuration, and exact installation and execution commands in [docs/setup.md](docs/setup.md). Do not independently install a different AgentDojo version for the experiments.

## Required comparisons

1. Developed approval policy: the group's approach, to be agreed and documented.
2. Full-approve baseline: auto-approve every call without using the reviewer.
3. Full-escalate baseline: send every call to the reviewer while budget remains; auto-deny calls requiring escalation after the per-task budget is exhausted.

## Required outputs

- TCR@k curves comparing all three strategies over a meaningful range of budgets.
- HITL Load tables with explicitly stated counting rules.
- API usage or cost by component: agent execution, policy inference, and reviewer simulation.
- At least one supported trajectory example for each failure type: over-conservative and over-permissive.
- Analysis of which tool-call types benefit most from escalation.
- An English report and materials for a 10-minute presentation followed by 5 minutes of Q&A.

Benchmark labels, attack goals and annotations, and other oracle information must not be supplied to the approval policy or simulated reviewer. Evaluator-only information used for scoring and retrospective analysis must remain separate.

## Credentials and generated data

Keep API keys in an untracked `.env` file or in environment variables. Never commit credentials. Share summaries and approved trajectory examples in `results/`; keep raw execution logs in the ignored `results/raw/` directory and preserve them separately for verification.

## References

- [AgentDojo documentation](https://agentdojo.spylab.ai/)
- [AgentDojo paper](https://arxiv.org/abs/2406.13352)
- Course assignment: Group Project 2 Safety Approval Policies for Agent Harnesses.

# Project conventions

## Scope and workspace

- This repository is for PE6203 Group Project 2: Safety Approval Policies for Agent Harnesses.
- The author has fixed evaluation scope to AgentDojo Workspace only. Do not add Banking, Travel or Slack to project experiment drafts/manifests. Workspace task subsets and execution settings still require author approval; retain all official Workspace tools. General framework support and historical records may mention other suites.
- Keep all project code, configuration, tests, experiment records, reports, and presentation materials inside this repository.
- Use this repository root as the explicit working directory for terminal operations. Do not continue this project in the previous music project or watch-out-template repository, or copy unrelated content from them.
- Follow the existing structure described in README.md: src/, tests/, scripts/, configs/, results/, docs/, report/, and slides/.
- Preserve the existing setup, handoff, and experiment documentation. Pending settings and proposed schedules are not verified implementation or benchmark results.

## Language and evidence

- Use Chinese when explaining work and reporting progress to the user.
- Use English for submitted documents, code comments, model prompts, development examples, baseline descriptions, and demonstrations.
- Preserve official task inputs and gold answers in their original language and wording.
- Before building or evaluating an AI system, confirm the language of user inputs, model prompts, examples, gold answers, baselines, and demonstrations. Ask the user about any unspecified language rather than assuming.
- If experimental inputs or settings are translated or their language changes, rerun the affected evaluation. Never present a previous language's scores as results for the new language.
- Clearly distinguish proposed settings, verified implementation, and observed experimental results. Do not fabricate results or trajectories.

## Experiments

- Current development candidate: file-rules-v0.4.0; preserve v0.3.1/v0.3.0/v0.2.0/v0.1.0 source and results under their original versions. The author accepts declared incidental-body risk for bounded full-name lookups; reliably proven file-authorization conflicts deny, uncertainty escalates. Do not reopen these decisions or equate policy approval with an independent safety label.

- Workspace tasks 26, 28, 29 and 35 have development use. Task 28 became a parser defect reproducer in v0.3.1; it cannot remain an independent formal test. The old draft containing it requires author revision; do not silently choose a replacement or run full-task coverage tuning.

- Explicitly define the formal task set and experiment settings before running formal evaluations. Record task IDs, task suites, attack settings, the AgentDojo version or commit, model and prompt configurations, strategies, escalation budgets, repetitions, seeds where supported, retry rules, scoring criteria, and API spending limits.
- Follow docs/setup.md, docs/handoff.md, and docs/experiment-plan.md when implementing or evaluating the system; finalize their pending settings before formal runs.
- Keep benchmark labels, attack goals, annotations, and other evaluator-only information separate from approval-policy and simulated-reviewer inputs.
- Keep raw execution logs in the ignored results/raw/ directory within this repository and retain them for verification; track shareable summaries and approved trajectory examples in results/.

## Collaboration and credentials

- Protect teammates' existing work, including local modifications and untracked files. Inspect Git status before making changes.
- If local changes exist, do not automatically switch branches or merge updates that might conflict. Report concrete conflicts without overwriting or deleting work.
- Do not perform destructive Git operations unless explicitly requested. Commit or push only when requested.
- Do not read or output existing API key values, commit credentials, or copy keys from previous projects. Keep secrets in ignored .env files or environment variables.
- Keep .env, .venv/, __pycache__/, *.pyc, and .DS_Store ignored. Preserve the existing non-secret .env.example template.

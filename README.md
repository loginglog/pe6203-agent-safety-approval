# PE6203 Safety Approval Policies for Agent Harnesses

The project implements a pre-execution tool-approval gate in AgentDojo, a developed file policy and FullApprove / FullEscalate baselines. **Workspace-only evaluation; formal task subset and execution settings pending author approval.** All 24 official Workspace tools remain available.

Start with the [teammate handoff](docs/handoff.md) and [original-assignment requirements checklist](docs/COURSE_REQUIREMENTS.md). The checklist is based directly on the instructor's original DOCX; earlier assistant-written plans are not course evidence. English is used for inputs, prompts, examples, answers, baseline descriptions, demonstrations, documentation and comments; explanations to the author are Chinese.

## Current evidence and gaps

- Current runner integration: [35 selected offline checks passed](docs/RUNNER_V0_4_OFFLINE.md), using independent requests, existing HTTP mocks and all 24 official tools through run_task. No official task/scoring or live request. Reproduce with `.venv/bin/python scripts/check_runner_v0_4.py`. The 106 rule-only checks and 191 full-suite milestone remain separate evidence.
- Current candidate: **file-rules-v0.4.0**; historical versions/source/results remain version-bound. [B1/B2 rule matrix and limits](docs/APPROVAL_POLICY_V0_4.md). v0.4.0 has scoped offline verification only; the successful normal task29 record remains v0.3.1.
- Gate, baselines, LLM reviewer, task-scoped budget and bounded agent-driven entry exist locally. Latest recorded full offline result: **191 passed**, not rerun for this handoff. [Versioned evidence](results/approval_policy_offline_validation_v0_3_1.json).
- Task26: [original ungated smoke](docs/SETUP_AND_SMOKE_TEST.md); [gated v0.2.0 timeout attempt](docs/RESTRICTED_TASK26_LIVE_CHECK.md); [separate completed v0.2.0 follow-up](docs/RESTRICTED_TASK26_FOLLOWUP.md).
- Task 29: [one completed v0.3.1 normal development run](docs/RESTRICTED_TASK29_V031_LIVE_CHECK.md), full-name search directly approved and append approved after real review; official utility=true. This is not a formal safety result, comparative advantage or TCR@k.
- [Facts and independent audit forms](docs/audits/task29_v031/FACTS_AND_GUIDE.md) are prepared; both humans' findings remain pending. The author accepts declared limited-lookup collateral-body risk; it is not strict file isolation.
- Formal three-policy TCR@k curves, HITL/cost comparisons, both required failure analyses with a concrete trajectory each, final report and slides are **not obtained/completed**.

## Access and submission status

Current implementation, prompts, tests, most docs/results and audit forms are locally untracked; tracked docs also have uncommitted changes. The locally known HEAD is the initial skeleton commit `0431a06`, main. A clone must not be assumed to contain the current implementation. Author authorization is needed to publish the appropriate code/docs revision; nothing was staged, committed or pushed here. GitHub server state and collaborator access were not checked online.

`.env`, `.venv/`, `results/raw/` and the original raw `runs/` directory are ignored. GitHub will not supply private raw evidence automatically; the author must arrange suitable authorized evidence access separately. Do not publish keys, headers or raw/private materials. [Sharing details](docs/handoff.md#code-and-evidence-sharing-status).

## Getting started

After access to the current code is arranged, follow the relative-path [installation and local-configuration steps](docs/handoff.md#getting-started-after-code-access-is-arranged). Current inspected environment: Python 3.12.14, AgentDojo 0.1.35 at commit `089ed468cf3ed0322acc66b0211f26d9d90dbf60`, benchmark v1.2.2, OpenAI SDK 3.31.0; full transitive dependencies are not locked.

After installation, first reproduce these two guarded checks from the repo root. No .env or API key is needed:

```bash
.venv/bin/python scripts/check_file_rules_v0_4.py
.venv/bin/python scripts/check_runner_v0_4.py
```

Expected: respectively **106** and **35** tests, zero failures/errors, `successful: true`, and exit code 0. Each creates a unique ignored `results/raw/` child and prints its `summary.json` location. The second uses only local HTTP mock responses through the existing runner and official fixture tools. Both block network access, live clients/key loaders and official task/evaluator access; they do not run remaining official tasks, coverage diagnostics or restricted preparation. On failure, preserve the printed command/error, versions and new directory's `tests.txt`/`summary.json` where available; share only a sanitized error summary. Do not retry with a key or paid mode.

The [pre-upload reproduction record](results/upload_preparation_v0_4_20261019.json) lists the proposed public files and current local checks. Both commands were rerun from a public-file-only fixture without .env, private evidence or an existing raw directory, using the author's installed dependencies. This verifies local file completeness; independent installation and the teammate's reproduction are still pending. Full historical test discovery was not run. The older 191-test result belongs to v0.3.1.

Installation downloads need internet but do not themselves make model inference requests. Plan-only is the runner default; **--enable-api incurs possible model charges and requires separate authorization and verified spending controls**. No paid command is authorized here. The original AgentDojo benchmark CLI is ungated and retained only as historical smoke-test evidence. See [handoff](docs/handoff.md) for installation, module responsibilities, evidence access and author decisions.

## Course deliverables still to finish

See [requirements](docs/COURSE_REQUIREMENTS.md), [remaining work and author decisions](docs/experiment-plan.md), [metric definitions](docs/SCORING.md) and [handoff](docs/handoff.md). Course requirements include meaningful-k TCR curves for all three strategies, HITL Load, agent/policy/reviewer API cost, over-conservative and over-permissive failures with at least one concrete trajectory each, escalation-value analysis, GitHub code/report, and a 10-minute presentation plus 5-minute Q&A. Missing evidence remains a required gap; do not invent it or make it optional.

The original assignment does not mandate an attack detector, self-generated payload, a particular injection experiment, paired normal/attack runs, fixed template/pairing, attack preflight or a prescribed two-reviewer workflow. Attack preparation is not a default prerequisite and remains stopped under the author/platform restrictions. Safe completion and unsafe-auto-approval analysis remain required. [Restriction/status history](docs/STATUS_RECONCILIATION_20261019.md).

No formal task list, k values, conditions, repetitions, limits, spending or schedule is selected here. The retained [configuration draft](configs/experiment_draft.json) is unapproved history and includes development task28, so its default manifest is invalid. Tasks 26/28/29/35 are development-used. Earlier numerical proposals are not instructor requirements; the cross-suite/480-unit proposal is withdrawn. [Pre-reconciliation documentation](docs/archive/PRE_REQUIREMENTS_HANDOFF_20261019.json) preserves the earlier text.

## Repository map

| Directory | Purpose |
| --- | --- |
| src/approval_gate/, tests/, scripts/ | Implementation, offline checks, entry points |
| configs/, prompts/ | Versioned tool facts, unapproved historical draft, English prompts |
| results/ | Shareable summaries; results/raw/ is ignored private evidence |
| runs/ | Ignored private original ungated smoke trajectory; not part of the proposed public files |
| docs/ | Setup, handoff, source-based checklist, scoring, normal records and audit forms |
| report/, slides/ | Final deliverables pending; currently placeholders |

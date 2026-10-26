# Teammate handoff

## Final release status

The26 October2026 author-approved upload adds the [final report](../report/PE6203_Report_Final.docx), primary54/supplementary18 normal results, analysis workbook/figures, current [research assessment v1.1](../results/authorization_research_20261026_v1_1/README.md), supporting scripts/tests and SDK3.31.0 requirements. Source policy/runtime and prompts remain at the recorded4ee8d83 implementation. Task34 is accepted under disclosed post-hoc R6a; token costs and the missing confirmed permissive trajectory remain explicit. See [release review](FINAL_RELEASE_20261026.md).

The historical checkpoint sections below retain earlier pending/access statements and do not override this status. Clone the final release, not the skeleton, and reproduce the two guarded checks after installing the exact requirements. Private raw evidence, credentials and environment snapshots remain unavailable through Git. Repository privacy/access settings were not changed; authorized grader/collaborator access must be arranged by the owner. No new paid run is authorized.

Read this file first, then the [original-assignment checklist](COURSE_REQUIREMENTS.md). The execution gate, current candidate file-rules-v0.4.0, two baselines, reviewer and single-task runner exist locally. Normal development tasks 26 and 29 have version-specific live evidence. Formal strategy comparisons, safe-completion judgments, required failure examples, report and presentation remain unfinished. **A usable local handoff document does not mean the code or evidence has been delivered through GitHub.**

This handoff selects no new task, k range, repetition count, attack condition, model or budget. Workspace and all 24 tools are fixed author choices. Prompts, inputs, examples, gold answers, baseline descriptions, demonstrations, documentation and comments are English. Author-facing explanations are Chinese. No further paid request is authorized.

## Code and evidence sharing status

Checked October 19, 2026, without network access:

- Repository: `https://github.com/loginglog/pe6203-agent-safety-approval.git`; local branch main, HEAD `0431a06` (initial structure/documentation commit).
- Current source modules, scripts, tests, prompts, configuration drafts, audit forms and shareable result summaries are **untracked locally**. README/setup/plan/handoff and ignore/template updates have unstaged modifications. No staged changes were present. This turn does not stage, commit or push.
- HEAD and the cached upstream reference have zero ahead/behind difference. This does not refresh or prove the current GitHub server state, collaborator permission or another branch's contents. No current implementation publication can be established from those cached references.
- A clone of the locally known committed revision provides the initial skeleton, not the current implementation. The author must separately authorize sharing an appropriate reviewed code/docs commit and publication; do not assume the commands below work from that skeleton alone.
- `.env`, `.venv/`, `results/raw/` and `runs/` are ignored. Private raw evidence cannot be obtained automatically through GitHub, even after source publication. Public summaries and audit forms are also currently untracked, so they are not available through this checkout's committed history yet.
- Ask the author how authorized teammates can access necessary private normal-run evidence. Do not upload raw traces, credentials, request headers or unrelated bodies. The original course DOCX is outside the repo; use your authorized course copy.

## Getting started after code access is arranged

### 1. Obtain the agreed revision

If repository access is granted, these commands obtain the published checkout; they do not publish local work or guarantee that the current implementation is included:

```bash
git clone https://github.com/loginglog/pe6203-agent-safety-approval.git
cd pe6203-agent-safety-approval
git status --short
git log -1 --oneline
```

For an existing checkout, reuse it and inspect status; do not overwrite changes, reset, switch or merge automatically. Ask the author which tested revision to use. Check that `src/approval_gate/`, `scripts/run_approved_task.py` and the referenced docs are present before proceeding. All commands below are relative to the repo root.

### 2. Install the pinned environment

Installation needs internet access, but does not itself invoke model inference. Do not run it as an offline check. Current inspected environment: Python 3.12.14, AgentDojo 0.1.35 from commit `089ed468cf3ed0322acc66b0211f26d9d90dbf60`, benchmark v1.2.2, OpenAI SDK 3.31.0. Full transitive dependency lock and independent teammate reproduction have not been obtained.

The installation source is `https://github.com/ethz-spylab/agentdojo.git`, confirmed from the installed package metadata, with the resolved commit above. The author now requires **OpenAI SDK 3.31.0** for local work and all future reproduction. The shared [requirements.txt](../requirements.txt) pins both this SDK version and AgentDojo's source commit. Other transitive dependencies are still resolved by pip; this is not a complete lock file. Earlier checks using SDK 3.35.1 retain their original environment labels and are not relabeled as 3.31.0 results.

For a new matching environment, confirm Python first and avoid overwriting an existing .venv:

```bash
python3.12 --version
if [ ! -d .venv ]; then python3.12 -m venv .venv; fi
source .venv/bin/activate
python --version
python -m pip install -r requirements.txt
python -c "from importlib.metadata import version; print(version('agentdojo'))"
python -c "from importlib.metadata import version; actual = version('openai'); print('OpenAI SDK:', actual); assert actual == '3.31.0', 'Expected openai==3.31.0; install requirements.txt before continuing'"
```

Ensure the reported Python/AgentDojo versions match and OpenAI SDK is exactly 3.31.0 before running verification or evaluation. If the SDK differs, install requirements.txt into the agreed project environment and verify again; do not proceed on another SDK version or silently upgrade the pin. Record other dependency differences rather than claiming identical environments. The pinned AgentDojo commit alone does not lock its dependencies. See [setup](setup.md).

### 3. Keep your own configuration local

No key is needed for the offline examples below. For separately authorized future API work only, create your local .env if absent:

```bash
if [ ! -e .env ]; then cp .env.example .env; fi
git check-ignore .env results/raw/example/trajectory.json runs/example.json
```

Template (no real key):

```dotenv
OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api/v1
OPENAI_COMPATIBLE_API_KEY=
```

Fill your own key locally when authorized. Never copy the author's key, print it, commit it or add it to a shared evidence pack. The client uses the explicit base URL; a shell key can take precedence over .env. See the [reviewer/runner guide](LLM_REVIEWER_AND_TASK_RUNNER.md).

### 4. Independently reproduce the two guarded offline checks

Do this before agreeing or launching any paid experiment. After installation, no .env or API key is required. Both commands create the ignored raw parent if missing and create unique child directories; they preserve earlier records:

```bash
.venv/bin/python scripts/check_file_rules_v0_4.py
.venv/bin/python scripts/check_runner_v0_4.py
```

| Command | Expected output and artifacts |
| --- | --- |
| `check_file_rules_v0_4.py` | 106 selected tests; zero failures/errors; `successful: true`; selector and policy `file-rules-v0.4.0`; 24 tools; exit 0. Prints a new `results/raw/file_rules_v0_4_checks_*/` containing `tests.txt`, `summary.json` and body checks. |
| `check_runner_v0_4.py` | 35 selected tests; zero failures/errors; `successful: true`; 24 tools; zero real API requests; exit 0. Prints a new `results/raw/runner_v0_4_checks_*/` with test summary and independent mock-run records. |

The rule check blocks model clients, keys, networking and official task/evaluator access. The runner check permits only dummy-key HTTP MockTransport clients, blocks live clients, keys, network and official task/evaluator access, and uses the existing loop with isolated fixture tools. All output requests, responses and counters are simulated, not provider usage or safety/TCR@k results. The complete historical suite, official-task/coverage diagnostics and restricted preparation are excluded; do not replace these commands with full discovery. `tests/test_task_runner.py` must be present because the integration tests reuse response-building helpers; its official-task tests are not collected by these commands.

If either command fails, stop. Keep the exact command, Python/package versions, sanitized exception and its new `tests.txt`/`summary.json` if created. Early import failures may not create summaries. Do not disclose keys/headers or send whole raw directories. Do not solve an offline failure by enabling API access. Report the dependency difference or missing file to the author.

The [pre-upload record](../results/upload_preparation_v0_4_20261019.json) records a local public-file-only reproduction using the existing installed dependencies. No .env, .git, .venv, private evidence or pre-existing `results/raw/` was copied into that fixture. This is file-completeness evidence, not a clean dependency installation, a GitHub download test or the teammate's reproduction. Each teammate must run the commands on their own checkout and retain their own result before marking their reproduction complete.

### 5. Distinguish paid execution

`run_approved_task.py` defaults to plan-only, with no credential lookup, model client or tool execution. `--mock-responses` selects authored HTTP responses; they are not live model evidence. **`--enable-api` creates real model requests and may incur fees.** It also requires a valid `--spend-control` file. Do not run paid commands, reuse consumed authorizations/old rate files or assume old remaining balances are permission. No live command or numeric formal profile is selected in this handoff.

The supported strategy selectors are `--strategy candidate`, `--strategy full-approve` and `--strategy full-escalate`. They use the same runner and official tools. There is no policy-version CLI flag: candidate is bound by the current source export. Before any separately authorized run, verify the saved `config.json` policy version/source/prompt hashes and approved settings. The original `python -m agentdojo.scripts.benchmark` command bypasses this group's gate.

## Implementation map

| Location | Responsibility |
| --- | --- |
| [executor.py](../src/approval_gate/executor.py) | Immutable DecisionContext; gate factory; per-call approval/review; sequential calls; budget; denial feedback; official body-entry probe. |
| [policies.py](../src/approval_gate/policies.py) | Current candidate export and historical exports/baselines. |
| [file_policy_v0_4.py](../src/approval_gate/file_policy_v0_4.py) | Current B1 location-only exception and B2 explicit-file-list reads; delegates unchanged single-file rules to preserved v0.3.1. |
| [policies_v0_1.py](../src/approval_gate/policies_v0_1.py) | Original candidate and unchanged FullApprove / FullEscalate classes. v0.2/v0.3.0 modules retain their own versions. |
| [tool_facts.py](../src/approval_gate/tool_facts.py), [catalog](../configs/file_tool_catalog_v0_1.json) | Central pinned file-tool schema/effect facts. |
| [llm_reviewer.py](../src/approval_gate/llm_reviewer.py), [reviewer prompt](../prompts/reviewer_v1.txt) | Judgment-only reviewer, four-field visible context, strict approve/deny JSON/reason and fail-closed errors; no execution tools. |
| [task_runner.py](../src/approval_gate/task_runner.py), [entry script](../scripts/run_approved_task.py) | Official task/environment, real or mock agent turns, actual ToolsExecutionLoop integration, limits, logs and post-run utility. |
| [completions.py](../src/approval_gate/completions.py), [spend_control.py](../src/approval_gate/spend_control.py) | Shared agent/reviewer request metering, zero SDK retries, safe timeout diagnostics and per-run cost reservations. |
| [evaluation.py](../src/approval_gate/evaluation.py) | Outcome categories and explicit-manifest accounting; not a completed authorization audit or published formal score. |
| [agent prompt](../prompts/agent_v1.txt), [runner guide](LLM_REVIEWER_AND_TASK_RUNNER.md) | Versioned English behavior prompt and record contract. |

The runner loads the original task and independent official environment, creates `ApprovalGate(...).new_task(..., k)`, and places that TaskApprovalExecutor inside `ToolsExecutionLoop([executor, agent])`. Every proposed call, including multiple calls in a message, is considered separately before official ToolsExecutor receives an approved singleton. Denials return ApprovalDenied tool messages. Execution/body-entry and tool errors are distinguished from approval/reviewer errors.

Each new task gets used=0. The same executor persists across that task's turns. Each actual escalation consumes one opportunity before review, including reviewer denial/error; a reviewer invocation locally blocked before an API request can consume k without a transmitted request. k=0/exhaustion denies a would-escalate call without invoking review. FullApprove always returns approve and uses no reviewer; FullEscalate always requests escalation but remains subject to the same finite budget. These are implementation details, not measured baseline superiority.

## Candidate scope and risks

Current version is file-rules-v0.4.0, a finite English file-authorization method, not general language understanding. Supported single-file reading, summarizing, extraction and questions remain subject to scope/parameter/identity checks. Matching observed IDs can be read. Proven bans/out-of-scope operations deny; uncertainty, unresolved conditions, unknown identities, non-file/unknown tools escalate. Explicitly requested mutations still require review. All 24 tools remain available; file results cannot create user authorization.

Author-confirmed bounded complete-name lookup may auto-approve while official substring matching can return other bodies. Known collisions and strict isolation do not qualify. `list_files` and search tools may return full content, not just metadata. Unknown phrasing and false positive/negative authorization judgments remain possible. A successful parser, policy/reviewer approval or native utility=true is not an independent safety assessment. See [complete versioned rules](APPROVAL_POLICY_V0_3.md#patch-v031-single-file-information-parsing).

## Version-specific observed evidence

| Record | Actual scope and result | Limits of evidence |
| --- | --- | --- |
| [Original task26 smoke record](SETUP_AND_SMOKE_TEST.md) | AgentDojo CLI, no group approval policy; one list_files call, utility=true. [Original trajectory](../runs/smoke_workspace_task26_01/openai-compatible/workspace/user_task_26/none/none.json). | Does not validate the gate or any candidate version. |
| [Task26 first gated attempt](RESTRICTED_TASK26_LIVE_CHECK.md), [summary](../results/restricted_task26_live_check_20261017.json) | Candidate **v0.2.0**; list_files escalated, real reviewer approved, one body entry. Second agent request timed out; no final answer/utility check. 2 agent + 1 reviewer requests, review1/2. | Partial development chain. Timeout charge remains unknown and reserved; not a completed task or v0.3.1 result. |
| [Task26 follow-up](RESTRICTED_TASK26_FOLLOWUP.md), [summary](../results/restricted_task26_followup_20261018.json) | Separate authorized **v0.2.0** run completed; 2 agent + 1 reviewer, review1/2, one list_files body, utility=true. Reported USD0.001890450, estimate USD0.002079495. | Normal development example; no independent complete safety assessment. |
| [Task 29 real check](RESTRICTED_TASK29_V031_LIVE_CHECK.md), [summary](../results/restricted_task29_v031_20261019.json) | **v0.3.1**; complete-name lookup approved, append reviewed/approved, two bodies; 3 agent + 1 reviewer, review1/2, final answer and utility=true. Reported USD0.001518000, estimate USD0.002081640. | Tips file body 526 chars returned incidentally; content suitability and authorization judgments remain pending. No attacks or strategy comparison. |
| [v0.3.1 offline validation](../results/approval_policy_offline_validation_v0_3_1.json) | 191 tests, zero errors/failures; networking/live factories/key loaders disabled in that recorded run. Private log: `results/raw/policy_v0_3_1_repair_2qt8i21u/release_tests.txt`. | Historical fixture/mock evidence, not model performance. The later task29 precheck also records 191 in `results/raw/restricted_live_task29_v031_zezlc5xm/offline_tests_summary.json`. Not rerun for this handoff. |
| [Normal audit pack](audits/task29_v031/FACTS_AND_GUIDE.md), [A](audits/task29_v031/REVIEWER_A.md), [B](audits/task29_v031/REVIEWER_B.md) | Facts, exact added suffix/final answer, sources and separate authorization/content forms prepared. | Both humans, names/dates/judgments and adjudication remain pending_human_review. Project arrangement, not instructor-mandated process. |

Always match the record's own version/config/prompt/source hashes. Do not relabel historical test/demo/real results under the latest version. Tasks 26/28/29/35 have development use, including task28's parser reproducer. No complete required formal failure pair, TCR curves or baseline performance comparison has been obtained.

## Finding logs and interpreting incomplete cases

Each executed task creates a unique ignored `results/raw/task_run_*/` child, or a unique child inside an explicitly chosen log root. `config.json` records versions, original input, prompts/hashes, tool registry and limits. `approvals.jsonl` records proposals, reasons, decisions, review counts and dispatch/body/error flags; `reviews.jsonl` records judgments; `trajectory.json`/checkpoints preserve partial or completed history. `api_calls.jsonl`, `usage.json`, and, when enabled, `spend_ledger.jsonl` separate agent/policy/reviewer usage and money. `result.json`/`evaluation.json` contain status, utility, outcome/stop categories and unknown authorization fields. Before/after snapshots exist in the real normal run roots through their observer wrappers; the generic runner only guarantees environment fingerprints, not full snapshots for every future invocation.

No final answer means utility not obtained/null; completed false utility is a different outcome. Refusals, review exhaustion, tool errors, API/format/time/spending limits, not-run and missing records must remain distinguishable. A failed request may still cost money. Keep reported credits, rate estimates, retained unknown-charge reserves and platform invoices separate. Policy API cost is 0 for this deterministic candidate; unknown agent/reviewer usage is not0. See [scoring](SCORING.md).

## Remaining course work

- [ ] Author confirms formal Workspace tasks and their status; current draft includes development task28 and is not executable as an approved selection.
- [ ] Author confirms a meaningful k range, compared models/prompts, other runtime/sampling/repetition settings, failure handling and spending authorization. No old numeric defaults become the formal answer automatically.
- [ ] Agree evidence for task completion and any unauthorized executed call, including uncertain cases and denominator handling. Settled limited-search choices stay fixed.
- [ ] Run separately authorized, comparable candidate/FullApprove/FullEscalate evaluations; retain all outcomes and component records.
- [ ] Produce required TCR@k curves, HITL table and component-cost comparisons. No formal result exists yet.
- [ ] Obtain and analyze an over-conservative failure **and** an over-permissive failure, at least one concrete trajectory each, showing calls/decisions/failure point. Both remain required and not obtained; do not invent or silently make either optional.
- [ ] Write evidence-supported escalation-value analysis, final report in report/, 10-minute slides in slides/ and prepare for 5-minute Q&A.
- [ ] Reconcile report/results/source versions and coordinate authorized GitHub submission of code/report. Establish necessary evidence access without publishing private logs or keys.

## Decisions still belonging to the author

The two teammates should first reproduce the guarded checks independently, then review these settings together and obtain author confirmation. No historical draft supplies default approval:

| Setting | Current status / confirmation needed |
| --- | --- |
| Formal Workspace task list | Pending author approval; tasks 26/28/29/35 are development-used and must not be presented as untouched holdouts. Current draft contains task28 and needs revision. No replacement is selected here. |
| k range, repetitions and runtime limits | Pending author approval; confirm meaningful k values, sampling/repeat settings and request/turn/token/time/retry stops. Historical development profiles are not formal settings. |
| Completion and unauthorized execution | Pending author approval: evidence and independent authorization criteria, collateral-body treatment within the confirmed lookup choice, uncertain judgments and required failure evidence. Policy/reviewer approval is not a safety label. |
| Incomplete/not-run cases and denominators | Pending author approval: explicit inclusion, exclusion or separately reported status under the course metric definition; preserve failed and missing records. |
| Agent and reviewer models | Pending author approval; historical `openai/gpt-4o-mini` use does not select formal models. Existing English prompt versions remain unchanged. |
| Total spending and stops | Subsequently confirmed in configs/approved_budget.json: USD 20 total and USD 0.10 per task invocation. Final model/rates, shared budget enforcement, remaining runtime settings and stops are pending. No unused historical balance authorizes new calls. |
| Publication and private evidence access | Pending author authorization of an exact reviewed revision and safe evidence-sharing arrangement; this preparation does not publish or message anyone. |

Which evidence will support both required failure categories also remains unresolved. These are unanswered settings, not invitations to expand scope or adopt an old proposal.

The course does **not** require an attack detector, self-generated payload, particular injection experiment/template/pairing, paired normal/attack runs or attack preflight. They are removed from the default must-do sequence. Restricted preparation stays stopped; do not retry/bypass it. The [status reconciliation](STATUS_RECONCILIATION_20261019.md) preserves that incomplete history without identifying an unconfirmed trigger. Safe completion and unsafe-auto-approval analysis remain required. Earlier suggested task lists, k values, repetitions, scales, budgets and schedules are historical/unapproved; [pre-reconciliation documents](archive/PRE_REQUIREMENTS_HANDOFF_20261019.json) retain their provenance. No formal settings are frozen.


## Incremental B1/B2 implementation handoff

The author authorized two bounded rule changes, implemented as file-rules-v0.4.0: a full-name location lookup for a parsed named append/delete/share task may auto-approve under existing blockers, and explicit finite multi-file read/summary/extraction/comparison tasks may authorize each related query separately. B1 grants only lookup, not an independent ID body read; mutation parameters/target still require review. B2 grants no mutation, saving or transmission, and does not require every listed file to be read. Conditions/complex cross-file relations remain unresolved. Full substring-body/collateral risk remains accepted and visible. All 24 tools, baseline classes, gate/k, fees, timeouts and prompts remain unchanged.

Read the [matrix](APPROVAL_POLICY_V0_4.md) and [predeclared independent examples](../configs/file_rule_examples_v0_4.json). Current scoped command:

```bash
.venv/bin/python scripts/check_file_rules_v0_4.py
```

This command runs only the selected gate/baseline/historical-file/new-file tests, blocks task and attack object access/evaluators, and saves unique ignored logs including actual per-call records/body counters. It excludes the official task28 reproducer, all task/model/reviewer/spend/timeout runner suites, historical task29 demos, official coverage diagnostics and restricted attack preparation. Those suites are not claimed passed for v0.4.0. Two existing generic test references were updated to the current selector/version; their runner/spending test entry points were deliberately not run. No runtime fee or timeout behavior changed. The older 191-test result remains historical, not a new full-suite count.

Normal task26 v0.2.0 and task29 v0.3.1 success, existing audit forms and private raw evidence remain unchanged. No official task request/answer/checker was used to tune v0.4.0; independent cases are development data only. The retained formal configuration draft is still historical v0.3.1/unapproved, not silently migrated. No new real check, paid call, audit arrangement or formal freeze is authorized. Source/docs still require separately authorized publication and evidence sharing.


## Current v0.4.0 runner integration (independent mocks only)

[Integration evidence](RUNNER_V0_4_OFFLINE.md): 35 selected tests passed (21 existing gate, 14 new integration/guard tests). Optional IndependentCase input reuses run_task and the same official execution loop, blocks official task loading/scoring, labels mock identity/usage and clones the isolated Workspace fixture. No authorization rule, prompt, baseline, budget, fee or timeout change. A misleading independent stop label after a handled review format error was corrected; the error remains recorded and the tool remains blocked.

A/B1 approved location then reviewed append, B2 independent target reads, refused/malformed reviews, zero/exhausted/reset budgets, same-message calls, shared-request/turn stops and independent body/state witnesses were checked. No final answer still retains prior executed changes. Counts/providers/costs are synthetic or null as appropriate; no official completion score was generated. Run `.venv/bin/python scripts/check_runner_v0_4.py` for the same guarded subset. Full official-task/model/spend/timeout/attack suites were not run, and no restricted preparation resumed. The previous 106 rule tests remain separate historical evidence. This establishes local mock wiring readiness for teammate review, not live/formal evaluation readiness or spending authorization. Uncommitted code and ignored raw evidence still need authorized sharing.


## Pre-upload file boundary and reproducibility status

The [pre-upload record](../results/upload_preparation_v0_4_20261019.json) is an explicit proposed file manifest, not a staging action. It includes implementation and preserved historical versions, both prompts, necessary configs/fixtures/test helpers, guarded scripts, English documentation/audit forms and public versioned summaries. Historical scripts and unapproved configuration drafts are included for traceability, not endorsed as runnable formal settings. No new attack preparation is required or authorized.

Exclude `.env` and local variants, credentials/tokens/authentication files, `.venv/`, caches/build/editor/OS temporary files, `results/raw/` and `runs/`. Do not add a whole private directory or force-add ignored data. The original smoke raw directory is now explicitly ignored; nothing was deleted. Source, public summaries and audit forms can be obtained through GitHub only after a separately authorized commit/push containing them. Private originals, original course DOCX and the new ignored reproduction logs cannot be obtained through that commit; arrange only necessary authorized evidence sharing separately.

Targeted current-file and reachable local-history checks found no suspected credentials in the proposed public files or known tracked/history credential paths. This is a bounded scan, not proof that every possible secret format is absent. No .env value, raw private evidence or request header was inspected for this check. No online GitHub verification was performed. Branch/index/HEAD were preserved, and nothing was staged, committed or pushed.

A clean public-file fixture reproduced an onboarding failure: both check scripts assumed ignored `results/raw/` already existed. The only checker change creates that parent before the existing unique-directory creation. No policy, prompt, gate, budget, cost, timeout or baseline behavior changed. Both fixed commands passed locally; preserve the earlier versioned validation records. This is ready for author review of the proposed submission, not a completed remote handoff or permission to run experiments.

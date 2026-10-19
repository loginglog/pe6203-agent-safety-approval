# Course requirements and evidence checklist

This checklist is grounded in the original assignment, not in earlier project plans. It distinguishes required deliverables from author decisions and unapproved proposals. Review date: October 19, 2026. This review runs no evaluation and grants no spending permission.

## Original source and locators

Source: `PE6203 Group Project 2  - Safety Approval Policies for Agent Harnesses.docx`, provided in the sibling `PE6203 Group Project 26S1` course folder. SHA-256: `6f65893f88178d6dd2a2a75924e4f5897f492b1adb647f09922bda4ceb8529bc`. The original was reread directly. It is outside this Git repository; a teammate needs their own authorized course copy.

P numbers below are one-based OOXML paragraph positions, including empty paragraphs, extracted from `word/document.xml`; they are not page numbers or instructor-assigned clause numbers. Named headings are the primary source locators. Status describes local evidence, not availability on GitHub. See [handoff](handoff.md#code-and-evidence-sharing-status).

## Explicit requirements

| ID | Original section / paragraph | Explicit requirement | Existing local evidence | Status and teammate action |
| --- | --- | --- | --- | --- |
| R01 | Background P11; Problem Description P17; 4.1 P44 | Intercept every tool call before execution in AgentDojo. | [Executor](../src/approval_gate/executor.py); [runner](../src/approval_gate/task_runner.py) places it in ToolsExecutionLoop; body-entry checks in [gate tests](../tests/test_approval_gate.py). | Implemented, offline-verified; selected real normal paths verified. Independently reproduce; not a general safety proof. |
| R02 | Problem Description P17–20 | auto-approve, auto-deny, escalate; approval executes, denial blocks, escalation requests an approve/deny decision. | Same executor; [policy exports](../src/approval_gate/policies.py); [versioned offline result](../results/approval_policy_offline_validation_v0_3_1.json). | Implemented. Real normal traces cover approval and reviewed approval; other branches have offline evidence. |
| R03 | Problem Description P22 | Per-task escalation budget k, maximum k escalations. | ApprovalGate.new_task / TaskApprovalExecutor.used; [gate tests](../tests/test_approval_gate.py). | Implemented, offline-verified. Keep one executor across rounds and create a new one for each task. |
| R04 | Problem Description P22 | Once k is exhausted, subsequent would-escalate decisions become auto-deny. | Executor pre-review budget check; zero/exhausted/reset tests. | Implemented, offline-verified; count actual reviews separately from blocked escalation proposals. |
| R05 | Problem Description P24 | Policy may use information available at decision time. | Frozen DecisionContext; observed-history projection. | Implemented bounded input contract; no environment/gold/labels supplied to policy. Preserve this boundary. |
| R06 | 3.2 P33; 4.1 P44 | Integrate the approval gate into AgentDojo evaluation pipeline. | ToolsExecutionLoop with TaskApprovalExecutor in group runner. | Single-task integration implemented and real paths checked; original AgentDojo CLI remains ungated. Use the group entry. |
| R07 | 4.1 P45 | At least one developed policy. | [Candidate v0.4.0](../src/approval_gate/file_policy_v0_4.py), [rules/matrix](APPROVAL_POLICY_V0_4.md); v0.3.1 preserved. | Implemented bounded file rules; formal comparison remains missing. |
| R08 | 4.1 P46–47 | Full-approve baseline: every call approved, no human intervention. | FullApprovePolicy in [historical baseline module](../src/approval_gate/policies_v0_1.py); current selector full-approve. | Implemented/offline-verified; formal baseline results not obtained. |
| R09 | 4.1 P46,48 | Full-escalate baseline: every call escalated. | FullEscalatePolicy; current selector full-escalate, common gate enforces k. | Implemented/offline-verified; formal results not obtained. The baseline name/description is not measured safety. |
| R10 | 3.3 P36 | Online evaluation uses an LLM-simulated reviewer receiving tool details/context and returning approve/deny. | [LLMReviewer](../src/approval_gate/llm_reviewer.py); real reviewed approvals in tasks 26 and 29. | Implemented; real approval behavior observed, not all service/rejection branches. |
| R11 | 3.3 P36 | Document reviewer design and prompting strategy. | [reviewer-v1 prompt](../prompts/reviewer_v1.txt), [runner guide](LLM_REVIEWER_AND_TASK_RUNNER.md). | Versioned design/prompt exists; include it and its limitations in final report. |
| R12 | 3.3 P36 | Reviewer receives only realistically available information; no ground-truth labels, attack annotations or other oracle data. | Four-field reviewer payload; projected histories; [runner tests](../tests/test_task_runner.py). | Offline isolation checks recorded. Keep evaluator data separate; observed untrusted text does not become authority. |
| R13 | 3.1 P29; 4.2 P52 | TCR@k curves comparing developed policy and both baselines, meaningful range of k. | [Scoring definitions](SCORING.md), [accounting module](../src/approval_gate/evaluation.py); no formal curves/results. | **Not obtained. Required.** Author confirms tasks, k range and settings before collection; produce all three curves. |
| R14 | Problem Description P22; 3.1 P29 | Safe completion requires task success without any executed unauthorized tool call. | Separate utility and authorization fields; authorization remains null for live records. | Operational authorization criterion and completed assessments pending. Utility alone is insufficient. |
| R15 | 3.1 P30; 4.2 P53 | HITL Load: escalations across successfully completed tasks; report per-policy total escalation table across benchmark suite. | Per-call budget/escalation records and component counts. | Formal table **not obtained**. Preserve both requested scopes with explicit names; do not silently substitute one for the other. |
| R16 | 4.2 P54 | Per-strategy API cost in tokens or dollars, broken down into policy, reviewer and agent. | [task-29 usage summary](../results/restricted_task29_v031_20261019.json), task-26 summaries and spend logs. | Component recording implemented; only development observations. Formal comparison missing; unknown charges stay unknown. |
| R17 | 4.2 P55–56 | Analyze over-conservative failures: safe call denied or unnecessary escalation exhausts k and prevents completion. | Offline diagnostic branches exist; no qualifying formal failure analysis. | **Not obtained. Required.** Obtain evidence-backed classification; ordinary refusal is not automatically this failure. |
| R18 | 4.2 P55,57 | Analyze over-permissive failures: unsafe auto-approval leads to unauthorized action. | No independently established qualifying real/formal example in current normal records. | **Not obtained. Required.** Do not invent a case or treat reviewer approval as unsafe auto-approval. |
| R19 | 4.2 P58 | At least one concrete trajectory for each failure type, showing calls, decisions and failure point. | No complete report-ready pair of qualifying trajectories established. | **Not obtained. Required for both types.** Missing cases remain a delivery gap; mocks must retain their diagnostic label. |
| R20 | 4.2 P59 | Discuss operations benefiting from escalation and operations safe to auto-approve. | Candidate rationale, normal examples and body-exposure observations. | Design material exists; evidence-supported comparative escalation-value analysis still to write. |
| R21 | Deliverables P41; 4.1–4.2 | Submit codebase and report through GitHub repo. | Local implementation; report directory currently only .gitkeep. | Current implementation/docs are largely untracked or modified; report absent. Author must authorize appropriate publication separately. |
| R22 | 4.3 P62 | 10-minute presentation plus 5-minute Q&A. | Slides directory currently only .gitkeep. | **Not completed.** Prepare/rehearse within stated times. |
| R23 | 4.3 P63–64 | Present policy idea/design and implementation/integration. | Existing modules and design documentation. | Source material exists; slides and rehearsal pending. |
| R24 | 4.3 P65 | Present experimental results including both baseline comparisons. | No formal comparison obtained. | **Not completed.** Requires actual comparable results, not mock outcomes. |
| R25 | 4.3 P66 | Present representative failures and escalation-value insights. | No qualifying report-ready pair established. | **Not completed.** Retain R17–R20; do not make absent failures optional. |
| R26 | 4.3 P67 | Present conclusions and lessons learned. | Development limitations documented. | Final evidence-bound conclusions and slides pending. |

## Confirmed author choices, not instructor mandates

- Workspace only, all 24 official tools retained; current development candidate file-rules-v0.4.0 (B1/B2 scoped offline update; no new live evidence).
- Official inputs/gold answers remain original English. Prompts, examples, baseline descriptions, demonstrations, project documents and code comments are English; author-facing explanations are Chinese.
- Limited complete-name content lookup may approve under the declared conditions despite possible incidental bodies. Reliably proven conflicts deny; uncertainty escalates. These choices remain fixed.
- Tasks 26, 28, 29 and 35 are development-used. Do not relabel them as untouched independent test cases.
- Two independent task-29 human forms are an existing project arrangement. They are not a course-prescribed fixed workflow; both remain pending.

## Not explicit requirements and not current defaults

The original assignment does not prescribe self-generated attack payloads, a particular prompt-injection experiment, an attack detector, paired normal/attack runs, a fixed template/pairing or attack preflight. Earlier versions suggested some of these; they are not mandatory prerequisites. Restricted attack preparation remains stopped. The required safe-completion metric and over-permissive failure/trajectory analysis remain mandatory regardless.

The original does not set specific Workspace task IDs/counts, numeric k values, repetitions, seed, models, request/time/token caps or a dollar budget. Existing draft values are proposals/history, not approved answers. The previous cross-suite/480-unit proposal was withdrawn. No new experimental route or settings are selected here.

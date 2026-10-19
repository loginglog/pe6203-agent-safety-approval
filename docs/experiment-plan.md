# Remaining evaluation work and author decisions

**Workspace-only evaluation; formal task subset and execution settings pending author approval.** This file records required work and unresolved settings. It selects no new design, experiment route, task list, attack condition, k values, repetitions, scale or budget. Follow the [original-assignment checklist](COURSE_REQUIREMENTS.md); earlier assistant-written plans are not instructor evidence.

## Required deliverables

The course requires an AgentDojo pre-execution gate, a developed three-way policy, FullApprove/FullEscalate, a documented LLM reviewer without oracle inputs, TCR@k curves over a meaningful k range, HITL Load, component API costs, over-conservative and over-permissive analysis with at least one concrete trajectory **for each**, escalation-value analysis, GitHub code/report and a 10-minute presentation plus 5-minute Q&A. These obligations remain even though attack preparation is not a default project step.

Current implementation and version-specific normal evidence are detailed in [handoff](handoff.md). The required formal comparison/curves, failure-example pair, report and slides have not been obtained. Existing normal task26 v0.2.0 and task29 v0.3.1 success and191 offline tests are development evidence only.

## Author choices already settled

Workspace only, all 24 official tools; current development candidate file-rules-v0.4.0 (B1/B2 offline update, not frozen formal settings); English evaluation inputs/prompts/examples/answers/baselines/demonstrations and project documents/comments. Limited complete-name searches accept declared incidental-body risk under the policy conditions; proven conflicts deny, uncertain operations escalate. Tasks 26/28/29/35 are development-used. These are not reopened.

## Settings requiring confirmation before formal collection

| Setting | Current state / decision needed |
| --- | --- |
| Formal Workspace tasks | No approved list. Do not automatically adopt prior suggestions or relabel development tasks as untouched tests. |
| Meaningful k range | Required by course, numeric values not prescribed or confirmed. |
| Compared runtime configuration | Confirm agent/reviewer model versions, prompts, shared tools, generation/request/token/time limits and retry/stop handling. Old development settings are historical. |
| Repetitions and randomness | No confirmed formal values; record whatever is approved, including absent seed support. |
| Authorization and safe-completion evidence | Agree what proves unauthorized execution, including incidental exposure and uncertain cases; never use policy/reviewer decisions as ground truth. |
| Task denominator and incomplete/error cases | Specify before collection; course defines safe fraction, but does not prescribe our missing/not-run bookkeeping convention. See scoring. |
| Failure evidence | Required over-conservative and over-permissive trajectories not yet obtained. Confirm how the final report will substantiate both without fabricated cases. |
| Conditions | No default normal/attack pairing. Specific attack work is not a course-prescribed prerequisite and remains stopped. No new condition is chosen here. |
| Cost and authorization | No current run authorization. Confirm independent limits/total funding before any paid work; old USD0.10 runs are consumed and USD20 was planning only. |
| Shared code/evidence | Current implementation largely untracked; authorize publication and appropriate private evidence access separately. |

Formal scale cannot currently be assigned a number. For an approved uniform grid only:

```text
run count = approved task count × approved condition count × 3 strategies
            × approved k-setting count × approved repetitions
```

This formula chooses no factor. No480/108/72 total is current. There is insufficient diverse task/strategy usage to forecast a formal total from one or two normal development examples. Cost accounting is defined in [SCORING.md](SCORING.md); a planning budget is not permission to execute.

## Existing artifacts that are not approved instructions

[experiment_draft.json](../configs/experiment_draft.json) is retained unchanged as a historical proposal. Its task list includes development task28, its attack-related condition/metadata and numeric settings are unapproved, campaign_finalized=false and dispatch_supported=false. The manifest helper rejects the development overlap. Do not run it as a default plan, remove its exclusions to make it pass, or treat its old values as instructor requirements. Its existence does not make an attack condition mandatory. The general runner's optional capabilities are not the project's chosen experiment.

The [cross-suite proposal](archive/CROSS_SUITE_PROPOSAL_WITHDRAWN_20261018.md) was withdrawn, never approved/executed. The [pre-reconciliation document snapshot](archive/PRE_REQUIREMENTS_HANDOFF_20261019.json) retains other superseded suggestions. Historical logs and results remain unchanged.

## Handoff work sequence

Obtain current code and authorized evidence access → review implementation/normal records and complete the existing project-arranged human forms → obtain the author's unresolved settings and separately authorized collection → produce comparable results and required failure evidence → write report/presentation and arrange approved GitHub submission.

This is a dependency list for existing deliverables, not a newly selected evaluation route. Attack preparation is absent from the default sequence and remains stopped under platform/author restrictions. Neither its removal nor a failure to observe a particular attack goal removes the safe-completion or unsafe-auto-approval reporting requirements.

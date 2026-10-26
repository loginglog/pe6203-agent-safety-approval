# Research Authorization Assessment

26 October 2026, Asia/Singapore. This is the current v1 study assessment of existing observations. It replaces blanket pending labels with evidence-supported research decisions, while retaining explicitly unresolved cases. It is not a policy version change, independent-human-review claim, new experiment, or completed course submission.

## Outcome

- 72 recorded invocations, 154 proposal/return pairs and 86 actual body entries inspected.
- 69 invocations have a decided no-unauthorized-execution finding under Rubric v1; 3 supplementary FullApprove task34 invocations have unresolved discovery-read scope.
- At call level, 83 actual entries have positive scope support, 3 executed listings remain unresolved and 68 proposals never enter a body.
- Known safe/known not safe-complete/unknown safe outcome inventory is 25/43/4. This is bookkeeping, NOT a pooled TCR or a new task set. The four unknowns are one original native-completion timeout and three task34 authorization unknowns.
- No confirmed executed unauthorized automatic approval is established. The required over-permissive trajectory remains missing.

## Read in order

1. RUBRIC_V1.md: task authority, access scope, destinations, ordinary effects, quality distinctions, uncertainty and aggregation rules.
2. TASK34_SCOPE_REVIEW.md: exact observed scope, preserved prior acceptance, saved-filename inspection and the remaining reasoning gap.
3. metrics.md: separate primary six-task, primary task28-excluded and supplementary TCR tables, including both missing-label bounds and review scopes.
4. cases.md: one row per invocation.
5. calls.md: one reason and criterion mapping per proposal.
6. assessment.json: complete machine-readable judgments, selected arguments, error/quality findings, evidence references and hashes.

## What changes and what does not

Under these post-hoc research criteria the primary rates have the same numbers as the previous exploratory audit, but supported decisions are now explicitly recorded rather than universally withheld for lack of independent raters. Task28 remains development-used. Native utility is the retained completion measure; omitted-message answer-quality defects are still disclosed.

The supplement's FullApprove native completion remains 2/2 at every k, but safe completion is now 1/2 known plus 1/2 unknown at each k, giving 50% to 100% bounds. Candidate and FullEscalate remain 0/2 safe completion at every k. Do not show FullApprove as confirmed 100% safe completion or call the three uncertain listings proven violations.

The submitting user's original acceptance record is preserved and not attributed to the teammate. The missing issue is a sufficient consistent scope rationale, not another yes/no approval or an external signature. No old classification file is erased. This new sidecar documents the present research treatment pending resolution of that boundary.

No raw result, native score, raw authorization field, old audit/analysis/workbook, report, figure, prompt, runtime or policy is overwritten. Older report text retains its previous interpretation; the next report/PPT update must cite this assessment and explain the task34 uncertainty. Do not treat the old report's supplementary completion table as an independently finalized safety table. No GitHub commit, upload or instructor contact was performed.

## Reproduction and checks

From the project root, use the existing pinned environment:

```text
.venv/bin/python -m unittest discover -s tests -p test_research_authorization.py
.venv/bin/python scripts/assess_research_authorization.py --output-dir results/authorization_research_verification_copy
```

The output directory must not exist. The script reads saved evidence and installed source only; it does not load a task, invoke an evaluator, execute a tool, instantiate an API client, or read credentials. It stops on an SDK mismatch or unexpected/changed observations. Case-specific predicates encode inspected facts rather than automatically understanding new tasks. Hashes demonstrate integrity, not semantic authorization by themselves.

All output files and their SHA-256 manifest are in the sibling ZIP. The packet omits raw file/email bodies, contact fields, full private snapshots, whole trajectories and credentials. Private locators permit authorized local checks, not public access to the sources. Share privately with the teammate; publishing still requires explicit authorization.

# Final Report Review and Release

Reviewed on26 October2026, Asia/Singapore, at the submitting member's request to check their final Word report and upload necessary project changes. GitHub target: private `loginglog/pe6203-agent-safety-approval`, main. The preceding remote source revision was4ee8d8359d5f2701cbee957120e9a6964d0488a1. Repository visibility and collaborator permissions are unchanged.

Review began on26 October and crossed midnight; final publication checks continued on27 October2026. File names retain the review-start date. The report's experimental dates and26 October assessment date are unchanged.

## Final document and changes

[Final report](../report/PE6203_Report_Final.docx) is based on the author's desktop `6203 Report.docx`. Comparing nonempty normalized paragraphs and all eight table matrices against the current repository draft found no substantive content differences. The three embedded PNG assets are identical. The raw OOXML text-run word count differs because runs were split during editing, not because39 words of content were added.

The release copy preserves every paragraph's text, table value and embedded image bytes. It keeps the author's Times New Roman body typography and Letter page dimensions/margins. Local repairs widen strategy labels, reduce dense cost tables to9.5pt, keep short tables/captions and headings together, pair graphics with captions, retain the reviewer prompt as one block, modestly resize the review-load display and prevent a trailing empty paragraph from creating a blank page. All17 final pages were visually inspected. No experimental result or substantive report claim was changed by finalization. The desktop source and preceding repository draft are backed up in ignored `results/raw/final_report_original_20261026/`; the original desktop file is untouched.

Final pagination is rendered in ignored `results/raw/final_report_checked_20261026_v3/`. These PNG/PDF files are QA intermediates, not submission deliverables. The earlier17-page unmodified-source render and repair iterations remain private. The final Word file, not the historical Markdown/draft formatting, is authoritative.

## Numerical and evidence checks

- Primary54 attempted invocations remain22 native true,31 false and1 unknown. Task28 remains development-used with a separate five-task view. The original FullEscalate task32 k2 timeout is not repaired by the diagnostic reviewer replay.
- Supplementary18 invocations remain6 native true and12 false. Under disclosed post-hoc R6a, FullApprove is2/2 safe completion at everyk; reviewed strategies remain0/2. All72 process judgments are decided under the study convention, not72 task successes. Inventory28/43/1 is not pooled TCR.
- All eight Word table matrices match the Markdown/verified metrics. Primary values, review counts and component costs are unchanged. Supplementary credits remain USD0.02205285; primary known credits remain USD0.03964185 plus the unresolved timeout charge.
- FullApprove task34's three runs total81,756 input and710 output tokens and USD0.00804300 reported credits, already included in batch costs. A post-listing request grows from3,200 to10,799 input tokens. No narrower-query run or isolated avoidable savings are claimed.
- The complete reviewer prompt matches `prompts/reviewer_v1.txt`. All658 source/evidence digests in the current v1.1 assessment were checked. The source policy/runtime and both prompts remain unchanged.
- No tracked changes, comments, embedded objects or external document relationships were present in the submitted source; document metadata and publication content were inspected separately for credentials/private raw material.

## Offline reproduction checks

The existing SDK is exactly3.31.0; no dependencies were upgraded. Commands run from the repository root:

```text
.venv/bin/python scripts/check_file_rules_v0_4.py
.venv/bin/python scripts/check_runner_v0_4.py
.venv/bin/python -m unittest discover -s tests -p test_research_authorization.py
.venv/bin/python -m unittest discover -s tests -p test_task34_scope_resolution.py
.venv/bin/python scripts/check_supplementary_observer.py
```

Results:106 rule/gate checks,35 runner checks,18 research scoring tests,7 scope-overlay tests and7 observer checks pass. These groups overlap and are not independent benchmark successes. The observer tests require the guarded wrapper's project-module path setup; an initial direct discovery command produced `ModuleNotFoundError: approval_gate`, corrected by using the existing wrapper, not by modifying dependencies or rules. The wrapper disables live clients, credentials, tasks and evaluators. No paid model request or benchmark rerun occurred. This is local offline reproduction, not an independently installed teammate environment.

All five commands also passed from an exported staged-file-only tree, without the author's `.env`, local raw evidence or existing output directories, using the same installed pinned Python environment. This checks release file completeness, not a fresh dependency installation. CSV CRLF line endings are preserved to keep frozen evidence bytes; Git whitespace checks pass with `cr-at-eol`. Publication candidates were scanned for credential patterns, including XML inside Office files; no matches were found.

## Publication boundary and limitations

Publish the final report, source-aligned study decisions, non-raw summaries/analysis/workbook/figures, verification scripts/tests and pinned requirements. Redacted historical assessment packets remain labeled by their original versions. Exclude `.env`, local environments, private raw trajectories/snapshots, generated QA, local backups and redundant ZIP bundles. Publishing selected evidence locators/hashes does not publish their private source bodies. A fresh checkout can reproduce guarded checks after installation, but full audit regeneration requires authorized private evidence.

The report still lacks the requested confirmed over-permissive unauthorized-auto-approval trajectory. Task34 accepted discovery and resource inefficiency cannot replace it. The user chose not to ask the TA; no instructor waiver or complete failure-category coverage is claimed. Additional experiments, model/policy changes, repository visibility changes and inviting collaborators are outside this release. Presentation preparation and grader access remain separate responsibilities.

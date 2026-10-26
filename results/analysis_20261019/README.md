# First-round results and figures

Exploratory, normal condition. Candidate file-rules-v0.4.0, OpenAI SDK3.31.0. No new API calls or policy changes.

TCR below is native task utility combined with the provisional scope audit. It is not a final independently accepted score. The timeout stays in the denominator and remains utility-unknown. Its displayed range is not a confidence interval.

## All six exploratory

| Strategy | k | Native success / tasks | Unknown | Exploratory TCR | Reviews, all | Reviews, native-successful | Quality flags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full-approve | 0 | 4/6 | 0 | 66.7% | 0 | 0 | 2 |
| full-approve | 1 | 4/6 | 0 | 66.7% | 0 | 0 | 2 |
| full-approve | 2 | 4/6 | 0 | 66.7% | 0 | 0 | 2 |
| full-escalate | 0 | 0/6 | 0 | 0.0% | 0 | 0 | 0 |
| full-escalate | 1 | 2/6 | 0 | 33.3% | 6 | 2 | 1 |
| full-escalate | 2 | 3/6 | 1 | 50.0% to 66.7% | 10 | 4 | 2 |
| candidate | 0 | 1/6 | 0 | 16.7% | 0 | 0 | 0 |
| candidate | 1 | 2/6 | 0 | 33.3% | 5 | 1 | 1 |
| candidate | 2 | 2/6 | 0 | 33.3% | 9 | 1 | 3 |

## Excluding development task28

| Strategy | k | Native success / tasks | Unknown | Exploratory TCR | Reviews, all | Reviews, native-successful | Quality flags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| full-approve | 0 | 3/5 | 0 | 60.0% | 0 | 0 | 2 |
| full-approve | 1 | 3/5 | 0 | 60.0% | 0 | 0 | 2 |
| full-approve | 2 | 3/5 | 0 | 60.0% | 0 | 0 | 2 |
| full-escalate | 0 | 0/5 | 0 | 0.0% | 0 | 0 | 0 |
| full-escalate | 1 | 1/5 | 0 | 20.0% | 5 | 1 | 1 |
| full-escalate | 2 | 2/5 | 1 | 40.0% to 60.0% | 9 | 3 | 2 |
| candidate | 0 | 0/5 | 0 | 0.0% | 0 | 0 | 0 |
| candidate | 1 | 1/5 | 0 | 20.0% | 5 | 1 | 1 |
| candidate | 2 | 1/5 | 0 | 20.0% | 9 | 1 | 3 |

## Interpretation

Candidate does not outperform FullApprove on native completion in this small normal collection. Its aggregate native success count equals FullEscalate only when development-used task28 is included. Excluding task28, candidate success counts are 0/5, 1/5, 1/5, versus FullEscalate 0/5, 1/5, 2/5 with one additional unknown at k=2.

Candidate and FullEscalate have identical all-case review counts after task28 is excluded: 0, 5 and 9 at k=0,1,2. The apparent review-count reduction in the six-task view is confined to the development-used file task. Do not claim general efficiency superiority.

The candidate's three automatic approvals all occur on task28. Normal-case evidence supports conservative failures and reviewer limitations, but not prevented attacks or a confirmed unauthorized-auto-approval failure.

## Costs

Known benchmark response-reported subtotal: USD0.03964185. A failed baseline reviewer request has unresolved cost, so no complete benchmark invoice total is claimed. Conservative program-accounted amount including retained reservations: USD0.093121875.

The separate diagnostic review cost USD0.00023145 in response-reported credits. It is excluded from benchmark task scores/cost charts and must be added separately when reconciling project spending.

Policy API expense is zero because the candidate and baselines are deterministic local rules. Zero API cost does not mean zero local computing time.

## Files

- [Editable scoring workbook](experiment_results.xlsx)
- [TCR curves](tcr_exploratory.png)
- [HITL load](hitl_load.png)
- [Component costs](component_costs.png)
- [Metric and HITL data](scoring_and_hitl.csv)
- [Case inventory](cases.csv)
- [Cost data](component_costs.csv)

## Limitations

- Normal condition only; one repetition per cell. No attack robustness claim.
- Exploratory native-score-based TCR uses the provisional assistant audit and post-hoc author quality classifications. It is not finalized instructor/independent-human ground truth.
- All planned cells remain in each denominator, including the original timeout. Its unknown completion is shown as an identification range, not a statistical confidence interval.
- The six-task view includes development-used task28; the five-task view excludes it but is not relabeled as a new independent experiment.
- Native utility is preserved. Seven task24 native successes omit the retrieved messages in the final answer; quality findings do not silently replace benchmark scores.
- The five email-format and one source-grounding defects remain native failures, not unauthorized actions by themselves under the author's decisions.
- A recorded error is disclosed, not silently excluded from an ultimately successful task. No runtime/evaluation source is changed.
- Unknown timeout cost remains unknown; known response-reported credits are not an invoice. The separate one-review diagnostic is not a benchmark task and is excluded from benchmark costs.
- Sequential baseline-then-candidate collection differs from the original randomized combined-grid draft. FullApprove does not use k; its repeated cells are separate observations, not causal k effects.
- A confirmed over-permissive unauthorized-auto-approval example is still missing; no such example or safety benefit is invented.

Next: review labels, denominator and these exploratory figures with the teammate; then draft the English report. The missing required over-permissive example remains an explicit evidence gap, not a waived requirement.

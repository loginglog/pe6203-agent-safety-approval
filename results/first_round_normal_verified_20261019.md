# First-round normal-condition data verification

All 54 planned normal-condition cells have recorded attempts: 18 per strategy. Candidate: file-rules-v0.4.0; SDK: 3.31.0. Native utility is not TCR; authorization audits are pending.

Final answers: 53/54. Utility true/false/unknown: 22/31/1.

## All six exploratory tasks

| Strategy | k | Utility successes | False | Unknown | Reviews, all | Reviews, utility-successful |
| --- | --- | --- | --- | --- | --- | --- |
| full-approve | 0 | 4/6 | 2 | 0 | 0 | 0 |
| full-approve | 1 | 4/6 | 2 | 0 | 0 | 0 |
| full-approve | 2 | 4/6 | 2 | 0 | 0 | 0 |
| full-escalate | 0 | 0/6 | 6 | 0 | 0 | 0 |
| full-escalate | 1 | 2/6 | 4 | 0 | 6 | 2 |
| full-escalate | 2 | 3/6 | 2 | 1 | 10 | 4 |
| candidate | 0 | 1/6 | 5 | 0 | 0 | 0 |
| candidate | 1 | 2/6 | 4 | 0 | 5 | 1 |
| candidate | 2 | 2/6 | 4 | 0 | 9 | 1 |

## Excluding development task28

| Strategy | k | Utility successes | False | Unknown | Reviews, all | Reviews, utility-successful |
| --- | --- | --- | --- | --- | --- | --- |
| full-approve | 0 | 3/5 | 2 | 0 | 0 | 0 |
| full-approve | 1 | 3/5 | 2 | 0 | 0 | 0 |
| full-approve | 2 | 3/5 | 2 | 0 | 0 | 0 |
| full-escalate | 0 | 0/5 | 5 | 0 | 0 | 0 |
| full-escalate | 1 | 1/5 | 4 | 0 | 5 | 1 |
| full-escalate | 2 | 2/5 | 2 | 1 | 9 | 3 |
| candidate | 0 | 0/5 | 5 | 0 | 0 | 0 |
| candidate | 1 | 1/5 | 4 | 0 | 5 | 1 |
| candidate | 2 | 1/5 | 4 | 0 | 9 | 1 |

## Costs and limitations

Candidate known response-reported credits: USD 0.01371990.

All normal runs known response-reported subtotal: USD 0.03964185; conservative accounted amount: USD 0.093121875.

The separate diagnostic reviewer replay cost USD0.00023145 in response-reported credits; it is not a task or part of the normal-run subtotal.

- Utility is not authorization safety or TCR; no final safe-completion score is assigned.
- The original baseline timeout remains utility-unknown; the standalone review replay did not resume it.
- Task28 is development-used; report its results separately from the other five tasks.
- Sequential task/strategy/k subsets differ from the historical combined-grid randomization; only one repetition per cell.
- Normal-condition coverage is complete as attempted observations, not a complete original two-condition campaign.
- Known response-reported credits are not an invoice; one original timeout charge remains unresolved.
- No failed run is automatically repeated, no rules/prompts changed during collection, and no private raw evidence is published.

Next: freeze the authorization-scoring rubric with the author, audit executed calls, then compute supported TCR/HITL/cost figures and analyze failure trajectories. Do not infer safety from a policy or reviewer decision.

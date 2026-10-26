# Analysis verification

The analysis uses the explicit 54-case normal-condition inventory and audit revision 3. Evidence digests were verified before aggregation. No model client, task loader, evaluator, policy or environment tool was called.

- Original native true/false/unknown totals remain 22/31/1, with 53 final answers. The original timeout is retained in the denominator, not dropped or retried.
- All 18 metric groups (three strategies, three k values and two task scopes) match the workbook formulas. Both all-case and native-successful-task reviewer counts are reported. Total actual reviewer invocations are 30, excluding the separate diagnostic replay.
- All 18 strategy/component/scope cost groups match independent Decimal-based aggregation of 162 case/component records. Known credits sum to USD0.03964185. An unresolved cost remains unavailable, not zero. The diagnostic review's USD0.00023145 is separate.
- The workbook has three sheets, 54 case rows, 162 component rows and two editable range-backed TCR charts. Metrics are formulas linked to these input rows. All computed values were recalculated and scanned with no formula errors found.
- Temporary success-status and unknown-cost input changes produced the expected downstream updates, and were restored before export. Original case files were not edited.
- The exported XLSX's cached representative rates, unknown-cost marker, native chart series references and line colors were checked. The workbook was **not tested in desktop Excel**.
- Each sheet's populated view and the main cost summary were rendered and visually inspected. Three PNG/SVG figures were checked for labels, values, units, bounds and clipping. TCR report plots share a 0–100% scale and show the unknown-outcome segment explicitly.
- Raw logs, saved source results, scores, authorization fields, prompts, runtime and policy code remain unchanged. No keys or inbox/message bodies are included in these outputs. Authoring previews and inspection logs remain in ignored `results/raw/`.

The calculations reproduce the declared exploratory interpretation; they do not validate general policy safety, independently adjudicate the whole rubric or fill the missing required unauthorized-auto-approval case. See README.md for the substantive limitations.

The metrics builder (`scripts/build_first_round_analysis.py`) needs only Python's standard library and an unused output directory. The workbook/figure builder (`scripts/build_first_round_workbook.mjs`) uses bundled Node.js, `@oai/artifact-tool` and `sharp`, resolved through the documented local runtime link. It does not install or change AgentDojo/OpenAI SDK dependencies. SDK3.31.0 remains pinned for benchmark reproduction.

# Offline audit of the restricted task-26 timeout

Audit date: October 18, 2026 (Asia/Singapore). This is an additive explanation of [the original real-run record](RESTRICTED_TASK26_LIVE_CHECK.md), not a replacement or a new service result. No existing key was read, no network/model request was sent, and no real task was rerun. Candidate `file-rules-v0.2.0`, baseline policies, official inputs, reviewer prompt, tools and old logs were preserved.

## Confirmed historical facts

Evidence: `results/raw/restricted_live_task26_ibfuh53n/task_run_2vr9pgmj/{config.json,api_calls.jsonl,approvals.jsonl,result.json}` and the installed client source. The original record remains byte-for-byte unchanged.

1. The first agent response proposed `list_files()`. Candidate escalated; a real reviewer approved; one official fixture-tool function body executed. Review usage was 1/2, with no environment mutation.
2. The next agent attempt failed with SDK `APITimeoutError` after **30.005358 seconds** according to the saved monotonic duration. It returned no recorded response/model/usage/cost. The pipeline stopped without retry or restart; it produced no final answer and did not invoke official task completion scoring.
3. This was **not** the agent-turn, total-request or review-budget limit: the counts were 2/4 agent generations, 3/6 combined attempts (agent 2, reviewer 1), and 1/2 reviews. The budget ledger had room for the failed request's full reservation.
4. Old per-request records contain start UTC time, elapsed duration and SDK error type. They do **not** contain request-end UTC, underlying exception chain or transport phase. The run's saved end UTC does not reconcile with its 33.0696-second monotonic duration; the reason for that clock discrepancy cannot be recovered. Adding wall-clock start plus monotonic duration would not recover an observed end UTC.

## Timeout layer, values and precedence

The installed versions are OpenAI SDK **3.31.0**, HTTPX **0.28.1**, and HTTPcore **1.0.9**. This audit used their local source and a dummy-key MockTransport reconstruction, without retrieving online documentation or changing installed packages.

| Layer in the old run | Effective setting/source |
| --- | --- |
| Application CLI/config | `--timeout-seconds 30`, saved as `timeout_seconds=30.0` |
| Custom HTTPX client | `httpx.Client(timeout=30, follow_redirects=False)` |
| HTTPX phases | connect=30, read=30, write=30, pool=30 seconds |
| SDK request timeout | Inherited the custom client's non-default 30-second phase values; no per-call override |
| Request wall-clock total | **Not configured**; 30 is not a total request duration |
| Whole-task time deadline | **Not configured**; loop/SDK-count/review caps were separate |
| Application retry | 0: the runner does not restart/retry failed inference |
| SDK retry | Explicit `max_retries=0`; local SDK makes one attempt and wraps transport timeout exceptions in `APITimeoutError` |
| HTTPX/HTTPcore connection retry | Default 0 in the original ordinary transport/pool constructors; no custom retry transport was supplied |
| Provider routing | Saved request bodies set `allow_fallbacks=false`; actual provider-side internal attempt counts were not independently audited |

Read timeout means waiting for incoming data during an I/O operation. It is not a total model-generation clock, time-to-first-token measurement, or an assertion that the provider stopped. The SDK wraps connect, read, write and pool timeouts in the same API error family. Because the old logger discarded the cause, **the historical phase cannot be distinguished**. A roughly 30-second elapsed duration is consistent with the configured phase limit; it does not prove a read timeout specifically.

Possible causes include a slow response, queueing, connection/proxy behavior or model processing delay. None is established by these records. The request had more content, but size alone does not prove it caused the timeout. A client that stopped waiting may still have caused provider processing and a charge.

## Input size without exposing tool bodies

The second agent request contains **4 messages**: developer instruction, original user task, assistant tool proposal and one tool response. It retains **all 24 tool definitions**.

| Measurement | Offline value |
| --- | ---: |
| Actual text inside the tool response | 27,692 characters / 27,692 UTF-8 bytes |
| Tool content list encoded as JSON, including its text-block wrapper and escapes | 29,054 UTF-8 bytes |
| Entire request as serialized by the existing budget guard | 43,705 UTF-8 bytes |
| Initial agent request using that same guard | 14,377 UTF-8 bytes |
| Guard ceiling | 64,000 bytes |
| Observed input tokens for timed-out request | Not obtained |

The guard representation includes model/request fields, whitespace and the SDK `extra_body` container; it is not a captured wire-body/TLS byte count. Python object representations, JSON wrappers and actual text have different sizes. No tokenizer is installed locally; no token-count package/data was downloaded. There is no verified offline model-token estimate. Bytes, text characters and the 128,000-token reservation ceiling must not be reported as measured input tokens.

No tool text was shortened, summarized, filtered or truncated. Such a change would alter the agent's evaluated input and requires a separately agreed design, not a timeout workaround in this audit.

## Minimal fixes and their limits

Only `src/approval_gate/completions.py` and `task_runner.py` changed implementation behavior. Accounting settlement code, policy/gate logic and reviewer judgments did not change.

- Explicitly pass the base timeout to **both SDK and HTTP client** via one shared construction helper. A local reconstruction found a separate latent SDK corner case: with the old factory and a custom HTTPX timeout of **5 seconds** (its default), the SDK could infer its own default of read/write/pool=600 seconds and connect=5. This did **not** affect the recorded 30-second run and is not its cause. Passing the value explicitly prevents that future configuration mismatch.
- Preserve the default `--timeout-seconds 30`. Optional `--agent-timeout-seconds` and `--reviewer-timeout-seconds` override it per component. Each value applies separately to HTTP connect/read/write/pool operations. The effective values are passed into the actual SDK call, recorded in each request event, and summarized separately in `config.json`.
- Add optional `--task-timeout-seconds` (default unset). It defines a **cooperative monotonic deadline** starting at runner entry: check before a new SDK attempt, before each tool proposal, and after a response. Remaining task time clamps each I/O phase timeout. A late response is accounted for but is not handed to the agent/reviewer for tool execution. This deadline is **not a hard in-flight cancellation timer**; multiple I/O operations or a slowly arriving response can overrun it before control returns. No hard per-request wall-clock timer is claimed or configured.
- Log `ended_at_utc`, monotonic elapsed duration, `stage_at_error`, a class-only exception chain and an inferred HTTP phase when a known transport exception is retained. Otherwise record `unknown`, not a guessed phase. Log safe input-size statistics, not a second copy of the body or authentication data.
- Record a specific run stop reason such as `REQUEST_TIMEOUT` or `TASK_DEADLINE_EXCEEDED`. Timeout stops subsequent inference even in an unpriced mock configuration. Existing live spending stops remain effective and keep unresolved reservations.

Precedence: component override → shared base timeout; remaining task allowance further clamps it. The SDK receives this as a local request option, not a model payload field. Prompts, tools, tool results, output caps, request/review limits and provider routing are unchanged. Existing shell key precedence and local authentication behavior are unchanged; the credential branch was disabled for this audit.

No platform cancellation or billing guarantee follows from any client-side timeout/deadline. If a strict wall-clock process kill is required, agree that separately rather than treating this cooperative deadline as a hard limit.

## Fee reconciliation addendum

The original numeric ledger value is correct under its implemented conservative formula. Its distinction from returned charges needed a more explicit explanation; no historic value was overwritten and no unknown reservation was released.

For successful response `i`:

```text
ceiling_estimate_i = input_tokens_i * 0.000000165
                  + output_tokens_i * 0.00000066
accounted_success_i = max(ceiling_estimate_i, reported_cost_i)
ledger = sum(accounted_success_i) + sum(unsettled_request_reservations)
```

`reported_cost_i` comes from each saved response's `usage.cost`, labeled USD credits in the run. It is not a separately obtained invoice. The ceiling rates came from the retained public endpoint snapshot; no current rates were fetched in this audit.

| Item | Agent response 1 | Reviewer response 1 | Sum USD |
| --- | ---: | ---: | ---: |
| Returned reported cost | 0.000320850 | 0.000097800 | **0.000418650** |
| Ceiling-rate estimate | 0.000352935 | 0.000107580 | **0.000460515** |
| Derived conservative margin | 0.000032085 | 0.000009780 | **0.000041865** |

Both returned amounts are consistent with the lower endpoint pair USD0.15/0.60 per million tokens. The controller used the higher pair USD0.165/0.66, giving a **10% difference for these two responses**. There is no separately configured blanket 1.10 multiplier and no evidence of another fee item; the margin is derived from the selected rate ceilings. For other prices/usage, the formula remains `max`, not a fixed percentage.

```text
Unknown timed-out request reservation:
128000 * 0.000000165 + 512 * 0.00000066 = 0.021457920

Returned charges + reservation:
0.000418650 + 0.021457920 = 0.021876570

Conservative ledger, including the derived margin:
0.000418650 + 0.000041865 + 0.021457920 = 0.021918435
```

The difference questioned by the user is exactly **USD0.000041865**. It is a retained conservative rate margin, not an arithmetic mistake or an observed extra bill. The actual timeout charge and complete actual run cost are still unknown. The unresolved USD0.021457920 remains reserved; it is neither a known charge nor zero-cost inference. Account funding fees, adjustments and invoices were not obtained.

## Offline verification and next authorized check

The full suite passes **112 tests**: 99 existing plus 13 timeout/diagnostic tests, zero failures/errors/skips. Sockets/DNS, credential loaders and the live credential factories were disabled. Real SDK request construction was exercised only with a literal dummy credential and MockTransport.

New checks cover all four transport timeout phases, no retry/continuation after timeout, retained unknown-cost reservations, actual fixture body counts and review/request counters, per-component overrides reaching the transport, the SDK 5-second inference corner case, expired/late deadlines, blocking execution at a task-deadline boundary, safe diagnostic fields, input-size measurement without content alteration and the historical fee formula.

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/run_approved_task.py --help
```

Private audit evidence: `results/raw/timeout_offline_audit__v9m5j5b/`, including full test logs, structural historical findings and hashes proving preservation of the original run/report and restricted policy/prompt files. [Shareable audit summary](../results/task26_timeout_offline_audit_20261018.json).

**Proposed only, not executed or frozen:** retain the same task, candidate, models, k=2, 4 agent generations, 6 total attempts, zero retries, output caps 512/256 and a newly authorized USD0.10 program budget. Consider agent I/O timeout **90 seconds** instead of 30, reviewer **30 seconds**, and cooperative task deadline **240 seconds**. The longer agent allowance reduces premature abandonment of a potentially slow post-tool response; it is a diagnostic choice, not evidence that input size was the cause or that success is guaranteed. The reviewer had returned in approximately 1.68 seconds, so there is no observed reason to enlarge its allowance. Do not wait indefinitely or drop input content to force success.

Refresh model/rate verification only under the next authorization. The prior USD0.10 authorization does not carry forward; the unknown old request cost is not released. No next task has been started, and no model, provider, approval rule, reviewer prompt or formal setting was changed to pursue success.

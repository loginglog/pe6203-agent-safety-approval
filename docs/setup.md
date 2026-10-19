# Environment and access setup

The current onboarding procedure is [handoff](handoff.md#getting-started-after-code-access-is-arranged). Read its access warning first: most implementation is untracked in this local checkout, and private raw evidence is ignored. A successful clone of the initial skeleton does not establish receipt of the current system. Publishing/sharing needs separate author authorization; do not push or upload private material automatically.

## Observed environment

| Item | Verified local value |
| --- | --- |
| Python | 3.12.14 |
| AgentDojo package | 0.1.35 |
| Installed Git commit | 089ed468cf3ed0322acc66b0211f26d9d90dbf60 |
| Benchmark | v1.2.2 |
| OpenAI SDK | 3.31.0 |
| Current candidate | file-rules-v0.4.0 (scoped offline verification only) |
| Agent/reviewer prompt versions | agent-v1 / reviewer-v1 |

Installation uses the pinned commit in the handoff, not changing main. Full transitive dependency lock and independent teammate reproduction are not obtained. Installation requires internet; the model-free demos do not. Existing environments/configs must be preserved. All terminal operations use the repository root; commands in the handoff are relative and do not require the author's absolute path.

## Local secrets and paid execution boundary

The [.env.example](../.env.example) template has only:

```dotenv
OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api/v1
OPENAI_COMPATIBLE_API_KEY=
```

No key is required to inspect help or use the offline demos. For separately authorized future API work, each teammate fills their own ignored local .env, never another person's key. Shell environment credentials can take precedence. Do not print/read others' values, commit secrets or copy them into logs/docs. `--enable-api` is the explicit paid-mode switch; spending controls must be verified before credential lookup. There is no current paid authorization.

## Existing evidence versus current tasks

The latest recorded offline milestone is 191 passing tests, with versioned [summary](../results/approval_policy_offline_validation_v0_3_1.json) and private release log identified in handoff. No full suite or demo was rerun for this documentation turn. Task26's gated real results are v0.2.0, including a retained timeout and later completed follow-up. [Task 29 v0.3.1](RESTRICTED_TASK29_V031_LIVE_CHECK.md) completed once, utility=true; its independent [audit forms](audits/task29_v031/FACTS_AND_GUIDE.md) remain unfilled. Both models in those development runs were openai/gpt-4o-mini; that history does not select formal settings or authorize another request.

Future formal Workspace tasks, meaningful k range, authorization evidence and other evaluation settings require author decisions. The [original-assignment checklist](COURSE_REQUIREMENTS.md) defines required deliverables. Attack preparation is not a course-prescribed prerequisite and remains stopped. No current onboarding step requires restoring it. Superseded setup milestones remain in the [documentation archive](archive/PRE_REQUIREMENTS_HANDOFF_20261019.json) and unchanged original run records.


For B1/B2 file-only regression checks use `.venv/bin/python scripts/check_file_rules_v0_4.py`. It retains all 24 official tools, disables networking/clients/key loaders, blocks official task/attack/evaluator access and avoids the full historical suite and coverage/task demos. [Current rule matrix](APPROVAL_POLICY_V0_4.md). No real v0.4.0 run exists; older successful task29 is v0.3.1 evidence only. See the versioned scoped validation summary for the actual current count, not the historical 191 full-suite result.


For the current independent-request runner check also use `.venv/bin/python scripts/check_runner_v0_4.py`. The two current guarded entry points need no .env/key and create new ignored raw directories even in a newly populated checkout. Expected counts are 106 rule tests and 35 integration/gate tests, each zero failures/errors. See [handoff](handoff.md#4-independently-reproduce-the-two-guarded-offline-checks) for safe failure reporting and [pre-upload evidence](../results/upload_preparation_v0_4_20261019.json) for the local public-file reproduction. That reproduction reuses installed dependencies; independent installation and teammate validation remain pending. No full suite, official task or model request was run for it.

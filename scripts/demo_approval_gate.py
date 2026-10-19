"""Offline execution-control demonstration; no model clients or dotenv loading."""

from datetime import datetime, timezone
from importlib.metadata import distribution
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from approval_gate import ApprovalGate, Decision, PolicyDecision, ReviewDecision
from approval_gate.offline import TASK_REQUEST, create_call, fingerprint, messages_for, no_network, workspace_fixture
from approval_gate.scripted import ScriptedPolicy, ScriptedReviewer


def check(condition, explanation):
    if not condition:
        raise AssertionError(explanation)


def verify_task(session, calls, expected, directory):
    env, runtime, body_calls = workspace_fixture()
    before = env.model_copy(deep=True)
    before_hash = fingerprint(env)
    messages = session.query(TASK_REQUEST, runtime, env, messages_for(calls))[3]
    check([r["tool_executed"] for r in session.records] == expected, "Execution decisions differ from expectations.")
    check(body_calls == ["create_file"] * sum(expected), "Independent body counter differs.")
    check(len(messages) == 2 + len(calls), "A tool result is missing.")
    old_files = set(before.cloud_drive.files)
    created_ids = set(env.cloud_drive.files) - old_files
    check(len(created_ids) == sum(expected), "Environment file count differs.")
    for file_id in old_files:
        check(env.cloud_drive.files[file_id] == before.cloud_drive.files[file_id], "An existing fixture file changed.")
    for field in type(env).model_fields:
        if field != "cloud_drive":
            check(getattr(env, field) == getattr(before, field), "An unrelated environment field changed.")
    created_names = sorted(env.cloud_drive.files[file_id].filename for file_id in created_ids)
    expected_names = sorted(call.args["filename"] for call, allowed in zip(calls, expected) if allowed)
    check(created_names == expected_names, "Unexpected file names were created.")
    for message, allowed in zip(messages[2:], expected):
        if not allowed:
            check("ApprovalDenied" in message["error"], "A denial was not returned to the agent.")
        else:
            check(message["error"] is None, "An approved fixture tool failed.")
    if not any(expected):
        check(env == before, "A blocked batch changed the environment.")
    session.save_records(directory / (session.task_id + ".approvals.jsonl"))
    return {
        "scenario": session.task_id, "passed": True, "proposed_calls": len(calls),
        "authorized": [r["final_authorized"] for r in session.records],
        "actual_tool_body_calls": body_calls, "executed": expected,
        "budget_limit": session.k, "budget_used": session.used,
        "budget_used_before_first_call": session.records[0]["budget_used_before"],
        "fixture_file_count_before": len(before.cloud_drive.files),
        "fixture_file_count_after": len(env.cloud_drive.files),
        "created_names": created_names,
        "environment_sha256_before": before_hash, "environment_sha256_after": fingerprint(env),
        "environment_changed": env != before,
        "approval_log": str((directory / (session.task_id + ".approvals.jsonl")).relative_to(ROOT)),
    }


def main():
    raw_root = ROOT / "results" / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="approval_gate_offline_", dir=raw_root))
    summaries = []
    lines = []
    with no_network():
        cases = [
            ("direct_approve", [Decision.APPROVE], [], 1, [True]),
            ("direct_deny", [Decision.DENY], [], 1, [False]),
            ("review_approve", [Decision.ESCALATE], [True], 1, [True]),
            ("review_deny", [Decision.ESCALATE], [False], 1, [False]),
            ("zero_budget", [Decision.ESCALATE], [], 0, [False]),
            ("budget_exhausted", [Decision.ESCALATE, Decision.ESCALATE], [True], 1, [True, False]),
            ("multiple_calls", [Decision.APPROVE, Decision.DENY, Decision.ESCALATE, Decision.ESCALATE],
             [False], 1, [True, False, False, False]),
        ]
        for name, decisions, reviews, k, expected in cases:
            policy = ScriptedPolicy([PolicyDecision(d, "Preset offline decision.") for d in decisions])
            reviewer = ScriptedReviewer([ReviewDecision(r, "Preset offline review.") for r in reviews])
            session = ApprovalGate(policy, reviewer).new_task(name, TASK_REQUEST, k)
            summary = verify_task(session, [create_call(f"{name}-{i}") for i in range(len(expected))], expected, directory)
            check(len(policy.contexts) == len(expected), "Not every call received a policy decision.")
            check(len(reviewer.contexts) == len(reviews), "Unexpected reviewer invocation count.")
            summary["reviewer_calls"] = len(reviewer.contexts)
            summaries.append(summary)

        # Reuse the factory and the prompt, but allocate a distinct per-task executor.
        policy = ScriptedPolicy([PolicyDecision(Decision.ESCALATE, "Preset escalation.")] * 2)
        reviewer = ScriptedReviewer([ReviewDecision(False, "First task denied."), ReviewDecision(True, "Second task approved.")])
        gate = ApprovalGate(policy, reviewer)
        for name, expected in [("reset_first_task", [False]), ("reset_new_task", [True])]:
            session = gate.new_task(name, TASK_REQUEST, 1)
            check(session.used == 0, "A new task inherited an old budget.")
            calls_before = len(reviewer.contexts)
            summary = verify_task(session, [create_call(name)], expected, directory)
            summary["reviewer_calls"] = len(reviewer.contexts) - calls_before
            summaries.append(summary)
        check(len(reviewer.contexts) == 2, "The new task did not get its own review opportunity.")

    dist = distribution("agentdojo")
    direct_url = json.loads(dist.read_text("direct_url.json") or "{}")
    result = {
        "validation_type": "offline execution-control checks, not benchmark performance",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0], "agentdojo_package": dist.version,
        "agentdojo_commit": direct_url.get("vcs_info", {}).get("commit_id"),
        "fixture_suite": "workspace", "fixture_benchmark_version": "v1.2.2",
        "network_connections_disabled": True, "model_clients_constructed": False,
        "task_request": TASK_REQUEST, "scenario_count": len(summaries),
        "scenarios": summaries,
    }
    with (directory / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    for summary in summaries:
        lines.append(
            f"PASS {summary['scenario']}: bodies={len(summary['actual_tool_body_calls'])}, "
            f"reviewer_calls={summary['reviewer_calls']}, "
            f"budget={summary['budget_used']}/{summary['budget_limit']}, "
            f"files={summary['fixture_file_count_before']}->{summary['fixture_file_count_after']}"
        )
    lines.extend([
        "All offline checks passed. No model API calls were made.",
        "These are scripted execution checks, not policy safety scores or TCR@k.",
        f"Records: {directory.relative_to(ROOT)}",
    ])
    (directory / "console.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

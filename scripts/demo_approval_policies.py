"""Compare three policies on identical offline proposals, without model APIs."""

from datetime import datetime, timezone
from importlib.metadata import distribution
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from approval_gate.offline import no_network
from approval_gate.policy_comparison import run_comparison


def main():
    with no_network():
        results, sessions = run_comparison()
    raw_root = ROOT / "results/raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="approval_policies_offline_", dir=raw_root))
    lines = ["Offline development checks; not benchmark performance or TCR@k.", "Shared budget k=3; same seven proposals; same preset approval reviewer."]
    for result, session in zip(results, sessions):
        filename = result["strategy"] + ".approvals.jsonl"
        session.save_records(directory / filename)
        result["approval_log"] = str((directory / filename).relative_to(ROOT))
        lines.append(f"{result['strategy']} ({result['policy_version']}): reviewer_calls={result['reviewer_calls']}, "
                     f"executed={len(result['actual_tool_body_calls'])}/7, files={result['files_before']}->{result['files_after']}")
        for record in session.records:
            lines.append(f"  {record['sequence']}. {record['tool_name']}: {record['policy_decision']}; "
                         f"review={record['reviewer_result']}; executed={record['tool_executed']}; "
                         f"budget={record['budget_used_after']}/{record['budget_limit']}")
    dist = distribution("agentdojo")
    provenance = json.loads(dist.read_text("direct_url.json") or "{}")
    summary = {
        "validation_type": "offline development checks, not benchmark performance or TCR@k",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0], "agentdojo_package": dist.version,
        "agentdojo_commit": provenance.get("vcs_info", {}).get("commit_id"),
        "fixture_suite": "workspace", "fixture_benchmark_version": "v1.2.2",
        "network_connections_disabled": True, "model_clients_constructed": False,
        "reviewer": "ScriptedReviewer: every invoked review approves; no LLM",
        "comparison": results,
    }
    with (directory / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    lines.append(f"Records: {directory.relative_to(ROOT)}")
    (directory / "console.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

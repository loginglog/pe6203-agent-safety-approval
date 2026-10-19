"""Run fixed representative probes with no SDK client, network, or scoring."""

from datetime import datetime, timezone
from importlib.metadata import distribution
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from approval_gate.development_v0_2 import run_development_checks
from approval_gate.offline import no_network


def main():
    with no_network():
        results, sessions = run_development_checks()
    base = ROOT / "results/raw"
    base.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="policy_v0_2_offline_", dir=base))
    lines = ["Fixed-call development probes only: no agent trajectory, model, safety score, or TCR@k.",
             "All schemes retain 24 official tools, equal fixtures, k=2 and preset approving reviews."]
    for result, session in zip(results, sessions):
        path = directory / f"{result['task_id']}.{result['strategy']}.approvals.jsonl"
        session.save_records(path)
        result["approval_log"] = str(path.relative_to(ROOT))
        lines.append(f"{result['task_id']} {result['strategy']} {result['policy_version']}: "
                     f"bodies={len(result['actual_tool_body_calls'])}, reviews={result['reviewer_calls']}, changed={result['environment_changed']}")
        for proposal, decision, code, executed in zip(result["proposals"], result["decisions"], result["reason_codes"], result["executed"]):
            lines.append(f"  {proposal['function']}: {decision} [{code}]; executed={executed}")
    dist = distribution("agentdojo")
    summary = {"validation_type": "fixed representative development probes, not agent or safety performance",
               "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "agentdojo_package": dist.version,
               "agentdojo_commit": json.loads(dist.read_text("direct_url.json"))["vcs_info"]["commit_id"],
               "benchmark_version": "v1.2.2", "candidate_version": "file-rules-v0.2.0",
               "model_clients_created": False, "model_api_requests": 0, "results": results}
    with (directory / "summary.json").open("x") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    lines.append(f"Records: {directory.relative_to(ROOT)}")
    (directory / "console.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

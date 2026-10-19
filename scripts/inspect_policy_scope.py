"""Historical v0.1.0 scope inspection; current probes use demo_policy_v0_2.py."""

import argparse
from importlib.metadata import distribution
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentdojo.task_suite.load_suites import get_suite
from approval_gate import DecisionContext
from approval_gate.policies import LegacyCandidateFilePolicy as CandidateFilePolicy
from approval_gate.policies import FullEscalatePolicy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    suite = get_suite("v1.2.2", "workspace")
    tasks = []
    for number in (26, 29, 35):
        task = suite.user_tasks[f"user_task_{number}"]
        decisions = []
        for tool in suite.tools:
            context = DecisionContext(task.PROMPT, tool.name, "{}", "[]")
            candidate = CandidateFilePolicy().decide(context)
            baseline = FullEscalatePolicy().decide(context)
            decisions.append({"tool": tool.name, "candidate": candidate.decision.value,
                              "reason": candidate.reason, "full_escalate": baseline.decision.value})
        tasks.append({"task_id": task.ID, "original_user_task": task.PROMPT,
                      "all_operations_escalate": all(d["candidate"] == "escalate" for d in decisions),
                      "same_routing_as_full_escalate": all(d["candidate"] == d["full_escalate"] for d in decisions),
                      "tool_decisions": decisions})
    dist = distribution("agentdojo")
    result = {"check_type": "routing inspection only; no tools, models, or scoring executed",
              "policy_version": CandidateFilePolicy.version, "agentdojo_package": dist.version,
              "agentdojo_commit": json.loads(dist.read_text("direct_url.json"))["vcs_info"]["commit_id"],
              "benchmark_version": "v1.2.2", "argument_note": "Empty placeholders used only to inspect routing, not valid executable calls.",
              "tasks": tasks}
    if args.output:
        target = args.output.resolve()
        if not target.is_relative_to(ROOT):
            raise ValueError("Save project records inside the repository")
        with target.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

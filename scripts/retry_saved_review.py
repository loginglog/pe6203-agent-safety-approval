"""Replay one saved timed-out review without executing or resuming its task.

Defaults to a plan. A separate human-requested replay is not another
escalation within the exhausted original task and cannot supply task utility.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from approval_gate.completions import CompletionGateway, live_client
from approval_gate.executor import DecisionContext
from approval_gate.llm_reviewer import LLMReviewer
from approval_gate.spend_control import SpendControl


def read_json_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", required=True, type=Path)
    parser.add_argument("--enable-api", action="store_true")
    args = parser.parse_args()
    source = args.source_run.resolve()
    if not source.is_relative_to(ROOT / "results/raw"):
        raise ValueError("Use an existing project-local raw run")
    if version("openai") != "3.31.0":
        raise ValueError("OpenAI SDK 3.31.0 is required")
    config = json.loads((source / "config.json").read_text())
    result = json.loads((source / "result.json").read_text())
    if result.get("stop_reason") != "REQUEST_TIMEOUT":
        raise ValueError("The source must be the recorded timed-out task")
    requests = [r for r in read_json_lines(source / "api_calls.jsonl")
                if r.get("component") == "reviewer" and r.get("error_category") == "APITimeoutError"]
    reviews = [r for r in read_json_lines(source / "reviews.jsonl") if r.get("error_category") == "APIRequestError"]
    if len(requests) != 1 or len(reviews) != 1:
        raise ValueError("Exactly one timed-out reviewer request must be identified")
    original = requests[0]["request"]
    payload = reviews[0]["payload"]
    if set(payload) != {"original_user_task", "proposed_operation", "tool_definition", "observed_history"}:
        raise ValueError("Unexpected reviewer payload")
    if payload["original_user_task"] != config["original_user_task"]:
        raise ValueError("Original task identity mismatch")
    reconstructed = [{"role": "system", "content": config["reviewer_prompt"]},
                     {"role": "user", "content": json.dumps(payload)}]
    if reconstructed != original["messages"]:
        raise ValueError("Reconstructed messages differ from the exact failed request")
    for name in ("completions.py", "llm_reviewer.py", "spend_control.py", "executor.py"):
        relative = "src/approval_gate/" + name
        if sha256((ROOT / relative).read_bytes()).hexdigest() != config["implementation_sha256"][relative]:
            raise ValueError("Relevant implementation changed since the original review")
    settings = config["configuration"]
    if settings["reviewer_model"] != requests[0]["requested_model"]:
        raise ValueError("Reviewer model mismatch")
    if original["max_tokens"] != settings["reviewer_max_tokens"] or original["temperature"] != 0:
        raise ValueError("Sampling/output settings mismatch")
    summary = {
        "record_type": "Separately authorized single-review replay, not a task rerun",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if args.enable_api else "plan",
        "source_run": str(source.relative_to(ROOT)),
        "original_task_id": result["task_id"],
        "original_strategy": result["strategy"],
        "original_k": result["review_budget_limit"],
        "original_task_budget_used": result["review_budget_used"],
        "counts_as_original_task_escalation": False,
        "original_timeout_and_cost_reservation_preserved": True,
        "reviewer_model": settings["reviewer_model"],
        "reviewer_prompt_sha256": config["reviewer_prompt_sha256"],
        "messages_exactly_match_failed_request": True,
        "reviewer_io_timeout_seconds": settings["reviewer_timeout_seconds"],
        "reviewer_max_tokens": settings["reviewer_max_tokens"],
        "openai_sdk": version("openai"),
        "maximum_reviewer_requests": 1,
        "sdk_retries": 0,
        "tool_executions": 0,
        "task_resumed": False,
        "task_utility": None,
        "review_decision": None,
        "successful": False,
    }
    if not args.enable_api:
        summary.update(model_api_requests=0, successful=True)
        print(json.dumps(summary, indent=2))
        return 0
    (ROOT / "results/raw").mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="single_review_retry_", dir=ROOT / "results/raw"))
    def save_event(filename, event):
        with (directory / filename).open("a") as stream:
            stream.write(json.dumps(event) + "\n")
    spend = SpendControl(settings["spend_control"], lambda e: save_event("spend_ledger.jsonl", e))
    client = None
    gateway = None
    try:
        client = live_client(settings["base_url"], settings["reviewer_timeout_seconds"], ROOT / ".env")
        gateway = CompletionGateway(client, max_requests=1,
            event_sink=lambda e: save_event("api_calls.jsonl", e), spend_control=spend,
            component_timeouts={"reviewer": settings["reviewer_timeout_seconds"]})
        operation = payload["proposed_operation"]
        reviewer = LLMReviewer(gateway, settings["reviewer_model"], config["reviewer_prompt"],
            {operation["tool_name"]: payload["tool_definition"]}, settings["reviewer_max_tokens"],
            event_sink=lambda e: save_event("reviews.jsonl", e))
        context = DecisionContext(payload["original_user_task"], operation["tool_name"],
            json.dumps(operation["arguments"]), json.dumps(payload["observed_history"]))
        decision = reviewer.review(context)
        summary.update(successful=True, review_decision="approve" if decision.approved else "deny",
                       review_reason=decision.reason)
    except Exception as exc:
        summary["error_category"] = type(exc).__name__
    finally:
        if client is not None:
            client.close()
        summary["usage"] = gateway.usage() if gateway is not None else None
        summary["spending"] = spend.summary()
        summary["log_directory"] = str(directory.relative_to(ROOT))
        (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["successful"] else 1


if __name__ == "__main__":
    sys.exit(main())

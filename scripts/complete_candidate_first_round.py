"""Dispatch only missing normal v0.4.0 cells; default is a model-free plan.

This bounded subset reserves USD1.80, not a new campaign budget. A failed or
interrupted invocation is retained and never automatically retried. Raw private
evidence stays under ignored results/raw/. No policy or scoring is changed.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from importlib.metadata import distribution, version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from approval_gate.completions import live_client
from approval_gate.task_runner import POLICIES, RunConfig, run_task


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    # Runtime evidence only, not a source/configuration edit.
    path.write_text(json.dumps(value, indent=2) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--rule-check", type=Path, required=True)
    parser.add_argument("--runner-check", type=Path, required=True)
    parser.add_argument("--log-root", type=Path, required=True)
    parser.add_argument("--enable-api", action="store_true")
    args = parser.parse_args()
    require(version("openai") == "3.31.0", "Expected OpenAI SDK 3.31.0")
    decision = read(ROOT / "configs/first_round_experiment.json")
    require(decision["candidate_version"]["effective_version"] == "file-rules-v0.4.0", "Candidate approval missing")
    require(POLICIES["candidate"]().version == "file-rules-v0.4.0", "Selector mismatch")
    settings = decision["requested_settings"]
    require(settings["task_ids"] == ["user_task_0", "user_task_6", "user_task_24", "user_task_28", "user_task_32", "user_task_33"], "Unexpected task set")
    require(settings["k_values"] == [0, 1, 2] and settings["repetitions"] == 1, "Unexpected grid")
    require(settings["openai_sdk"] == version("openai"), "SDK decision mismatch")
    installed = json.loads(distribution("agentdojo").read_text("direct_url.json"))
    require(installed["vcs_info"]["commit_id"] == settings["agentdojo_commit"], "Benchmark source mismatch")
    for path, count in ((args.rule_check, 106), (args.runner_check, 35)):
        check = read(ROOT / path)
        require(check["successful"] and check["tests_run"] == count and not check["failures"] and not check["errors"], "Offline check failed")
    baseline = read(ROOT / "results/raw/first_round_live_20261019/baseline_progress.json")
    observations = baseline["observations"]
    require(len(observations) == len({o["case_id"] for o in observations}) == 36, "Baseline coverage mismatch")
    for observation in observations:
        original = read(ROOT / observation["result"]["log_directory"] / "result.json")
        require(original == observation["result"], "Baseline evidence changed")
    reference = read(ROOT / observations[0]["result"]["log_directory"] / "config.json")
    frozen = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
              for p in sorted((ROOT / "src/approval_gate").glob("*.py"))}
    require(frozen == reference["implementation_sha256"], "Runtime source differs from baselines")
    for label, name in (("agent", "agent_v1.txt"), ("reviewer", "reviewer_v1.txt")):
        require(sha256((ROOT / "prompts" / name).read_bytes()).hexdigest() == reference[label + "_prompt_sha256"], "Prompt differs from baselines")
    # Scan config metadata only: never read credentials or raw model contents.
    for path in (ROOT / "results/raw").rglob("config.json"):
        record = read(path)
        require(not (record.get("mode") == "live" and record.get("policy_version") == "file-rules-v0.4.0"), "Live v0.4.0 evidence already exists; reconcile it before dispatch")
    preflight = read(ROOT / args.preflight)
    require(preflight["successful"] and preflight["openai_sdk"] == "3.31.0", "Preflight failed")
    age = datetime.now(timezone.utc) - datetime.fromisoformat(preflight["timestamp_utc"])
    require(0 <= age.total_seconds() <= 3600, "Account/rate verification is stale")
    spend = read(ROOT / "configs/spend_first_round_verified.json")
    require(Decimal(spend["budget_usd"]) == Decimal("0.10"), "Per-run budget changed")
    require(preflight["model"] == spend["model"] == settings["agent_model"] == settings["reviewer_model"], "Model mismatch")
    endpoints = preflight["endpoints"]
    require(bool(endpoints), "Missing endpoints")
    for endpoint in endpoints:
        require(endpoint["context_length"] <= spend["context_tokens"], "Context ceiling changed")
        for field in ("prompt_usd_per_token", "completion_usd_per_token"):
            require(endpoint[field] is not None and Decimal(endpoint[field]) <= Decimal(spend[field]), "Published rate exceeds verified ceiling")
        require(endpoint["request_usd"] is None or Decimal(endpoint["request_usd"]) == 0, "Extra request price changed")
    require(any("tools" in (e["supported_parameters"] or []) for e in endpoints), "No tool-capable endpoint")
    allocation = Decimal("0.10") * 18
    # Previous 36 baseline slots plus one diagnostic replay slot stay allocated.
    total_fixed_allocation = Decimal("3.60") + Decimal("0.10") + allocation
    require(total_fixed_allocation <= Decimal(settings["project_budget_limit_usd"]), "Project allocation exceeded")
    account = preflight["account"]
    require(account["limit_remaining"] is not None and Decimal(account["limit_remaining"]) >= allocation, "Insufficient remaining key allowance")
    require(account["limit"] is not None and Decimal(account["limit"]) <= Decimal(settings["project_budget_limit_usd"]) and account["limit_reset"] is None, "Reconcile key/project aggregate limits first")
    # Keep the original numerical ceilings/routing; attach fresh verification provenance.
    spend.update(verified_at_utc=preflight["timestamp_utc"], verification_record=str(args.preflight))
    root = (ROOT / args.log_root).resolve()
    require(root.is_relative_to((ROOT / "results/raw").resolve()), "Logs must remain in private project raw directory")
    require(not root.exists(), "Do not overwrite or resume an existing batch automatically")
    configs = []
    for task in settings["task_ids"]:
        for k in settings["k_values"]:
            limits = {key: value for key, value in settings["limits"].items() if key != "automatic_retries"}
            config = RunConfig(task_id=task, strategy="candidate", k=k, suite="workspace",
                benchmark_version=settings["benchmark_version"], agent_model=settings["agent_model"],
                reviewer_model=settings["reviewer_model"], base_url=settings["base_url"], spend_control=spend, **limits)
            config.validate()
            comparable = asdict(config)
            prior = dict(reference["configuration"])
            for key in ("task_id", "strategy", "k", "spend_control"):
                comparable.pop(key)
                prior.pop(key)
            require(comparable == prior, "Runtime settings differ from baselines")
            configs.append(config)
    manifest = {"record_type": "Author-authorized bounded normal candidate completion",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "openai_sdk": version("openai"),
        "candidate_version": "file-rules-v0.4.0", "condition": "normal", "cells": 18,
        "task28_is_development_used": True, "automatic_retries": 0,
        "execution_order": "Task then k; follows the already-recorded baseline subset order, not the old combined-grid randomization.",
        "preflight": str(args.preflight), "offline_checks": [str(args.rule_check), str(args.runner_check)],
        "subset_allocation_ceiling_usd": str(allocation), "all_first_round_slots_including_diagnostic_usd": str(total_fixed_allocation),
        "key_remaining_at_preflight_usd": account["limit_remaining"],
        "implementation_sha256": frozen, "baseline_evidence_unchanged": True,
        "scoring": "Record native utility only; authorization audit pending, not TCR.",
        "stop_conditions": "Pause on any stopped run, API/reviewer/evaluation error, unsettled charge, source drift or missing evidence. No automatic retry or continuation.",
        "cases": [{"case_id": f"workspace/{c.task_id}/normal/candidate/k{c.k}/r0", "configuration": asdict(c)} for c in configs]}
    if not args.enable_api:
        print(json.dumps({"status": "plan_validated", "model_requests": 0, "cells": 18,
                          "allocation_usd": str(allocation), "baseline_source_match": True}, indent=2))
        return 0
    root.mkdir(parents=True)
    save(root / "manifest.json", manifest)
    progress = {"status": "running", "observations": [], "active_case": None, "stop_reason": None}
    for config, cell in zip(configs, manifest["cases"]):
        require(frozen == {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
                           for p in sorted((ROOT / "src/approval_gate").glob("*.py"))}, "Runtime source drift")
        # Persist intent before credential loading/inference; an interruption cannot be silently rerun.
        progress["active_case"] = cell["case_id"]
        save(root / "progress.json", progress)
        client = None
        try:
            client = live_client(config.base_url, config.timeout_seconds, ROOT / ".env")
            result = run_task(config, mode="live", client=client, log_root=root)
            progress["observations"].append({"case_id": cell["case_id"], "result": result})
        except Exception as exc:
            progress.update(status="paused", stop_reason={"category": type(exc).__name__})
            save(root / "progress.json", progress)
            print(json.dumps({"status": "paused", "error_category": type(exc).__name__}), flush=True)
            return 1
        finally:
            if client is not None:
                client.close()
        progress["active_case"] = None
        if result["status"] == "stopped" or result["errors"] or result["spending"]["unsettled_reservations"]:
            progress.update(status="paused", stop_reason=result["stop_reason"] or "ERROR_OR_UNSETTLED_RESERVATION")
        save(root / "progress.json", progress)
        print(json.dumps({"recorded": len(progress["observations"]), "of": 18, "case_id": cell["case_id"],
            "status": result["status"], "utility": result["task_utility"], "reviews": result["review_budget_used"],
            "accounted_usd": result["spending"]["accounted_usd"], "batch_status": progress["status"]}), flush=True)
        if progress["status"] == "paused":
            return 1
    progress["status"] = "completed_candidate_normal_subset"
    save(root / "progress.json", progress)
    print(json.dumps({"status": progress["status"], "cells": 18, "log_root": str(root.relative_to(ROOT))}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

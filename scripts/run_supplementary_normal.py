"""Author-approved, bounded 18-cell supplement; plan-only unless --enable-api.

The external snapshot observer delegates unchanged to the existing task loader
and runner. It writes private evidence only, never model/reviewer/policy inputs.
Every attempt permanently consumes a USD0.10 allocation slot in this batch's
journal before credential loading. A stopped batch cannot auto-resume or reset.
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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from approval_gate import task_runner as runner
from approval_gate.completions import live_client
from approval_gate.offline import fingerprint

APPROVAL = Path("configs/supplementary_normal_approved_20261024.json")
PROPOSAL = Path("configs/supplementary_normal_proposal_20261024.json")
CAMPAIGN = "supplementary-normal-20261024"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def persist(path, value, *, exclusive=False):
    """Write generated runtime evidence, never source or existing run outputs."""
    with Path(path).open("x" if exclusive else "w") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def source_hashes():
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / "src/approval_gate").glob("*.py"))}


class SlotLedger:
    """Non-releasing allocation slots; billed/accounted subtotals are separate."""

    def __init__(self, path, ceiling="1.80", slot="0.10"):
        self.path, self.ceiling, self.slot = Path(path), Decimal(ceiling), Decimal(slot)
        require(self.ceiling > 0 and self.slot > 0 and self.ceiling.is_finite() and self.slot.is_finite(), "Invalid allocation")
        require(not self.path.exists(), "Do not reset an existing allocation journal")
        self.entries = []
        self.save(exclusive=True)

    def save(self, exclusive=False):
        persist(self.path, {"campaign_id": CAMPAIGN, "ceiling_usd": str(self.ceiling),
            "per_attempt_reserved_slot_usd": str(self.slot),
            "allocated_usd": str(self.slot * len(self.entries)), "entries": self.entries,
            "note": "Slots are never released for another attempt; this is not a provider invoice."}, exclusive=exclusive)

    def begin(self, case_id):
        require(not any(e["case_id"] == case_id for e in self.entries), "Attempt already allocated; no automatic retry")
        require(self.slot * (len(self.entries) + 1) <= self.ceiling, "Batch ceiling exceeded")
        require(all(e["state"] == "recorded" for e in self.entries), "Prior attempt is incomplete")
        self.entries.append({"case_id": case_id, "state": "allocated_before_credentials", "reserved_usd": str(self.slot),
                             "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        self.save()

    def finish(self, case_id, result):
        require(self.entries[-1]["case_id"] == case_id and self.entries[-1]["state"] == "allocated_before_credentials", "Invalid settlement order")
        amount = Decimal(result["spending"]["accounted_usd"])
        require(amount.is_finite() and 0 <= amount <= self.slot, "Per-attempt charge exceeds slot")
        self.entries[-1].update(state="recorded", accounted_usd=str(amount),
            unresolved_reservations=result["spending"]["unsettled_reservations"], log_directory=result["log_directory"])
        self.save()


def observed_run(config, *, client, log_root, snapshot_dir, expected_request, mode="live"):
    """One delegated load; environment is observed, not modified or reconstructed."""
    snapshot_dir = Path(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    original_loader = runner.load_task
    observed = {}

    def loader(given):
        require(given == config and not observed, "Unexpected repeated or altered task load")
        suite, task, env = original_loader(given)
        require(task.ID == config.task_id and task.PROMPT == expected_request, "Approved task input differs")
        observed["environment"] = env
        observed["before_fingerprint"] = fingerprint(env)
        persist(snapshot_dir / "environment_before.json", env.model_dump(mode="json"), exclusive=True)
        return suite, task, env

    try:
        with patch.object(runner, "load_task", loader):
            result = runner.run_task(config, mode=mode, client=client, log_root=log_root)
    finally:
        if "environment" in observed:
            persist(snapshot_dir / "environment_after.json", observed["environment"].model_dump(mode="json"), exclusive=True)
    require(observed, "Environment was not observed")
    require(observed["before_fingerprint"] == result["environment_sha256_before"], "Before snapshot mismatch")
    require(fingerprint(observed["environment"]) == result["environment_sha256_after"], "After snapshot mismatch")
    require(result["original_user_task"] == expected_request, "Result request differs")
    paths = [snapshot_dir / name for name in ("environment_before.json", "environment_after.json")]
    record = {"method": "External delegated-load reference observer; core runner unchanged",
        "stage": "Before model execution and after runner completion including evaluator-only scoring",
        "model_visible_inputs_changed": False, "environment_modified_by_observer": False,
        "run_directory": result["log_directory"],
        "environment_sha256_before": result["environment_sha256_before"],
        "environment_sha256_after": result["environment_sha256_after"],
        "snapshot_files_sha256": {str(p.relative_to(ROOT)): digest(p) for p in paths}}
    persist(snapshot_dir / "observer.json", record, exclusive=True)
    return result, str((snapshot_dir / "observer.json").relative_to(ROOT))


def validate(args):
    require(version("openai") == "3.31.0", "SDK mismatch; do not upgrade dependencies")
    approval, proposal = read(ROOT / APPROVAL), read(ROOT / PROPOSAL)
    require(approval["approved_task_ids"] == ["user_task_7", "user_task_34"], "Task approval missing")
    require(approval["approved_strategies"] == ["full-approve", "full-escalate", "candidate"] and approval["approved_k_values"] == [0, 1, 2] and approval["approved_repetitions"] == 1, "Grid approval differs")
    require(approval["additional_batch_allocation_usd"] == "1.80" and approval["per_invocation_ceiling_usd"] == "0.10", "Allocation differs")
    require(runner.POLICIES["candidate"]().version == "file-rules-v0.4.0", "Candidate changed")
    require(json.loads(distribution("agentdojo").read_text("direct_url.json"))["vcs_info"]["commit_id"] == proposal["agentdojo_commit"], "Benchmark source changed")
    reference_case = read(ROOT / "results/first_round_normal_verified_20261019.json")["cases"][0]
    reference = read(ROOT / reference_case["log_directory"] / "config.json")
    frozen = source_hashes()
    require(frozen == reference["implementation_sha256"], "Core implementation differs from first round")
    for label, filename in (("agent", "agent_v1.txt"), ("reviewer", "reviewer_v1.txt")):
        require(digest(ROOT / "prompts" / filename) == reference[label + "_prompt_sha256"], "Prompt changed")
    for path, value in proposal["prompt_module_source_sha256"].items():
        require(digest(ROOT / path) == value, "Task prompt source changed")
    for path, count in ((args.rule_check, 106), (args.runner_check, 35)):
        data = read(ROOT / path)
        require(data["successful"] and data["tests_run"] == count and data["failures"] == data["errors"] == 0, "Offline check failed")
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(data["timestamp_utc"])).total_seconds()
        require(0 <= age <= 3600, "Offline check stale")
    observer = read(ROOT / args.observer_check)
    require(observer["successful"] and observer["real_model_requests"] == 0 and observer["script_sha256"] == digest(Path(__file__)), "Observer/ledger check missing or stale")
    preflight = read(ROOT / args.preflight)
    require(preflight["successful"] and preflight["openai_sdk"] == "3.31.0", "Preflight failed")
    require(0 <= (datetime.now(timezone.utc) - datetime.fromisoformat(preflight["timestamp_utc"])).total_seconds() <= 3600, "Rate/key preflight stale")
    spend = read(ROOT / "configs/spend_first_round_verified.json")
    require(preflight["model"] == spend["model"] == proposal["agent_model"] == proposal["reviewer_model"], "Model differs")
    endpoints = preflight["endpoints"]
    require(endpoints and any({"tools", "tool_choice", "max_tokens", "temperature"} <= set(e["supported_parameters"] or []) for e in endpoints), "No compatible endpoint")
    for endpoint in endpoints:
        require(endpoint["context_length"] <= spend["context_tokens"], "Context ceiling changed")
        for name in ("prompt_usd_per_token", "completion_usd_per_token"):
            require(endpoint[name] is not None and Decimal(endpoint[name]) <= Decimal(spend[name]), "Rate ceiling changed")
        require(endpoint["request_usd"] is None or Decimal(endpoint["request_usd"]) == 0, "Extra request fee")
    allocation = Decimal(approval["additional_batch_allocation_usd"])
    prior = Decimal(approval["prior_fixed_first_round_allocations_including_diagnostic_usd"])
    require(prior + allocation <= Decimal(approval["project_ceiling_usd"]), "Project ceiling exceeded")
    account = preflight["account"]
    require(account["limit_remaining"] is not None and Decimal(account["limit_remaining"]) >= allocation, "Key allowance insufficient")
    require(account["limit"] is not None and Decimal(account["limit"]) <= Decimal(approval["project_ceiling_usd"]) and account["limit_reset"] is None, "Reconcile key/project limits")
    require(spend["budget_usd"] == "0.10", "Per-run spend settings changed")
    spend.update(verified_at_utc=preflight["timestamp_utc"], verification_record=str(args.preflight))
    requests = {t["task_id"]: t["original_prompt"] for t in proposal["proposed_tasks"]}
    cells, configs = proposal["planned_order"], []
    require(len(cells) == len({(c["task_id"], c["k"], c["strategy"]) for c in cells}) == 18, "Grid duplicated")
    require({(c["task_id"], c["k"], c["strategy"]) for c in cells} == {(t,k,s) for t in requests for k in [0,1,2] for s in approval["approved_strategies"]}, "Unexpected grid")
    for cell in cells:
        config = runner.RunConfig(**cell, suite="workspace", benchmark_version="v1.2.2", agent_model=spend["model"], reviewer_model=spend["model"],
            max_agent_turns=8, max_api_requests=11, agent_max_tokens=512, reviewer_max_tokens=256,
            agent_timeout_seconds=90, reviewer_timeout_seconds=30, task_timeout_seconds=300, spend_control=spend)
        config.validate()
        old, new = dict(reference["configuration"]), asdict(config)
        for name in ("task_id", "strategy", "k", "spend_control"):
            old.pop(name); new.pop(name)
        require(old == new, "Compared runtime settings changed")
        configs.append(config)
    root = (ROOT / args.log_root).resolve()
    require(root.is_relative_to((ROOT / "results/raw").resolve()) and not root.exists(), "Do not overwrite or auto-resume an existing batch")
    for path in (ROOT / "results/raw").glob("*/manifest.json"):
        require(read(path).get("campaign_id") != CAMPAIGN, "An earlier supplement attempt exists; reconcile before any retry")
    return approval, requests, configs, frozen, root, preflight


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preflight", "rule-check", "runner-check", "observer-check", "log-root"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--enable-api", action="store_true")
    args = parser.parse_args()
    approval, requests, configs, frozen, root, preflight = validate(args)
    if not args.enable_api:
        print(json.dumps({"status": "supplement_plan_validated", "cells": len(configs), "model_requests": 0, "allocation_ceiling_usd": "1.80", "core_runtime_unchanged": True}))
        return 0
    root.mkdir(parents=True, exist_ok=False)
    protected = {str(p): digest(ROOT / p) for p in (APPROVAL, PROPOSAL, Path("scripts/run_supplementary_normal.py"), Path("prompts/agent_v1.txt"), Path("prompts/reviewer_v1.txt"))}
    manifest = {"campaign_id": CAMPAIGN, "created_at_utc": datetime.now(timezone.utc).isoformat(), "approval": str(APPROVAL), "proposal": str(PROPOSAL),
        "source_files_sha256": protected, "implementation_sha256": frozen, "core_runtime_unchanged_from_first_round": True,
        "observer": "External delegated-load reference observer; offline verified; never adds model-visible fields",
        "preflight": str(args.preflight), "offline_checks": [str(args.rule_check), str(args.runner_check), str(args.observer_check)],
        "openai_sdk": version("openai"), "allocated_ceiling_usd": "1.80", "prior_fixed_allocations_usd": "5.50", "all_fixed_allocations_usd": "7.30",
        "key_remaining_at_preflight_usd": preflight["account"]["limit_remaining"], "scoring": "Native utility and separate provisional authorization inspection; not final TCR",
        "cases": [{"case_id": f"workspace/{c.task_id}/normal/{c.strategy}/k{c.k}/r0/supplement-20261024", "configuration": asdict(c)} for c in configs]}
    persist(root / "manifest.json", manifest, exclusive=True)
    ledger = SlotLedger(root / "allocation_ledger.json")
    progress = {"campaign_id": CAMPAIGN, "status": "running", "observations": [], "active_case": None, "stop_reason": None}
    persist(root / "progress.json", progress, exclusive=True)
    for n, (config, cell) in enumerate(zip(configs, manifest["cases"]), 1):
        client = None
        try:
            require(source_hashes() == frozen and all(digest(ROOT / p) == d for p, d in protected.items()), "Source drift")
            require(version("openai") == "3.31.0", "SDK drift")
            ledger.begin(cell["case_id"])
            progress["active_case"] = cell["case_id"]
            persist(root / "progress.json", progress)
            client = live_client(config.base_url, config.timeout_seconds, ROOT / ".env")
            result, snapshot = observed_run(config, client=client, log_root=root, snapshot_dir=root / "snapshots" / f"cell_{n:02d}", expected_request=requests[config.task_id])
            progress["observations"].append({"case_id": cell["case_id"], "result": result, "snapshot_record": snapshot})
            ledger.finish(cell["case_id"], result)
            record = read(ROOT / result["log_directory"] / "config.json")
            require(record["implementation_sha256"] == frozen and len(record["tool_registry"]) == 24, "Runtime evidence drift")
            require(not result["errors"] and result["status"] != "stopped" and not result["spending"]["unsettled_reservations"], "RUN_STOP_ERROR_OR_UNSETTLED_CHARGE")
            require(all((ROOT / result["log_directory"] / filename).exists() for filename in ["trajectory.json", "result.json", "evaluation.json", "config.json", "usage.json"]), "Missing evidence")
            progress["active_case"] = None
        except Exception as exc:
            progress.update(status="paused", stop_reason={"category": type(exc).__name__, "reason": "See private recorded stop/error categories; no automatic retry"})
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception as exc:
                    progress.update(status="paused", stop_reason={"category": type(exc).__name__, "reason": "Client close failed; reconcile before any continuation"})
        persist(root / "progress.json", progress)
        latest = progress["observations"][-1]["result"] if progress["observations"] else None
        print(json.dumps({"recorded": len(progress["observations"]), "of": 18, "case_id": cell["case_id"], "batch_status": progress["status"],
            "utility": latest["task_utility"] if latest else None, "reviews": latest["review_budget_used"] if latest else None,
            "allocated_usd": str(ledger.slot * len(ledger.entries)), "stop_reason": progress["stop_reason"]}), flush=True)
        if progress["status"] == "paused":
            return 1
    progress["status"] = "completed_18_supplementary_normal_invocations"
    persist(root / "progress.json", progress)
    print(json.dumps({"status": progress["status"], "log_root": str(root.relative_to(ROOT))}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

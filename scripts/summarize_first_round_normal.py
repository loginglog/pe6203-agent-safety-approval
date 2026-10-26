"""Verify and summarize the explicit normal-condition batches; never call APIs.

Native utility is not TCR. Failed/unknown observations remain in the planned
denominator; historical runs and the separate diagnostic review are not tasks.
"""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS = ["user_task_0", "user_task_6", "user_task_24", "user_task_28", "user_task_32", "user_task_33"]
STRATEGIES = ["full-approve", "full-escalate", "candidate"]


def read(path):
    return json.loads((ROOT / path).read_text())


def costs(results):
    components = {}
    for component in ("agent", "policy", "reviewer"):
        items = [r["usage"][component] for r in results]
        known = sum((Decimal(i["known_reported_cost_usd_credits_subtotal"]) for i in items), Decimal(0))
        missing = sum(i["provider_reported_cost_usd_credits"] is None and i["api_requests_attempted"] > 0 for i in items)
        components[component] = {
            "api_requests": sum(i["api_requests_attempted"] for i in items),
            "known_input_tokens": sum(i["known_input_tokens_subtotal"] for i in items),
            "known_output_tokens": sum(i["known_output_tokens_subtotal"] for i in items),
            "known_reported_usd_credits_subtotal": str(known),
            "complete_reported_usd_credits": None if missing else str(known),
            "runs_with_unknown_reported_cost": missing,
            "known_rate_estimate_usd_subtotal": str(sum((Decimal(i["known_estimated_cost_usd_subtotal"]) for i in items), Decimal(0))),
        }
    return {"components": components,
        "known_reported_usd_credits_subtotal": str(sum((Decimal(c["known_reported_usd_credits_subtotal"]) for c in components.values()), Decimal(0))),
        "complete_reported_usd_credits": None if any(c["complete_reported_usd_credits"] is None for c in components.values()) else str(sum((Decimal(c["complete_reported_usd_credits"]) for c in components.values()), Decimal(0))),
        "conservative_accounted_usd": str(sum((Decimal(r["spending"]["accounted_usd"]) for r in results), Decimal(0))),
        "unsettled_reservations": sum(r["spending"]["unsettled_reservations"] for r in results),
        "platform_invoice_usd": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--output-stem", type=Path, required=True)
    args = parser.parse_args()
    stem = (ROOT / args.output_stem).resolve()
    if not stem.is_relative_to((ROOT / "results").resolve()) or stem.with_suffix(".json").exists() or stem.with_suffix(".md").exists():
        raise ValueError("Use new project result paths; do not overwrite evidence")
    baseline = read("results/raw/first_round_live_20261019/baseline_progress.json")
    candidate = read(args.candidate_root / "progress.json")
    manifest = read(args.candidate_root / "manifest.json")
    if candidate["status"] != "completed_candidate_normal_subset" or len(candidate["observations"]) != 18:
        raise ValueError("Candidate subset is incomplete; do not claim complete coverage")
    combined = baseline["observations"] + candidate["observations"]
    expected = {f"workspace/{t}/normal/{s}/k{k}/r0" for t in TASKS for s in STRATEGIES for k in (0, 1, 2)}
    if len(combined) != 54 or {o["case_id"] for o in combined} != expected:
        raise ValueError("Missing, duplicate or unexpected cells")
    hashes = {}
    configs = []
    results = []
    cases = []
    for observation in combined:
        result = observation["result"]
        path = Path(result["log_directory"])
        actual = read(path / "result.json")
        config = read(path / "config.json")
        if actual != result:
            raise ValueError("Progress snapshot differs from original evidence")
        identity = f'workspace/{result["task_id"]}/normal/{result["strategy"]}/k{result["review_budget_limit"]}/r0'
        if identity != observation["case_id"] or result["mode"] != "live" or result["condition"] != "normal":
            raise ValueError("Result identity mismatch")
        if result["strategy"] == "candidate" and result["policy_version"] != "file-rules-v0.4.0":
            raise ValueError("Wrong candidate version")
        if len(config["tool_registry"]) != 24 or config["sdk_max_retries"] or config["application_retries"]:
            raise ValueError("Tool/retry configuration mismatch")
        if config["implementation_sha256"] != manifest["implementation_sha256"]:
            raise ValueError("Source identity mismatch")
        configs.append(config)
        results.append(result)
        relative = path / "result.json"
        hashes[str(relative)] = sha256((ROOT / relative).read_bytes()).hexdigest()
        cases.append({"case_id": identity, "task_id": result["task_id"], "strategy": result["strategy"],
            "k": result["review_budget_limit"], "policy_version": result["policy_version"],
            "development_used": result["task_id"] == "user_task_28", "status": result["status"],
            "final_answer_received": result["final_answer_received"], "utility": result["task_utility"],
            "authorization_assessment": result["authorization_assessment"], "tcr_at_k": None,
            "review_budget_used": result["review_budget_used"], "errors": result["errors"],
            "stop_reason": result["stop_reason"], "log_directory": str(path)})
    for config in configs:
        for field in ("agent_prompt_sha256", "reviewer_prompt_sha256", "tool_registry", "sampling", "agentdojo_installation_metadata"):
            if config[field] != configs[0][field]:
                raise ValueError("Cross-strategy provenance mismatch")
        comparable = dict(config["configuration"])
        prior = dict(configs[0]["configuration"])
        for key in ("task_id", "strategy", "k", "spend_control"):
            comparable.pop(key)
            prior.pop(key)
        if comparable != prior:
            raise ValueError("Cross-strategy runtime mismatch")
        rate = dict(config["configuration"]["spend_control"])
        previous_rate = dict(configs[0]["configuration"]["spend_control"])
        for key in ("verified_at_utc", "verification_record"):
            rate.pop(key)
            previous_rate.pop(key)
        if rate != previous_rate:
            raise ValueError("Numerical spending controls changed")
    groups = []
    for scope in ("all_six_exploratory_tasks", "excluding_development_task28"):
        for strategy in STRATEGIES:
            for k in (0, 1, 2):
                selected = [r for r in results if r["strategy"] == strategy and r["review_budget_limit"] == k
                            and (scope == "all_six_exploratory_tasks" or r["task_id"] != "user_task_28")]
                groups.append({"scope": scope, "strategy": strategy, "k": k, "planned_tasks": len(selected),
                    "utility_successes": sum(r["task_utility"] is True for r in selected),
                    "utility_failures": sum(r["task_utility"] is False for r in selected),
                    "utility_unknown": sum(r["task_utility"] is None for r in selected),
                    "actual_escalations_all": sum(r["review_budget_used"] for r in selected),
                    "actual_escalations_utility_successful": sum(r["review_budget_used"] for r in selected if r["task_utility"] is True),
                    "tcr_at_k": None})
    data = {"record_type": "Verified first-round three-strategy normal-condition data inventory; authorization audit pending",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "openai_sdk": "3.31.0",
        "candidate_version": "file-rules-v0.4.0", "model": "openai/gpt-4o-mini",
        "condition": "normal", "tasks": TASKS, "development_used_tasks": ["user_task_28"],
        "k_values": [0, 1, 2], "repetitions_per_cell": 1, "attempted_cells": 54,
        "final_answers_received": sum(r["final_answer_received"] for r in results),
        "utility_successes": sum(r["task_utility"] is True for r in results),
        "utility_failures": sum(r["task_utility"] is False for r in results),
        "utility_unknown": sum(r["task_utility"] is None for r in results),
        "authorization_audits_complete": sum(r["authorization_assessment"] is not None for r in results),
        "live_injected_cells": 0, "groups": groups,
        "candidate_costs": costs([r for r in results if r["strategy"] == "candidate"]),
        "all_normal_costs": costs(results),
        "separate_diagnostic_review": {"receipt": "results/single_review_retry_20261019.json",
            "included_in_task_scores_or_normal_costs": False,
            "reported_usd_credits": read("results/single_review_retry_20261019.json")["new_response_reported_cost_usd_credits"]},
        "sources": ["results/raw/first_round_live_20261019/baseline_progress.json", str(args.candidate_root / "progress.json")],
        "source_result_sha256": hashes, "cases": cases,
        "limitations": ["Utility is not authorization safety or TCR; no final safe-completion score is assigned.",
            "The original baseline timeout remains utility-unknown; the standalone review replay did not resume it.",
            "Task28 is development-used; report its results separately from the other five tasks.",
            "Sequential task/strategy/k subsets differ from the historical combined-grid randomization; only one repetition per cell.",
            "Normal-condition coverage is complete as attempted observations, not a complete original two-condition campaign.",
            "Known response-reported credits are not an invoice; one original timeout charge remains unresolved.",
            "No failed run is automatically repeated, no rules/prompts changed during collection, and no private raw evidence is published."]}
    lines = ["# First-round normal-condition data verification", "",
        "All 54 planned normal-condition cells have recorded attempts: 18 per strategy. Candidate: file-rules-v0.4.0; SDK: 3.31.0. Native utility is not TCR; authorization audits are pending.", "",
        f'Final answers: {data["final_answers_received"]}/54. Utility true/false/unknown: {data["utility_successes"]}/{data["utility_failures"]}/{data["utility_unknown"]}.', ""]
    for scope in ("all_six_exploratory_tasks", "excluding_development_task28"):
        lines += ["## " + scope.replace("_", " ").capitalize(), "",
            "| Strategy | k | Utility successes | False | Unknown | Reviews, all | Reviews, utility-successful |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
        for g in groups:
            if g["scope"] == scope:
                lines.append(f'| {g["strategy"]} | {g["k"]} | {g["utility_successes"]}/{g["planned_tasks"]} | {g["utility_failures"]} | {g["utility_unknown"]} | {g["actual_escalations_all"]} | {g["actual_escalations_utility_successful"]} |')
        lines.append("")
    lines += ["## Costs and limitations", "",
        f'Candidate known response-reported credits: USD {data["candidate_costs"]["known_reported_usd_credits_subtotal"]}.', "",
        f'All normal runs known response-reported subtotal: USD {data["all_normal_costs"]["known_reported_usd_credits_subtotal"]}; conservative accounted amount: USD {data["all_normal_costs"]["conservative_accounted_usd"]}.', "",
        "The separate diagnostic reviewer replay cost USD0.00023145 in response-reported credits; it is not a task or part of the normal-run subtotal.", ""]
    lines += ["- " + item for item in data["limitations"]]
    lines += ["", "Next: freeze the authorization-scoring rubric with the author, audit executed calls, then compute supported TCR/HITL/cost figures and analyze failure trajectories. Do not infer safety from a policy or reviewer decision.", ""]
    with stem.with_suffix(".json").open("x") as stream:
        stream.write(json.dumps(data, indent=2) + "\n")
    with stem.with_suffix(".md").open("x") as stream:
        stream.write("\n".join(lines))
    print(json.dumps({"summary": str(stem.with_suffix(".json").relative_to(ROOT)),
        "attempted_cells": 54, "utility_true_false_unknown": [data["utility_successes"], data["utility_failures"], data["utility_unknown"]],
        "candidate_costs": data["candidate_costs"]}, indent=2))


if __name__ == "__main__":
    main()

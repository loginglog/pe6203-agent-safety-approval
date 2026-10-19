"""Agent-driven, task-scoped pipeline with offline planning as the default."""

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import distribution
import json
from pathlib import Path
import tempfile
import sys
from time import monotonic
from urllib.parse import urlsplit

from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
from agentdojo.agent_pipeline.llms.openai_llm import (
    _function_to_openai, _message_to_openai, _openai_to_assistant_message,
)
from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite
from agentdojo.types import text_content_block_from_string

from .completions import CompletionGateway, live_client, mock_client, strict_json
from .executor import ApprovalGate, _public
from .llm_reviewer import LLMReviewer
from .offline import fingerprint, no_network
from .policies import CandidateFilePolicy, FullApprovePolicy, FullEscalatePolicy
from .spend_control import SpendControl, SpendControlError


ROOT = Path(__file__).resolve().parents[2]
POLICIES = {"full-approve": FullApprovePolicy, "full-escalate": FullEscalatePolicy,
            "candidate": CandidateFilePolicy}


@dataclass(frozen=True)
class RunConfig:
    task_id: str = "user_task_26"
    strategy: str = "full-escalate"
    k: int = 2
    suite: str = "workspace"
    benchmark_version: str = "v1.2.2"
    agent_model: str = "openai/gpt-4o-mini"
    reviewer_model: str = "openai/gpt-4o-mini"
    base_url: str = "https://openrouter.ai/api/v1"
    max_agent_turns: int = 4
    max_api_requests: int = 6
    agent_max_tokens: int = 512
    reviewer_max_tokens: int = 256
    timeout_seconds: float = 30
    agent_timeout_seconds: float | None = None
    reviewer_timeout_seconds: float | None = None
    task_timeout_seconds: float | None = None
    spend_control: dict | None = None
    attack_fixture: dict | None = None

    def validate(self):
        if self.strategy not in POLICIES:
            raise ValueError("Unknown strategy")
        if self.attack_fixture is not None:
            fixture = self.attack_fixture
            if (not isinstance(fixture, dict) or set(fixture) != {"source", "injection_task_id", "injections"}
                    or not all(isinstance(fixture[k], str) and fixture[k] for k in ("source", "injection_task_id"))
                    or not isinstance(fixture["injections"], dict) or not fixture["injections"]
                    or not all(isinstance(k, str) and isinstance(v, str) for k, v in fixture["injections"].items())):
                raise ValueError("Invalid offline attack fixture")
        for name in ("max_agent_turns", "max_api_requests", "agent_max_tokens", "reviewer_max_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.k) is not int or self.k < 0:
            raise ValueError("k must be a non-negative integer")
        for name in ("timeout_seconds", "agent_timeout_seconds", "reviewer_timeout_seconds", "task_timeout_seconds"):
            value = getattr(self, name)
            if value is None and name != "timeout_seconds":
                continue
            if type(value) not in (int, float) or not 0 < value < float("inf"):
                raise ValueError("A finite positive timeout is required")
        url = urlsplit(self.base_url)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Use a credential-free HTTPS base URL")
        if self.spend_control is not None:
            SpendControl(self.spend_control)
            if (self.base_url != "https://openrouter.ai/api/v1"
                    or {self.agent_model, self.reviewer_model} != {self.spend_control["model"]}):
                raise ValueError("Spending verification must match the endpoint and both requested models")

    def component_timeouts(self):
        return {"agent": self.agent_timeout_seconds or self.timeout_seconds,
                "reviewer": self.reviewer_timeout_seconds or self.timeout_seconds}


class AgentTurnLimitError(RuntimeError):
    pass


class AgentFormatError(RuntimeError):
    pass


@dataclass(frozen=True)
class IndependentCase:
    """Explicit test input, not an official task or a live execution interface."""

    case_id: str
    request: str
    environment: object

    def validate(self, config, mode):
        if mode not in ("plan", "mock"):
            raise ValueError("Independent cases are plan/mock only")
        if (not isinstance(self.case_id, str) or not self.case_id.startswith("independent/")
                or config.task_id != self.case_id or not isinstance(self.request, str)
                or not self.request.strip() or not callable(getattr(self.environment, "model_copy", None))):
            raise ValueError("An explicit independent ID, request and isolated model environment are required")
        if config.suite != "workspace" or config.attack_fixture is not None or config.spend_control is not None:
            raise ValueError("Independent checks use Workspace without attack fixtures or spending controls")


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def append_json(path, value):
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(_public(value), ensure_ascii=False) + "\n")


def load_task(config):
    config.validate()
    suite = get_suite(config.benchmark_version, config.suite)
    task = suite.user_tasks[config.task_id]
    injections = config.attack_fixture["injections"] if config.attack_fixture else {}
    if config.attack_fixture:
        suite.get_injection_task_by_id(config.attack_fixture["injection_task_id"])
    env = task.init_environment(suite.load_and_inject_default_environment(injections).model_copy(deep=True))
    return suite, task, env


class MeteredAgent(BasePipelineElement):
    """Use official conversion helpers, without the official LLM retry decorator."""

    def __init__(self, gateway, config, messages, checkpoint):
        self.gateway, self.config = gateway, config
        self.messages = messages
        self.turns = 0
        self.checkpoint = checkpoint

    def query(self, query, runtime, env=None, messages=None, extra_args=None):
        self.messages = list(messages)
        self.checkpoint(self.messages)
        if self.turns >= self.config.max_agent_turns:
            raise AgentTurnLimitError("Maximum agent response turns reached.")
        self.turns += 1
        response = self.gateway.complete(
            "agent", self.config.agent_model,
            messages=[_message_to_openai(m, self.config.agent_model) for m in self.messages],
            tools=[_function_to_openai(f) for f in runtime.functions.values()],
            tool_choice="auto", temperature=0, max_tokens=self.config.agent_max_tokens,
        )
        try:
            if len(response["choices"]) != 1:
                raise ValueError("Expected one agent choice")
            choice = response["choices"][0]
            if choice.get("finish_reason") not in ("stop", "tool_calls"):
                raise ValueError("Incomplete agent response")
            from openai.types.chat import ChatCompletionMessage
            api_message = ChatCompletionMessage.model_validate(choice["message"])
            if api_message.refusal or api_message.function_call:
                raise ValueError("Agent refused or returned an unsupported legacy function call")
            ids = [c.id for c in api_message.tool_calls or []]
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate tool call identifiers")
            for call in api_message.tool_calls or []:
                if not call.id or call.type != "function" or not isinstance(strict_json(call.function.arguments), dict):
                    raise ValueError("Invalid tool proposal")
                # Reject duplicate keys before the installed converter calls json.loads.
                strict_json(call.function.arguments)
            output = _openai_to_assistant_message(api_message)
            if not output.get("tool_calls") and not (api_message.content or "").strip():
                raise ValueError("Empty agent result")
        except Exception:
            raise AgentFormatError("Invalid or incomplete agent response") from None
        self.messages = [*self.messages, output]
        self.checkpoint(self.messages)
        return query, runtime, env, self.messages, extra_args


def run_task(config=RunConfig(), *, mode="plan", client=None, log_root=None, independent_case=None):
    """Plan needs no client. Mock/live modes run the same actual pipeline.

    A caller supplies an explicit client only for execution. The CLI creates a
    real client exclusively after --enable-api, or a local HTTP mock otherwise.
    """
    started = monotonic()
    if mode not in ("plan", "mock", "live"):
        raise ValueError("Unknown execution mode")
    if independent_case is not None:
        if not isinstance(independent_case, IndependentCase):
            raise ValueError("Independent input must be an IndependentCase")
        independent_case.validate(config, mode)
        if mode == "mock":
            import httpx
            transport = getattr(getattr(client, "_client", None), "_transport", None)
            if not isinstance(transport, httpx.MockTransport):
                raise ValueError("Independent mock execution requires the local HTTP mock transport")
    if mode != "plan" and client is None:
        raise ValueError("Execution needs an explicitly supplied client")
    if mode != "plan" and getattr(client, "max_retries", None) != 0:
        raise ValueError("Client retries must be disabled for exact request limits")
    if mode == "live" and config.spend_control is None:
        raise ValueError("Live execution requires verified spending controls")
    if mode == "live" and config.attack_fixture is not None:
        raise ValueError("Attack fixture execution is plan/mock only until the attack protocol is agreed")
    if independent_case is None:
        suite, task, env = load_task(config)
        task_id, task_request = task.ID, task.PROMPT
    else:
        config.validate()
        suite = get_suite(config.benchmark_version, config.suite)
        task = None
        task_id, task_request = independent_case.case_id, independent_case.request
        env = independent_case.environment.model_copy(deep=True)
    before = env.model_copy(deep=True)
    log_root = Path(log_root or ROOT / "results/raw")
    log_root = log_root.resolve()
    if not log_root.is_relative_to(ROOT):
        raise ValueError("Run logs must remain inside this project repository")
    log_root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="task_run_", dir=log_root))
    agent_prompt = (ROOT / "prompts/agent_v1.txt").read_text()
    review_prompt = (ROOT / "prompts/reviewer_v1.txt").read_text()
    policy = POLICIES[config.strategy]()
    dist = distribution("agentdojo")
    metadata = {
        "mode": mode, "configuration": asdict(config), "policy_version": policy.version,
        "agent_prompt_version": "agent-v1", "reviewer_prompt_version": "reviewer-v1",
        "agent_prompt": agent_prompt, "reviewer_prompt": review_prompt,
        "agent_prompt_sha256": sha256(agent_prompt.encode()).hexdigest(),
        "reviewer_prompt_sha256": sha256(review_prompt.encode()).hexdigest(),
        "agentdojo_package_version": dist.version,
        "python_version": sys.version,
        "implementation_sha256": {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest()
                                  for p in sorted((ROOT / "src/approval_gate").glob("*.py"))},
        "agentdojo_installation_metadata": json.loads(dist.read_text("direct_url.json") or "{}"),
        "original_user_task": task_request, "tool_registry": [f.name for f in suite.tools],
        "task_source": "independent_development" if independent_case else "official_benchmark",
        "official_evaluation_enabled": independent_case is None,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sdk_max_retries": 0, "application_retries": 0,
        "timeout_configuration": {
            "component_io_timeout_seconds": {name: {phase: value for phase in ("connect", "read", "write", "pool")}
                                             for name, value in config.component_timeouts().items()},
            "request_wall_clock_timeout_seconds": None,
            "task_timeout_seconds": config.task_timeout_seconds,
            "task_deadline_mode": "Cooperative monotonic checks before requests/tools and after responses; not hard in-flight cancellation.",
            "precedence": "Component override > --timeout-seconds; remaining task time clamps each HTTP I/O phase.",
        },
        "model_configuration_status": "unverified with real service",
        "condition": "injected_fixture" if config.attack_fixture else "normal",
        "sampling": {"temperature": 0, "model_seed": None},
    }
    if independent_case:
        metadata.update(condition="independent_development", independent_case_id=task_id,
                        model_configuration_status="Local synthetic responses; no service verification",
                        usage_provenance="mock SDK requests and synthetic usage only")
    write_json(directory / "config.json", metadata)
    (directory / "agent_prompt.txt").write_text(agent_prompt)
    (directory / "reviewer_prompt.txt").write_text(review_prompt)
    if mode == "plan":
        result = {"status": "plan_only", "api_requests_attempted": 0,
                  "execution_status": "not_run", "task_utility": None, "official_attack_success": None,
                  "condition": metadata["condition"], "strategy": config.strategy,
                  "outcome_categories": ["not_run"],
                  "note": "No credential lookup, client construction, model call or tool execution.",
                  "log_directory": str(directory.relative_to(ROOT))}
        if independent_case:
            result.update(task_id=task_id, policy_version=policy.version,
                          task_source="independent_development", official_evaluation_enabled=False)
        write_json(directory / "result.json", result)
        return result

    if independent_case:
        write_json(directory / "environment_before.json", env.model_dump(mode="json"))
    spend = SpendControl(config.spend_control, lambda e: append_json(directory / "spend_ledger.jsonl", e)) if config.spend_control else None
    gateway = CompletionGateway(client, config.max_api_requests,
                                lambda e: append_json(directory / "api_calls.jsonl", {
                                    **e, **({"usage_provenance": "mock_response", "real_api_request": False}
                                            if independent_case else {})}), spend_control=spend,
                                component_timeouts=config.component_timeouts(),
                                task_deadline=started + config.task_timeout_seconds if config.task_timeout_seconds is not None else None)
    definitions = {f.name: dict(_function_to_openai(f)["function"]) for f in suite.tools}
    reviewer = LLMReviewer(gateway, config.reviewer_model, review_prompt, definitions,
                           config.reviewer_max_tokens,
                           lambda e: append_json(directory / "reviews.jsonl", e))
    def check_run_stop():
        gateway.check_can_continue()
        if spend and spend.stop_reason:
            raise SpendControlError(spend.stop_reason)

    executor = ApprovalGate(policy, reviewer).new_task(task_id, task_request, config.k, before_call=check_run_stop)
    written = 0

    def checkpoint(messages):
        nonlocal written
        for record in executor.records[written:]:
            append_json(directory / "approvals.jsonl", record)
        written = len(executor.records)
        append_json(directory / "trajectory_checkpoints.jsonl", {"messages": messages})

    messages = [
        {"role": "system", "content": [text_content_block_from_string(agent_prompt)]},
        {"role": "user", "content": [text_content_block_from_string(task_request)]},
    ]
    agent = MeteredAgent(gateway, config, messages, checkpoint)
    runtime = FunctionsRuntime(suite.tools)
    errors = []
    try:
        _, _, _, messages, _ = agent.query(task_request, runtime, env, messages, {})
        # The actual existing approval executor is inside the official loop.
        loop = ToolsExecutionLoop([executor, agent], max_iters=config.max_agent_turns)
        _, _, _, messages, _ = loop.query(task_request, runtime, env, messages, {})
    except Exception as exc:
        errors.append({"component": "agent_or_pipeline", "category": type(exc).__name__})
    finally:
        messages = agent.messages
        checkpoint(messages)
    final = messages[-1] if messages else {}
    finished = final.get("role") == "assistant" and not final.get("tool_calls") and bool(final.get("content"))
    utility = None
    tool_results = [m for m in messages if m["role"] == "tool"]
    executed_trace = [m["tool_call"] for m, r in zip(tool_results, executor.records) if r["tool_executed"]]
    if finished and independent_case is None:
        try:
            # Scoring is evaluator-only and runs after all model decisions.
            utility = suite._check_user_task_utility(task, final["content"], before, env, executed_trace)
        except Exception as exc:
            errors.append({"component": "evaluator", "category": type(exc).__name__})
    attack_success, attack_check_status = None, "not_applicable"
    if config.attack_fixture:
        try:
            # Evaluator-only goal object never enters the policy/reviewer context.
            attack_task = suite.get_injection_task_by_id(config.attack_fixture["injection_task_id"])
            attack_success = suite._check_injection_task_security(
                attack_task, (final.get("content") or []) if finished else [], before, env, executed_trace)
            attack_check_status = "checked" if finished else "checked_partial_execution"
        except Exception as exc:
            attack_check_status = "error"
            errors.append({"component": "attack_evaluator", "category": type(exc).__name__})
    errors.extend({"component": "reviewer", "category": e["error_category"]}
                  for e in reviewer.events if e["error_category"])
    usage = gateway.usage(sum(r["policy_decision"] is not None for r in executor.records))
    if independent_case:
        for component, item in usage.items():
            item.update(usage_provenance="synthetic mock usage; not provider usage or fees",
                        mock_requests_attempted=item["api_requests_attempted"], real_api_requests_attempted=0)
            if component != "policy":
                item["synthetic_reported_cost_usd_credits"] = (
                    item["provider_reported_cost_usd_credits"] if item["api_requests_attempted"] else None)
                item["provider_reported_cost_usd_credits"] = None
                item["estimated_cost"] = None
    result = {
        "status": "completed" if finished else "stopped", "mode": mode,
        "task_id": task_id, "suite": config.suite, "benchmark_version": config.benchmark_version,
        "strategy": config.strategy, "review_budget_limit": config.k, "condition": metadata["condition"],
        "original_user_task": task_request, "policy_version": policy.version,
        "final_answer_received": finished, "task_utility": utility,
        "security": None, "security_evaluated": False,
        "security_note": "No attack was run. Native no-attack security=true is not policy safety evidence.",
        "official_attack_success": attack_success, "attack_check_status": attack_check_status,
        "authorization_assessment": None,
        "agent_turns": agent.turns, "review_budget_used": executor.used,
        "api_requests_attempted": len(gateway.events), "usage": usage, "errors": errors,
        "stop_reason": gateway.stop_reason or (spend.stop_reason if spend else None) or
                       (errors[0]["category"] if errors else None),
        "spending": spend.summary() if spend else None,
        "tool_bodies_entered": sum(r["tool_executed"] for r in executor.records),
        "environment_changed": env != before,
        "environment_sha256_before": fingerprint(before), "environment_sha256_after": fingerprint(env),
        "log_directory": str(directory.relative_to(ROOT)),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": monotonic() - started,
    }
    if config.attack_fixture:
        result["security_note"] = "Official attack-goal success is recorded separately; comprehensive authorization safety is not assessed."
    if independent_case:
        result.update(task_source="independent_development", official_evaluation_enabled=False,
                      real_api_requests_attempted=0, mock_requests_attempted=len(gateway.events),
                      independent_case_id=task_id,
                      completion_kind="mock_pipeline_final_answer" if finished else "mock_pipeline_stopped",
                      security_note="Independent mock pipeline check; no official completion or safety evaluation.")
        if finished:
            # Review errors remain in errors/reviews; they did not stop this pipeline.
            result["stop_reason"] = None
        write_json(directory / "environment_after.json", env.model_dump(mode="json"))
    from .evaluation import outcome_categories
    result["outcome_categories"] = outcome_categories(result, executor.records, gateway.events)
    write_json(directory / "evaluation.json", {
        "official_task_utility": utility,
        "utility_check_status": "disabled_independent_case" if independent_case else
                                "checked" if finished and utility is not None else "not_obtained",
        "official_attack_success": attack_success, "attack_check_status": attack_check_status,
        "authorization_assessment": None,
        "executed_call_sequences": [r["sequence"] for r in executor.records if r["tool_executed"]],
        "note": "Attack-goal failure is not evidence that every executed action was authorized.",
    })
    write_json(directory / "trajectory.json", _public(messages))
    write_json(directory / "usage.json", usage)
    write_json(directory / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan by default; explicitly enable real API or mock execution.")
    parser.add_argument("--task-id", default="user_task_26")
    parser.add_argument("--strategy", choices=POLICIES, default="full-escalate")
    parser.add_argument("--suite", default="workspace")
    parser.add_argument("--benchmark-version", default="v1.2.2")
    parser.add_argument("--k", type=int, default=2)
    parser.add_argument("--agent-model", default="openai/gpt-4o-mini")
    parser.add_argument("--reviewer-model", default="openai/gpt-4o-mini")
    parser.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    parser.add_argument("--max-agent-turns", type=int, default=4)
    parser.add_argument("--max-api-requests", type=int, default=6)
    parser.add_argument("--agent-max-tokens", type=int, default=512)
    parser.add_argument("--reviewer-max-tokens", type=int, default=256)
    parser.add_argument("--timeout-seconds", type=float, default=30,
                        help="Default timeout for each HTTP connect/read/write/pool operation; not request total")
    parser.add_argument("--agent-timeout-seconds", type=float, help="Override agent HTTP I/O timeout")
    parser.add_argument("--reviewer-timeout-seconds", type=float, help="Override reviewer HTTP I/O timeout")
    parser.add_argument("--task-timeout-seconds", type=float,
                        help="Optional cooperative monotonic task deadline; not hard in-flight cancellation")
    parser.add_argument("--spend-control", type=Path, help="Verified public rate/context ceilings and USD budget JSON")
    parser.add_argument("--attack-fixture", type=Path, help="Official injection mapping plus evaluator ID; plan/mock only")
    parser.add_argument("--log-root", type=Path, default=ROOT / "results/raw")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--enable-api", action="store_true")
    modes.add_argument("--mock-responses", type=Path)
    args = vars(parser.parse_args(argv))
    enable, mocks, logs = args.pop("enable_api"), args.pop("mock_responses"), args.pop("log_root")
    if args["spend_control"] is not None:
        args["spend_control"] = json.loads(args["spend_control"].read_text())
    if args["attack_fixture"] is not None:
        args["attack_fixture"] = strict_json(args["attack_fixture"].read_text())
    config = RunConfig(**args)
    config.validate()
    if enable and config.spend_control is None:
        raise ValueError("Verify rates and supply --spend-control before loading credentials")
    if enable and config.attack_fixture is not None:
        raise ValueError("Live attack protocol is pending; no credential lookup is allowed")
    client = None
    try:
        if enable:
            client = live_client(config.base_url, config.timeout_seconds, ROOT / ".env")
            result = run_task(config, mode="live", client=client, log_root=logs)
        elif mocks:
            client, _ = mock_client(json.loads(mocks.read_text()))
            with no_network():
                result = run_task(config, mode="mock", client=client, log_root=logs)
        else:
            result = run_task(config, log_root=logs)
        print(json.dumps(result, indent=2))
        return 1 if result["status"] == "stopped" else 0
    finally:
        if client:
            client.close()

"""Bounded Chat Completions transport and component-specific usage accounting."""

from collections import deque
from copy import deepcopy
import json
from datetime import datetime, timezone
from time import monotonic
from decimal import Decimal

from .spend_control import money


class RequestLimitError(RuntimeError):
    pass


class APIRequestError(RuntimeError):
    pass


class TaskDeadlineError(RuntimeError):
    pass


class RunStoppedError(RuntimeError):
    pass


def safe_exception_details(exc):
    """Retain exception classes/known phases, never messages, requests or headers."""
    chain, phase, seen = [], None, set()
    current = exc
    phases = {"ConnectTimeout": "connect", "ReadTimeout": "read",
              "WriteTimeout": "write", "PoolTimeout": "pool"}
    while current is not None and id(current) not in seen and len(chain) < 8:
        seen.add(id(current))
        name = type(current).__name__
        chain.append(name)
        if type(current).__module__.split(".")[0] in ("httpx", "httpx2", "httpcore"):
            phase = phases.get(name, phase)
        current = current.__cause__ or current.__context__
    return {"exception_type_chain": chain, "exception_phase": phase or "unknown"}


def input_summary(payload):
    """Content sizes only; token count requires a tokenizer or service usage."""
    messages = payload.get("messages", [])
    tool_contents = [m.get("content") for m in messages if m.get("role") == "tool"]
    texts = []
    for content in tool_contents:
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            texts.extend(p["text"] for p in content if p.get("type") == "text" and isinstance(p.get("text"), str))
    return {"message_count": len(messages), "message_roles": [m.get("role") for m in messages],
            "tool_definition_count": len(payload.get("tools", [])),
            "tool_text_characters": sum(len(s) for s in texts),
            "tool_text_utf8_bytes": sum(len(s.encode("utf-8")) for s in texts),
            "tool_content_json_utf8_bytes": sum(len(json.dumps(c, ensure_ascii=False).encode("utf-8")) for c in tool_contents),
            "input_token_estimate": None, "token_estimate_note": "Not computed locally; sizes are not token counts."}


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError("Non-finite JSON value")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def token_value(value):
    return value if type(value) is int and value >= 0 else None


class CompletionGateway:
    """One counted SDK invocation per attempt; clients must use max_retries=0."""

    def __init__(self, client, max_requests, event_sink=None, spend_control=None,
                 component_timeouts=None, task_deadline=None):
        self.client = client
        self.max_requests = max_requests
        self.events = []
        self.event_sink = event_sink
        self.spend_control = spend_control
        self.component_timeouts = component_timeouts or {}
        self.task_deadline = task_deadline
        self.stop_reason = None

    def check_can_continue(self):
        if self.stop_reason:
            raise RunStoppedError(self.stop_reason)
        if self.task_deadline is not None and monotonic() >= self.task_deadline:
            self.stop_reason = "TASK_DEADLINE_EXCEEDED"
            if self.spend_control:
                self.spend_control.stop_reason = self.spend_control.stop_reason or self.stop_reason
            raise TaskDeadlineError(self.stop_reason)

    def complete(self, component, model, **payload):
        if component not in ("agent", "reviewer"):
            raise ValueError("Invalid API accounting component")
        self.check_can_continue()
        if len(self.events) >= self.max_requests:
            raise RequestLimitError("Per-task API request limit reached.")
        reservation = self.spend_control.reserve(component, model, payload) if self.spend_control else None
        remaining = max(0, self.task_deadline - monotonic()) if self.task_deadline is not None else None
        timeout = self.component_timeouts.get(component)
        if timeout is not None:
            import httpx
            effective = min(timeout, remaining) if remaining is not None else timeout
            request_timeout = httpx.Timeout(effective)
            timeout_info = request_timeout.as_dict()
        else:
            request_timeout = None
            timeout_info = None
        event = {"sequence": len(self.events) + 1, "component": component,
                 "requested_model": model, "response_model": None, "response_id": None,
                 "response_provider": None, "estimated_cost_usd": None, "accounted_cost_usd": None,
                 "started_at_utc": datetime.now(timezone.utc).isoformat(),
                 "ended_at_utc": None, "io_timeout_seconds": timeout_info,
                 "task_seconds_remaining_before": remaining,
                 "input_summary": input_summary(payload),
                 "exception_type_chain": [], "exception_phase": None, "stage_at_error": None,
                 "reservation": reservation,
                 "input_tokens": None, "output_tokens": None, "total_tokens": None,
                 "provider_reported_cost": None, "provider_cost_currency": None,
                 "response_received": False, "error_category": None,
                 "request": deepcopy(payload), "response": None}
        self.events.append(event)
        started = monotonic()
        stage = "sdk_request"
        try:
            options = {"timeout": request_timeout} if request_timeout is not None else {}
            response = self.client.chat.completions.create(model=model, **payload, **options)
            stage = "response_validation"
            response = response.model_dump(mode="json") if hasattr(response, "model_dump") else response
            if not isinstance(response, dict):
                raise ValueError("Completion response is not an object")
            event.update(response_received=True, response=deepcopy(response),
                         response_model=response.get("model"), response_id=response.get("id"),
                         response_provider=response.get("provider"))
            usage = response.get("usage") or {}
            if isinstance(usage, dict):
                event.update(input_tokens=token_value(usage.get("prompt_tokens")),
                             output_tokens=token_value(usage.get("completion_tokens")),
                             total_tokens=token_value(usage.get("total_tokens")),
                             provider_reported_cost=usage.get("cost"))
                if usage.get("cost") is not None:
                    event["provider_cost_currency"] = "USD credits" if self.spend_control else None
            if self.spend_control:
                stage = "usage_accounting"
                self.spend_control.settle(reservation, event)
            stage = "task_deadline_check"
            self.check_can_continue()
            return response
        except Exception as exc:
            # Error bodies/headers can contain credentials. Persist the type only.
            event["error_category"] = type(exc).__name__
            event.update(safe_exception_details(exc), stage_at_error=stage)
            event["http_status"] = getattr(exc, "status_code", None)
            if type(exc).__name__ == "APITimeoutError" or event["exception_phase"] in ("connect", "read", "write", "pool"):
                self.stop_reason = "REQUEST_TIMEOUT"
            if self.spend_control:
                self.spend_control.stop_reason = self.spend_control.stop_reason or "REQUEST_FAILED_COST_UNKNOWN"
            raise APIRequestError(type(exc).__name__) from None
        finally:
            event["elapsed_seconds"] = monotonic() - started
            event["ended_at_utc"] = datetime.now(timezone.utc).isoformat()
            event["stop_reason"] = self.stop_reason or (self.spend_control.stop_reason if self.spend_control else None)
            if self.event_sink:
                self.event_sink(event)

    def usage(self, policy_evaluations=0):
        result = {}
        for component in ("agent", "reviewer", "policy"):
            events = [e for e in self.events if e["component"] == component]
            item = {"api_requests_attempted": len(events),
                    "api_responses_received": sum(e["response_received"] for e in events),
                    "estimated_cost": None, "provider_bill_cost": None,
                    "response_models": [e["response_model"] for e in events]}
            for field in ("input_tokens", "output_tokens", "total_tokens"):
                values = [e[field] for e in events]
                item[field] = sum(values) if all(v is not None for v in values) else None
                item["known_" + field + "_subtotal"] = sum(v for v in values if v is not None)
            if component == "policy":
                item["decision_evaluations"] = policy_evaluations
            item["response_providers"] = [e["response_provider"] for e in events]
            costs = [e["estimated_cost_usd"] for e in events]
            item["estimated_cost"] = str(sum((money(c) for c in costs), Decimal(0))) if all(c is not None for c in costs) else None
            item["known_estimated_cost_usd_subtotal"] = str(sum((money(c) for c in costs if c is not None), Decimal(0)))
            reported = [e["provider_reported_cost"] for e in events]
            try:
                item["provider_reported_cost_usd_credits"] = str(sum((money(c) for c in reported), Decimal(0))) if all(c is not None for c in reported) else None
            except ValueError:
                item["provider_reported_cost_usd_credits"] = None
            valid_reported = []
            for cost in reported:
                if cost is not None:
                    try:
                        valid_reported.append(money(cost))
                    except ValueError:
                        pass
            item["known_reported_cost_usd_credits_subtotal"] = str(sum(valid_reported, Decimal(0)))
            item["provider_bill_cost"] = None
            result[component] = item
        return result


def _sdk_client(api_key, base_url, timeout_seconds, transport=None):
    """Shared client entry point; tests supply a dummy key and local transport."""
    import httpx
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url, max_retries=0, timeout=timeout_seconds,
                  http_client=httpx.Client(timeout=timeout_seconds, follow_redirects=False, transport=transport))


def mock_client(items, timeout_seconds=30):
    """Real OpenAI SDK with a local HTTP mock; no connection or key lookup."""
    import httpx

    queue = deque(deepcopy(items))
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        if not queue:
            raise AssertionError("No mock API response remains")
        item = queue.popleft()
        if "mock_error" in item:
            raise httpx.ConnectError("Synthetic offline request failure", request=request)
        return httpx.Response(200, json=item, request=request)

    client = _sdk_client("offline-dummy-key", "https://offline.invalid/v1", timeout_seconds,
                         transport=httpx.MockTransport(respond))
    return client, requests


def live_client(base_url, timeout_seconds, env_file):
    """Called only after explicit --enable-api, never by plan/mock mode."""
    import os
    from dotenv import dotenv_values

    key = os.environ.get("OPENAI_COMPATIBLE_API_KEY")
    if not key:
        key = dotenv_values(env_file).get("OPENAI_COMPATIBLE_API_KEY")
    if not key:
        raise ValueError("Configure OPENAI_COMPATIBLE_API_KEY locally before enabling API access.")
    return _sdk_client(key, base_url, timeout_seconds)

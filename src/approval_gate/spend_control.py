"""Conservative per-request reservations using verified service context/rate ceilings.

This is a program-side USD ledger, not a provider account spending hard limit.
No tokenizer estimate is used: reserve the entire verified context as input,
plus the requested output cap, even though the context also contains output.
"""

from decimal import Decimal, InvalidOperation
import json


class SpendControlError(RuntimeError):
    pass


def money(value):
    if isinstance(value, bool):
        raise ValueError("Invalid monetary value")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid monetary value") from None
    if not number.is_finite() or number < 0:
        raise ValueError("A finite non-negative monetary value is required")
    return number


class SpendControl:
    def __init__(self, settings, event_sink=None):
        self.settings = dict(settings)
        self.limit = money(settings["budget_usd"])
        self.prompt_rate = money(settings["prompt_usd_per_token"])
        self.completion_rate = money(settings["completion_usd_per_token"])
        if not self.limit or not self.prompt_rate or not self.completion_rate:
            raise ValueError("Positive budget and verified token rates are required")
        for field in ("context_tokens", "max_request_bytes", "agent_max_tokens", "reviewer_max_tokens"):
            if type(settings[field]) is not int or settings[field] <= 0:
                raise ValueError("Positive integer input/output ceilings are required")
        if not settings.get("model") or not settings.get("pricing_source") or not settings.get("verified_at_utc"):
            raise ValueError("Record model and pricing verification provenance")
        self.committed = Decimal(0)
        self.stop_reason = None
        self.events = []
        self.event_sink = event_sink

    def stop(self, reason):
        self.stop_reason = self.stop_reason or reason
        raise SpendControlError(self.stop_reason)

    def reserve(self, component, model, payload):
        if self.stop_reason:
            raise SpendControlError(self.stop_reason)
        if model != self.settings["model"]:
            self.stop("UNVERIFIED_MODEL")
        cap = payload.get("max_tokens")
        if type(cap) is not int or not 0 < cap <= self.settings[component + "_max_tokens"]:
            self.stop("OUTPUT_CAP_MISSING_OR_EXCEEDED")
        # Refuse optional chargeable features, alternate models, headers and routing overrides.
        allowed = {"messages", "tools", "tool_choice", "temperature", "max_tokens", "response_format"}
        if set(payload) - allowed:
            self.stop("UNVERIFIED_REQUEST_FEATURE")
        payload["extra_body"] = {"provider": {
            "allow_fallbacks": False, "require_parameters": True,
            "max_price": {"prompt": float(self.prompt_rate * 1000000),
                          "completion": float(self.completion_rate * 1000000), "request": 0},
        }}
        size = len(json.dumps({"model": model, **payload}, ensure_ascii=False).encode("utf-8"))
        if size > self.settings["max_request_bytes"]:
            self.stop("REQUEST_BYTE_LIMIT")
        reservation = self.prompt_rate * self.settings["context_tokens"] + self.completion_rate * cap
        if self.committed + reservation > self.limit:
            self.stop("INSUFFICIENT_REMAINING_BUDGET")
        record = {"component": component, "request_bytes": size,
                  "input_token_ceiling": self.settings["context_tokens"], "output_token_ceiling": cap,
                  "committed_before_usd": str(self.committed), "reserved_usd": str(reservation),
                  "remaining_after_reservation_usd": str(self.limit - self.committed - reservation),
                  "settled_estimate_usd": None, "accounted_usd": str(reservation), "state": "reserved"}
        self.committed += reservation
        self.events.append(record)
        if self.event_sink:
            self.event_sink(dict(record))
        return record

    def settle(self, record, event):
        inputs, outputs, total = (event.get(f) for f in ("input_tokens", "output_tokens", "total_tokens"))
        if any(type(v) is not int or v < 0 for v in (inputs, outputs, total)):
            self.stop("MISSING_TOKEN_USAGE")
        if (inputs > record["input_token_ceiling"] or outputs > record["output_token_ceiling"]
                or inputs + outputs != total):
            self.stop("TOKEN_USAGE_EXCEEDS_OR_CONTRADICTS_LIMITS")
        estimate = inputs * self.prompt_rate + outputs * self.completion_rate
        reported = event.get("provider_reported_cost")
        try:
            reported = money(reported) if reported is not None else None
        except ValueError:
            self.stop("INVALID_REPORTED_COST")
        accounted = max(estimate, reported or Decimal(0))
        if accounted > money(record["reserved_usd"]):
            self.stop("COST_EXCEEDS_RESERVATION")
        self.committed += accounted - money(record["reserved_usd"])
        record.update(settled_estimate_usd=str(estimate), accounted_usd=str(accounted), state="settled")
        event["estimated_cost_usd"] = str(estimate)
        event["accounted_cost_usd"] = str(accounted)
        if self.event_sink:
            self.event_sink(dict(record))

    def summary(self):
        return {"budget_usd": str(self.limit), "accounted_usd": str(self.committed),
                "remaining_usd": str(self.limit - self.committed), "stop_reason": self.stop_reason,
                "unsettled_reservations": sum(e["state"] != "settled" for e in self.events),
                "control": "Program-side published-rate reservations; not a platform billing hard cap."}
